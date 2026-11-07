"""API tests run against real PostgreSQL and Redis, on a dedicated database."""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
import redis
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text

from ledgerlens.api.app import create_app
from ledgerlens.core.config import Settings
from ledgerlens.db.models import Base

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
TEST_DATABASE = "ledgerlens_test"
TEST_REDIS_DB = 15
JWT_SECRET = "test-only-" + "x" * 40


def _env_file() -> dict[str, str]:
    path = ROOT / ".env"
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return {key.strip(): value.strip() for key, value in pairs if not key.startswith("#")}


def _server_url() -> str:
    """Connection string without a database name. CI sets LEDGERLENS_TEST_POSTGRES."""
    if url := os.environ.get("LEDGERLENS_TEST_POSTGRES"):
        return url
    env = _env_file()
    user, password = env.get("POSTGRES_USER", ""), env.get("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{password}@127.0.0.1:5433"


REDIS_URL = os.environ.get("LEDGERLENS_TEST_REDIS", "redis://127.0.0.1:6380") + f"/{TEST_REDIS_DB}"


@pytest.fixture(scope="session")
def database_url() -> str:
    server = _server_url()
    try:
        with psycopg.connect(
            f"{server}/postgres", autocommit=True, connect_timeout=3
        ) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DATABASE,)
            ).fetchone()
            if not exists:
                connection.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    except psycopg.OperationalError as error:
        pytest.fail(f"PostgreSQL is required for API tests: {type(error).__name__}")
    url = f"{server}/{TEST_DATABASE}".replace("postgresql://", "postgresql+psycopg://")
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.attributes["database_url"] = url
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return url


@pytest.fixture
def settings(database_url: str, tmp_path: Path) -> Settings:
    return Settings(
        database_url=database_url,
        redis_url=REDIS_URL,
        jwt_secret=SecretStr(JWT_SECRET),
        storage_dir=tmp_path / "storage",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    connection = redis.Redis.from_url(REDIS_URL)
    connection.flushdb()
    app = create_app(settings)
    with app.state.engine.begin() as database:
        tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        database.execute(text(f"TRUNCATE {tables} CASCADE"))
    with TestClient(app) as test_client:
        yield test_client
    app.state.engine.dispose()


class Account:
    def __init__(self, client: TestClient, email: str, tokens: dict[str, str]) -> None:
        self.client = client
        self.email = email
        self.tokens = tokens

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tokens['access_token']}"}


PASSWORD = "correct-horse-battery"


def register(client: TestClient, name: str = "Org") -> Account:
    email = f"{uuid.uuid4().hex}@example.test"
    response = client.post(
        "/auth/register", json={"organization": name, "email": email, "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return Account(client, email, response.json())


def add_user(client: TestClient, admin: Account, role: str) -> Account:
    email = f"{uuid.uuid4().hex}@example.test"
    created = client.post(
        "/auth/users",
        json={"email": email, "password": PASSWORD, "role": role},
        headers=admin.headers,
    )
    assert created.status_code == 201, created.text
    tokens = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert tokens.status_code == 200, tokens.text
    return Account(client, email, tokens.json())


@pytest.fixture
def admin(client: TestClient) -> Account:
    return register(client, "First")


@pytest.fixture
def other_admin(client: TestClient) -> Account:
    return register(client, "Second")
