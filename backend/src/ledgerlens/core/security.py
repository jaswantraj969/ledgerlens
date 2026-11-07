"""Password hashing, tokens and API keys."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

ALGORITHM = "HS256"
API_KEY_PREFIX = "llk_"
_hasher = PasswordHasher()


class TokenError(Exception):
    """A token is invalid, expired, or of the wrong type."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def digest(secret: str) -> str:
    """Hash for high-entropy tokens and API keys, stored in place of the value."""
    return hashlib.sha256(secret.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def create_access_token(
    user_id: uuid.UUID, organization_id: uuid.UUID, role: str, secret: str, minutes: int
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    try:
        claims: dict[str, Any] = jwt.decode(
            token, secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "org"]}
        )
    except jwt.InvalidTokenError as error:
        raise TokenError(type(error).__name__) from error
    if claims.get("type") != "access":
        raise TokenError("wrong token type")
    return claims
