"""Webhooks against a real local receiver: creation rules, signatures, retries, final failure."""

import hashlib
import hmac
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from evals.synthetic.generate import generate_invoice
from fastapi.testclient import TestClient
from sqlalchemy import select

from ledgerlens.core.config import Settings
from ledgerlens.db.models import WebhookDelivery
from ledgerlens.workers.webhooks import UnsafeWebhookUrl, check_url, sign
from tests.api.conftest import Account, add_user
from tests.api.test_worker import context_for, drain

PDF = generate_invoice(21, layout="classic").pdf


class Receiver:
    """Records requests; replies with the queued statuses, then 200."""

    def __init__(self) -> None:
        self.requests: list[tuple[dict[str, str], bytes]] = []
        self.statuses: list[int] = []
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                receiver.requests.append((dict(self.headers), body))
                self.send_response(receiver.statuses.pop(0) if receiver.statuses else 200)
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def receiver() -> Iterator[Receiver]:
    server = Receiver()
    yield server
    server.server.shutdown()


def allow_local(client: TestClient, settings: Settings) -> Settings:
    local = settings.model_copy(
        update={"allow_insecure_webhooks": True, "webhook_retry_intervals": [0, 0]}
    )
    client.app.state.settings = local  # type: ignore[attr-defined]
    return local


def create(client: TestClient, account: Account, url: str, events: list[str] | None = None):  # type: ignore[no-untyped-def]
    return client.post("/webhooks", json={"url": url, "events": events or []},
                       headers=account.headers)  # fmt: skip


def process(client: TestClient, account: Account, settings: Settings) -> str:
    body = client.post("/documents", files={"file": ("a.pdf", PDF, "application/pdf")},
                       headers=account.headers).json()  # fmt: skip
    drain(context_for(settings))
    return str(body["id"])


def test_creation_needs_https_and_shows_the_secret_once(client: TestClient, admin: Account) -> None:
    assert create(client, admin, "http://example.com/hook").json()["code"] == "unsafe_url"
    assert create(client, admin, "https://127.0.0.1/hook").json()["code"] == "unsafe_url"
    assert (
        create(client, admin, "https://example.com/h", ["nope"]).json()["code"] == "unknown_event"
    )


def test_secret_is_shown_once_and_hooks_are_scoped(
    client: TestClient, admin: Account, other_admin: Account, settings: Settings,
    receiver: Receiver,
) -> None:  # fmt: skip
    allow_local(client, settings)
    created = create(client, admin, receiver.url)
    assert created.status_code == 201 and created.json()["secret"].startswith("whsec_")
    listed = client.get("/webhooks", headers=admin.headers).json()
    assert [h["id"] for h in listed] == [created.json()["id"]]
    assert "secret" not in listed[0]
    assert client.get("/webhooks", headers=other_admin.headers).json() == []
    hook = created.json()["id"]
    assert client.delete(f"/webhooks/{hook}", headers=other_admin.headers).status_code == 404
    reviewer = add_user(client, admin, "reviewer")
    assert client.get("/webhooks", headers=reviewer.headers).status_code == 403
    assert client.delete(f"/webhooks/{hook}", headers=admin.headers).status_code == 204


def test_a_finished_job_sends_a_signed_delivery_without_field_values(
    client: TestClient, admin: Account, settings: Settings, receiver: Receiver
) -> None:
    local = allow_local(client, settings)
    secret = create(client, admin, receiver.url).json()["secret"]
    document_id = process(client, admin, local)
    drain(context_for(local))  # the delivery job

    assert len(receiver.requests) == 1
    headers, body = receiver.requests[0]
    expected = sign(secret, int(headers["X-LedgerLens-Timestamp"]), body)
    assert hmac.compare_digest(headers["X-LedgerLens-Signature"], expected)
    payload = json.loads(body)
    assert payload["document_id"] == document_id
    assert headers["X-LedgerLens-Event"] == payload["event"]
    assert payload["event"] in ("job.completed", "job.ready_for_review")
    assert set(payload) == {"event", "delivery_id", "job_id", "document_id", "state"}
    tampered = sign(secret, int(headers["X-LedgerLens-Timestamp"]), body + b" ")
    assert tampered != headers["X-LedgerLens-Signature"]
    assert hashlib.sha256(secret.encode()).hexdigest() not in body.decode()


def test_a_failed_delivery_is_retried_until_it_succeeds(
    client: TestClient, admin: Account, settings: Settings, receiver: Receiver
) -> None:
    local = allow_local(client, settings)
    hook = create(client, admin, receiver.url).json()["id"]
    receiver.statuses = [500]
    process(client, admin, local)
    drain(context_for(local))
    deliveries = client.get(f"/webhooks/{hook}/deliveries", headers=admin.headers).json()
    assert [(d["status"], d["attempts"], d["response_status"]) for d in deliveries] == [
        ("delivered", 2, 200)
    ]
    assert len(receiver.requests) == 2
    ids = {json.loads(body)["delivery_id"] for _, body in receiver.requests}
    assert len(ids) == 1, "a retry resends the same delivery"


def test_a_delivery_that_keeps_failing_is_marked_failed(
    client: TestClient, admin: Account, settings: Settings, receiver: Receiver
) -> None:
    local = allow_local(client, settings)
    create(client, admin, receiver.url)
    receiver.statuses = [503, 503, 503]
    process(client, admin, local)
    drain(context_for(local))
    with context_for(local).sessions() as session:
        delivery = session.scalars(select(WebhookDelivery)).one()
    assert (delivery.status, delivery.attempts, delivery.last_error) == ("failed", 3, "HTTP 503")


def test_only_subscribed_events_are_sent(
    client: TestClient, admin: Account, settings: Settings, receiver: Receiver
) -> None:
    local = allow_local(client, settings)
    create(client, admin, receiver.url, ["job.failed"])
    process(client, admin, local)
    drain(context_for(local))
    assert receiver.requests == []


@pytest.mark.parametrize(
    "url", ["https://10.0.0.5/h", "https://192.168.1.2/h", "https://[::1]/h", "ftp://x.test/h"]
)
def test_private_and_odd_targets_are_refused(url: str) -> None:
    with pytest.raises(UnsafeWebhookUrl):
        check_url(url, allow_insecure=False)
