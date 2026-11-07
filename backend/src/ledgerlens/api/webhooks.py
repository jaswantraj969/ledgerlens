"""Webhook management. Admin only, organization-scoped. The secret is shown once, at creation."""

import secrets
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import select

from ledgerlens.api.deps import Principal, SessionDep, require_role
from ledgerlens.core.errors import Problem
from ledgerlens.core.security import digest
from ledgerlens.db.models import Webhook, WebhookDelivery
from ledgerlens.db.repositories import audit
from ledgerlens.workers.webhooks import EVENTS, UnsafeWebhookUrl, check_url

router = APIRouter(tags=["webhooks"])
AdminDep = Annotated[Principal, Depends(require_role("admin"))]
_missing = Problem(404, "Not found", "No such webhook.", "not_found")


class WebhookIn(BaseModel):
    url: str = PydanticField(max_length=2000)
    events: list[str] = []


class WebhookOut(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str]
    active: bool
    created_at: datetime


class WebhookCreated(WebhookOut):
    secret: str


class DeliveryOut(BaseModel):
    id: uuid.UUID
    event: str
    status: str
    attempts: int
    response_status: int | None
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None


def _out(hook: Webhook) -> WebhookOut:
    return WebhookOut(id=hook.id, url=hook.url, events=hook.events, active=hook.active,
                      created_at=hook.created_at)  # fmt: skip


@router.post("/webhooks", status_code=201)
def create_webhook(
    body: WebhookIn, request: Request, session: SessionDep, principal: AdminDep
) -> WebhookCreated:
    unknown = sorted(set(body.events) - set(EVENTS))
    if unknown:
        raise Problem(422, "Invalid webhook", f"Unknown events: {', '.join(unknown)}.",
                      "unknown_event")  # fmt: skip
    try:
        check_url(body.url, allow_insecure=request.app.state.settings.allow_insecure_webhooks)
    except UnsafeWebhookUrl as error:
        raise Problem(
            422, "Invalid webhook", f"Webhook URL refused: {error}.", "unsafe_url"
        ) from error
    secret = "whsec_" + secrets.token_urlsafe(32)
    hook = Webhook(organization_id=principal.organization_id, url=body.url, events=body.events,
                   secret=secret, secret_hash=digest(secret), active=True)  # fmt: skip
    session.add(hook)
    session.flush()
    audit(session, principal.organization_id, principal.user_id, "webhook.create", "webhook",
          hook.id, request_id=getattr(request.state, "request_id", None))  # fmt: skip
    session.commit()
    return WebhookCreated(**_out(hook).model_dump(), secret=secret)


def _owned(session: SessionDep, principal: Principal, webhook_id: uuid.UUID) -> Webhook:
    hook = session.scalar(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == principal.organization_id
        )
    )
    if hook is None:
        raise _missing
    return hook


@router.get("/webhooks")
def list_webhooks(session: SessionDep, principal: AdminDep) -> list[WebhookOut]:
    hooks = session.scalars(
        select(Webhook)
        .where(Webhook.organization_id == principal.organization_id)
        .order_by(Webhook.created_at)
    ).all()
    return [_out(hook) for hook in hooks]


@router.get("/webhooks/{webhook_id}/deliveries")
def list_deliveries(
    webhook_id: uuid.UUID, session: SessionDep, principal: AdminDep
) -> list[DeliveryOut]:
    hook = _owned(session, principal, webhook_id)
    rows = session.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == hook.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
    ).all()
    return [
        DeliveryOut(id=d.id, event=d.event, status=d.status, attempts=d.attempts,
                    response_status=d.response_status, last_error=d.last_error,
                    created_at=d.created_at, delivered_at=d.delivered_at)
        for d in rows
    ]  # fmt: skip


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: uuid.UUID, request: Request, session: SessionDep, principal: AdminDep
) -> Response:
    hook = _owned(session, principal, webhook_id)
    session.delete(hook)
    audit(session, principal.organization_id, principal.user_id, "webhook.delete", "webhook",
          webhook_id, request_id=getattr(request.state, "request_id", None))  # fmt: skip
    session.commit()
    return Response(status_code=204)
