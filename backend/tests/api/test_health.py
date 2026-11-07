import json
from pathlib import Path
from typing import cast

import pytest
import redis
import structlog
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ledgerlens.core.logs import REDACTED, redact
from tests.api.conftest import Account


def test_live(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "live"}


def test_ready_reports_each_dependency_and_a_missing_worker(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["checks"] == {"database": True, "redis": True, "storage": True, "worker": False}


def test_ready_reflects_redis_failure(client: TestClient) -> None:
    good = client.app.state.redis  # type: ignore[attr-defined]
    client.app.state.redis = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=1)  # type: ignore[attr-defined]
    response = client.get("/health/ready")
    client.app.state.redis = good  # type: ignore[attr-defined]
    assert response.status_code == 503
    assert response.json()["checks"]["redis"] is False


def test_ready_reflects_database_failure(client: TestClient) -> None:
    good = client.app.state.session_factory  # type: ignore[attr-defined]
    broken = create_engine(
        "postgresql+psycopg://x:y@127.0.0.1:1/z", connect_args={"connect_timeout": 1}
    )
    client.app.state.session_factory = sessionmaker(broken)  # type: ignore[attr-defined]
    response = client.get("/health/ready")
    client.app.state.session_factory = good  # type: ignore[attr-defined]
    assert response.status_code == 503
    assert response.json()["checks"]["database"] is False


def test_ready_reflects_storage_failure(client: TestClient, tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    client.app.state.storage.root = blocker  # type: ignore[attr-defined]
    response = client.get("/health/ready")
    assert response.json()["checks"]["storage"] is False


def test_metrics_exposes_request_latency(client: TestClient) -> None:
    client.get("/health/live")
    body = client.get("/metrics").text
    assert "ledgerlens_request_seconds_count" in body


def test_unknown_route_is_a_problem_response(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_openapi_documents_the_api(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/auth/login", "/documents", "/documents/{document_id}", "/jobs/{job_id}"} <= set(paths)


@pytest.mark.parametrize("key", ["password", "value_raw", "text", "token", "api_key"])
def test_redaction_processor_hides_sensitive_keys(key: str) -> None:
    event = redact(None, "info", {"event": "x", key: "SECRET", "status": 200})
    assert event[key] == REDACTED
    assert event["status"] == 200


def test_logs_hold_no_secrets_or_document_content(
    client: TestClient, admin: Account, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    structlog.get_logger().info("field", value_raw="TOTAL 1,234.00", password="hunter2")
    client.post("/auth/login", json={"email": admin.email, "password": "the-wrong-password"})
    output = capsys.readouterr().out
    assert "1,234.00" not in output
    assert "hunter2" not in output
    assert "the-wrong-password" not in output
    assert admin.tokens["access_token"] not in output
    line = next(item for item in output.splitlines() if '"field"' in item)
    assert cast(dict[str, str], json.loads(line))["value_raw"] == REDACTED
