"""Registration, login, token refresh, and API keys."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledgerlens.api.deps import Principal, SessionDep, SettingsDep, rate_limit, require_role
from ledgerlens.core.config import Settings
from ledgerlens.core.errors import Problem
from ledgerlens.core.security import (
    create_access_token,
    digest,
    hash_password,
    new_api_key,
    new_refresh_token,
    verify_password,
)
from ledgerlens.db.models import ApiKey, Organization, RefreshToken, User
from ledgerlens.db.repositories import audit

router = APIRouter(prefix="/auth", tags=["auth"])
# Verified on unknown emails too, so response time does not reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


class RegisterRequest(BaseModel):
    organization: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - the OAuth scheme name


class InviteRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "reviewer", "viewer"]


class ApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str


def _issue(session: Session, settings: Settings, user: User) -> TokenResponse:
    refresh = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    access = create_access_token(
        user.id,
        user.organization_id,
        user.role,
        settings.jwt_secret.get_secret_value(),
        settings.access_token_minutes,
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> TokenResponse:
    """Create an organization and its first admin."""
    rate_limit(
        request, "auth", request.client.host if request.client else "?", settings.auth_rate_limit
    )
    organization = Organization(name=body.organization)
    session.add(organization)
    session.flush()
    user = User(
        organization_id=organization.id,
        email=body.email.casefold(),
        password_hash=hash_password(body.password),
        role="admin",
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise Problem(
            409, "Conflict", "This email is already registered.", "email_taken"
        ) from error
    tokens = _issue(session, settings, user)
    audit(session, organization.id, user.id, "user.register", "user", user.id)
    session.commit()
    return tokens


@router.post("/login")
def login(
    body: LoginRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> TokenResponse:
    rate_limit(request, "auth", body.email.casefold(), settings.auth_rate_limit)
    user = session.scalar(select(User).where(User.email == body.email.casefold()))
    if not verify_password(user.password_hash if user else _DUMMY_HASH, body.password) or not user:
        raise Problem(401, "Not authenticated", "Wrong email or password.", "bad_credentials")
    tokens = _issue(session, settings, user)
    audit(session, user.organization_id, user.id, "user.login", "user", user.id)
    session.commit()
    return tokens


@router.post("/refresh")
def refresh(body: RefreshRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    """Rotate a refresh token. Replaying a used token revokes the user's other tokens."""
    stored = session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == digest(body.refresh_token))
    )
    invalid = Problem(401, "Not authenticated", "The refresh token is invalid.", "bad_refresh")
    if stored is None or stored.expires_at <= datetime.now(UTC):
        raise invalid
    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        for token in session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None)
            )
        ):
            token.revoked_at = now
        session.commit()
        raise invalid
    user = session.get(User, stored.user_id)
    if user is None:
        raise invalid
    stored.revoked_at = now
    tokens = _issue(session, settings, user)
    session.commit()
    return tokens


AdminDep = Annotated[Principal, Depends(require_role("admin"))]


@router.post("/users", status_code=201)
def invite(body: InviteRequest, session: SessionDep, principal: AdminDep) -> dict[str, str]:
    """Add a user to the caller's organization."""
    user = User(
        organization_id=principal.organization_id,
        email=body.email.casefold(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise Problem(
            409, "Conflict", "This email is already registered.", "email_taken"
        ) from error
    audit(session, principal.organization_id, principal.user_id, "user.create", "user", user.id)
    session.commit()
    return {"id": str(user.id), "role": user.role}


@router.post("/api-keys", status_code=201)
def create_api_key(body: ApiKeyRequest, session: SessionDep, principal: AdminDep) -> ApiKeyResponse:
    """Create a key. The value is returned once, and only its hash is stored."""
    key = new_api_key()
    row = ApiKey(user_id=principal.user_id, name=body.name, key_hash=digest(key))
    session.add(row)
    session.flush()
    audit(
        session, principal.organization_id, principal.user_id, "api_key.create", "api_key", row.id
    )
    session.commit()
    return ApiKeyResponse(id=str(row.id), name=row.name, key=key)
