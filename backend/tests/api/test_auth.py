from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlens.core.security import digest
from ledgerlens.db.models import ApiKey, AuditLog, User
from tests.api.conftest import JWT_SECRET, PASSWORD, Account, add_user, register


def problem(response) -> str:  # type: ignore[no-untyped-def]
    assert response.headers["content-type"].startswith("application/problem+json")
    return str(response.json()["code"])


def test_register_makes_the_first_user_an_admin(client: TestClient) -> None:
    account = register(client)
    claims = jwt.decode(account.tokens["access_token"], JWT_SECRET, algorithms=["HS256"])
    assert claims["role"] == "admin"
    assert claims["type"] == "access"


def test_password_is_stored_as_argon2(client: TestClient, admin: Account) -> None:
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        user = session.scalar(select(User).where(User.email == admin.email))
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert PASSWORD not in user.password_hash


def test_duplicate_email_is_a_conflict(client: TestClient, admin: Account) -> None:
    response = client.post(
        "/auth/register", json={"organization": "x", "email": admin.email, "password": PASSWORD}
    )
    assert response.status_code == 409
    assert problem(response) == "email_taken"


def test_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"organization": "x", "email": "a@b.test", "password": "short"}
    )
    assert response.status_code == 422
    assert problem(response) == "invalid_request"


def test_login_with_a_wrong_password_fails(client: TestClient, admin: Account) -> None:
    response = client.post("/auth/login", json={"email": admin.email, "password": "wrong" * 3})
    assert response.status_code == 401
    assert problem(response) == "bad_credentials"


def test_login_for_an_unknown_email_gives_the_same_answer(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "no@one.test", "password": "x" * 12})
    assert response.status_code == 401
    assert problem(response) == "bad_credentials"


def test_refresh_rotates_and_old_token_stops_working(client: TestClient, admin: Account) -> None:
    old = admin.tokens["refresh_token"]
    response = client.post("/auth/refresh", json={"refresh_token": old})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != old
    assert client.post("/auth/refresh", json={"refresh_token": old}).status_code == 401


def test_replaying_a_used_refresh_token_revokes_the_family(
    client: TestClient, admin: Account
) -> None:
    old = admin.tokens["refresh_token"]
    newer = client.post("/auth/refresh", json={"refresh_token": old}).json()["refresh_token"]
    assert client.post("/auth/refresh", json={"refresh_token": old}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": newer}).status_code == 401


def test_unknown_refresh_token_is_rejected(client: TestClient) -> None:
    assert client.post("/auth/refresh", json={"refresh_token": "nope"}).status_code == 401


def test_no_credentials_is_unauthorized(client: TestClient) -> None:
    response = client.get("/documents")
    assert response.status_code == 401
    assert problem(response) == "unauthorized"


def forged(admin: Account, **changes: object) -> dict[str, str]:
    claims = jwt.decode(admin.tokens["access_token"], JWT_SECRET, algorithms=["HS256"])
    secret = str(changes.pop("secret", JWT_SECRET))
    token = jwt.encode(claims | changes, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_jwt_signed_with_another_key_is_rejected(client: TestClient, admin: Account) -> None:
    headers = forged(admin, secret="another-key-" + "y" * 40, role="admin")
    assert client.get("/documents", headers=headers).status_code == 401


def test_tampered_jwt_payload_is_rejected(client: TestClient, admin: Account) -> None:
    header, _, signature = admin.tokens["access_token"].split(".")
    payload = "eyJzdWIiOiJ4Iiwib3JnIjoieCIsInJvbGUiOiJhZG1pbiJ9"
    token = f"{header}.{payload}.{signature}"
    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_alg_none_jwt_is_rejected(client: TestClient, admin: Account) -> None:
    claims = jwt.decode(admin.tokens["access_token"], JWT_SECRET, algorithms=["HS256"])
    token = jwt.encode(claims, key="", algorithm="none")
    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_expired_jwt_is_rejected(client: TestClient, admin: Account) -> None:
    headers = forged(admin, exp=datetime.now(UTC) - timedelta(minutes=1))
    assert client.get("/documents", headers=headers).status_code == 401


def test_refresh_style_token_type_is_rejected(client: TestClient, admin: Account) -> None:
    assert client.get("/documents", headers=forged(admin, type="refresh")).status_code == 401


def test_api_key_authenticates_and_is_hashed_at_rest(client: TestClient, admin: Account) -> None:
    created = client.post("/auth/api-keys", json={"name": "ci"}, headers=admin.headers)
    assert created.status_code == 201
    key = created.json()["key"]
    assert client.get("/documents", headers={"X-API-Key": key}).status_code == 200
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        stored = session.scalars(select(ApiKey)).one()
    assert stored.key_hash == digest(key)
    assert key not in stored.key_hash


def test_wrong_api_key_is_rejected(client: TestClient) -> None:
    assert client.get("/documents", headers={"X-API-Key": "llk_wrong"}).status_code == 401


@pytest.mark.parametrize("role", ["reviewer", "viewer"])
def test_only_admins_can_create_api_keys(client: TestClient, admin: Account, role: str) -> None:
    account = add_user(client, admin, role)
    response = client.post("/auth/api-keys", json={"name": "x"}, headers=account.headers)
    assert response.status_code == 403
    assert problem(response) == "forbidden"


def test_only_admins_can_add_users(client: TestClient, admin: Account) -> None:
    viewer = add_user(client, admin, "viewer")
    response = client.post(
        "/auth/users",
        json={"email": "new@example.test", "password": PASSWORD, "role": "admin"},
        headers=viewer.headers,
    )
    assert response.status_code == 403


def test_login_rate_limit_triggers(client: TestClient, admin: Account) -> None:
    limit = client.app.state.settings.auth_rate_limit  # type: ignore[attr-defined]
    for _ in range(limit):
        client.post("/auth/login", json={"email": admin.email, "password": "wrong" * 3})
    response = client.post("/auth/login", json={"email": admin.email, "password": PASSWORD})
    assert response.status_code == 429
    assert problem(response) == "rate_limited"


def test_actions_are_audited(client: TestClient, admin: Account) -> None:
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        actions = set(session.scalars(select(AuditLog.action)))
    assert "user.register" in actions
