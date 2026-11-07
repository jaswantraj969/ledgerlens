"""Request dependencies: database session, caller identity, roles and rate limits."""

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

import redis
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlens.core.config import Settings
from ledgerlens.core.errors import Problem
from ledgerlens.core.security import TokenError, decode_access_token, digest
from ledgerlens.db.models import ApiKey, User
from ledgerlens.db.repositories import DocumentRepository


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
_unauthorized = Problem(401, "Not authenticated", "Valid credentials are required.", "unauthorized")


def _from_api_key(session: Session, key: str) -> Principal:
    row = session.execute(
        select(ApiKey, User)
        .join(User, ApiKey.user_id == User.id)
        .where(ApiKey.key_hash == digest(key), ApiKey.revoked_at.is_(None))
    ).first()
    if row is None:
        raise _unauthorized
    _, user = row
    return Principal(user.id, user.organization_id, user.role)


def get_principal(
    session: SessionDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> Principal:
    if x_api_key:
        return _from_api_key(session, x_api_key)
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized
    try:
        claims = decode_access_token(
            authorization.removeprefix("Bearer "), settings.jwt_secret.get_secret_value()
        )
        return Principal(uuid.UUID(claims["sub"]), uuid.UUID(claims["org"]), claims["role"])
    except (TokenError, KeyError, ValueError) as error:
        raise _unauthorized from error


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_role(*roles: str) -> Callable[[Principal], Principal]:
    def check(principal: PrincipalDep) -> Principal:
        if principal.role not in roles:
            raise Problem(403, "Forbidden", "Your role does not allow this.", "forbidden")
        return principal

    return check


def documents(session: SessionDep, principal: PrincipalDep) -> DocumentRepository:
    return DocumentRepository(session, principal.organization_id)


DocumentsDep = Annotated[DocumentRepository, Depends(documents)]


def rate_limit(request: Request, scope: str, identity: str, limit: int) -> None:
    """Fixed-window counter in Redis. Without Redis the request fails closed."""
    settings = get_settings(request)
    key = f"ratelimit:{scope}:{digest(identity)}"
    client: redis.Redis = request.app.state.redis
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, settings.rate_window_seconds)
    except redis.RedisError as error:
        raise Problem(
            503, "Service unavailable", "Rate limiter is unavailable.", "redis_unavailable"
        ) from error
    if count > limit:
        raise Problem(429, "Too many requests", "Rate limit exceeded.", "rate_limited")
