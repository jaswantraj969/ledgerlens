"""Webhook events and signed delivery with retries.

Signature: `X-LedgerLens-Signature: sha256=<hex>`, the HMAC-SHA256 of `<timestamp>.<body>` with the
webhook's secret, where `<timestamp>` is `X-LedgerLens-Timestamp` (Unix seconds). Receivers should
reject old timestamps. Payloads carry ids and states only, never field values or document text.

Delivery runs on the RQ queue with backoff (`webhook_retry_intervals`). A non-2xx reply or a
network error is retried; after the last attempt the delivery is marked failed.
"""

import hashlib
import hmac
import ipaddress
import json
import socket
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx
import redis
import structlog
from rq import Retry, get_current_job
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlens.core.config import Settings
from ledgerlens.db.models import Webhook, WebhookDelivery, utcnow
from ledgerlens.workers.queue import queue_for

_log = structlog.get_logger()
EVENTS = ("job.completed", "job.ready_for_review", "job.failed", "document.reviewed")
DELIVER_TASK = "ledgerlens.workers.webhooks.deliver"


class UnsafeWebhookUrl(ValueError):
    pass


def sign(secret: str, timestamp: int, body: bytes) -> str:
    message = str(timestamp).encode() + b"." + body
    return "sha256=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def check_url(url: str, *, allow_insecure: bool) -> None:
    """Refuse anything but https to a public address, unless insecure targets are allowed."""
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise UnsafeWebhookUrl("the URL must be http(s) with a host")
    if allow_insecure:
        return
    if parts.scheme != "https":
        raise UnsafeWebhookUrl("the URL must use https")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 443)}
    except OSError as error:
        raise UnsafeWebhookUrl("the host does not resolve") from error
    for address in addresses:
        ip = ipaddress.ip_address(str(address).split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise UnsafeWebhookUrl("the host resolves to a private address")


def emit(
    session: Session, organization_id: uuid.UUID, event: str, payload: dict[str, Any]
) -> list[uuid.UUID]:
    """Add one delivery per active, subscribed webhook. The caller commits, then enqueues."""
    hooks = session.scalars(
        select(Webhook).where(Webhook.organization_id == organization_id, Webhook.active)
    ).all()
    created = []
    for hook in hooks:
        if hook.events and event not in hook.events:
            continue
        delivery = WebhookDelivery(
            webhook_id=hook.id, event=event, status="pending", attempts=0,
            payload={"event": event, "delivery_id": None, **payload},
        )  # fmt: skip
        session.add(delivery)
        session.flush()
        delivery.payload = {**delivery.payload, "delivery_id": str(delivery.id)}
        created.append(delivery.id)
    return created


def enqueue_deliveries(connection: redis.Redis, settings: Settings, ids: list[uuid.UUID]) -> None:
    intervals = settings.webhook_retry_intervals
    for delivery_id in ids:
        queue_for(connection, settings).enqueue(
            DELIVER_TASK, str(delivery_id), job_id=f"webhook-{delivery_id}",
            retry=Retry(max=len(intervals), interval=intervals) if intervals else None,
        )  # fmt: skip


def deliver_once(
    session: Session, delivery_id: uuid.UUID, settings: Settings, *, final: bool,
    client: httpx.Client | None = None,
) -> str:  # fmt: skip
    """One attempt. Returns the delivery status; raises to ask RQ for a retry."""
    delivery = session.get(WebhookDelivery, delivery_id)
    if delivery is None or delivery.status == "delivered":
        return "delivered" if delivery else "missing"
    hook = session.get(Webhook, delivery.webhook_id)
    if hook is None or not hook.active:
        delivery.status = "cancelled"
        session.commit()
        return "cancelled"
    body = json.dumps(delivery.payload, sort_keys=True, separators=(",", ":")).encode()
    timestamp = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "X-LedgerLens-Event": delivery.event,
        "X-LedgerLens-Delivery": str(delivery.id),
        "X-LedgerLens-Timestamp": str(timestamp),
        "X-LedgerLens-Signature": sign(hook.secret, timestamp, body),
    }
    delivery.attempts += 1
    error: str | None = None
    try:
        check_url(hook.url, allow_insecure=settings.allow_insecure_webhooks)
        http = client or httpx.Client(timeout=settings.webhook_timeout_seconds)
        reply = http.post(hook.url, content=body, headers=headers)
        delivery.response_status = reply.status_code
        if not 200 <= reply.status_code < 300:
            error = f"HTTP {reply.status_code}"
    except (httpx.HTTPError, UnsafeWebhookUrl) as failure:
        error = f"{type(failure).__name__}: {failure}"[:500]
    if error is None:
        delivery.status, delivery.delivered_at, delivery.last_error = "delivered", utcnow(), None
        session.commit()
        return "delivered"
    delivery.last_error = error
    delivery.status = "failed" if final else "retrying"
    session.commit()
    _log.warning("webhook.failed", delivery_id=str(delivery_id), retry=not final)
    if final:
        return "failed"
    raise RuntimeError(f"webhook delivery failed: {error}")


def deliver(delivery_id: str) -> str:
    """RQ entry point. Uses the worker's context; the last retry is the final attempt."""
    from ledgerlens.workers.tasks import _process_context

    context = _process_context()
    current = get_current_job()
    final = not (current.retries_left if current is not None else None)
    with context.sessions() as session:
        return deliver_once(session, uuid.UUID(delivery_id), context.settings, final=final)
