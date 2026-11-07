import json
from io import BytesIO
from pathlib import Path

import pytest
import redis
from evals.synthetic.generate import generate_invoice, render_image
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from rq import Queue
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ledgerlens.core.config import Settings
from ledgerlens.db.models import AuditLog, Document, Job
from tests.api.conftest import REDIS_URL, Account, add_user

PDF = generate_invoice(1, layout="classic").pdf
FILES = {"file": ("invoice.pdf", PDF, "application/pdf")}


def upload(client: TestClient, account: Account, files: dict | None = None):  # type: ignore[no-untyped-def,type-arg]
    return client.post("/documents", files=files or FILES, headers=account.headers)


def code(response) -> str:  # type: ignore[no-untyped-def]
    assert response.headers["content-type"].startswith("application/problem+json")
    return str(response.json()["code"])


def count(client: TestClient, model: type) -> int:
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_pdf_upload_creates_document_and_queued_job(client: TestClient, admin: Account) -> None:
    response = upload(client, admin)
    assert response.status_code == 201
    body = response.json()
    assert body["mime"] == "application/pdf"
    assert body["pages"] == 1
    assert body["duplicate"] is False
    job = client.get(f"/jobs/{body['job_id']}", headers=admin.headers).json()
    assert job["state"] == "queued"
    queued = Queue("ledgerlens", connection=redis.Redis.from_url(REDIS_URL))
    assert body["job_id"] in queued.job_ids


def test_png_and_jpeg_uploads_are_accepted(client: TestClient, admin: Account) -> None:
    png = render_image(PDF, dpi=60)
    assert upload(client, admin, {"file": ("r.png", png, "image/png")}).status_code == 201
    buffer = BytesIO()
    from PIL import Image

    Image.open(BytesIO(png)).convert("RGB").save(buffer, format="JPEG")
    jpg = {"file": ("r.jpg", buffer.getvalue(), "image/jpeg")}
    assert upload(client, admin, jpg).json()["mime"] == "image/jpeg"


def test_duplicate_upload_returns_the_same_document(client: TestClient, admin: Account) -> None:
    first, second = upload(client, admin), upload(client, admin)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["duplicate"] is True
    assert second.json()["job_id"] == first.json()["job_id"]
    assert count(client, Document) == 1
    assert count(client, Job) == 1


def test_same_file_in_two_organizations_is_two_documents(
    client: TestClient, admin: Account, other_admin: Account
) -> None:
    assert upload(client, admin).json()["id"] != upload(client, other_admin).json()["id"]


def test_disguised_executable_is_rejected(client: TestClient, admin: Account) -> None:
    files = {"file": ("invoice.pdf", b"MZ\x90\x00" + b"\x00" * 200, "application/pdf")}
    response = upload(client, admin, files)
    assert response.status_code == 415
    assert code(response) == "unsupported_type"
    assert count(client, Document) == 0


def test_extension_must_match_the_content(client: TestClient, admin: Account) -> None:
    response = upload(client, admin, {"file": ("invoice.png", PDF, "image/png")})
    assert response.status_code == 415
    assert code(response) == "extension_mismatch"


def test_oversize_file_is_rejected(client: TestClient, admin: Account, settings: Settings) -> None:
    client.app.state.settings = settings.model_copy(update={"max_upload_bytes": 100})  # type: ignore[attr-defined]
    response = upload(client, admin)
    assert response.status_code == 413
    assert code(response) == "file_too_large"


def test_empty_file_is_rejected(client: TestClient, admin: Account) -> None:
    response = upload(client, admin, {"file": ("a.pdf", b"", "application/pdf")})
    assert code(response) == "file_empty"


def test_truncated_pdf_is_rejected(client: TestClient, admin: Account) -> None:
    response = upload(client, admin, {"file": ("a.pdf", b"%PDF-1.7\nbroken", "application/pdf")})
    assert response.status_code == 400
    assert code(response) == "pdf_malformed"


def test_encrypted_pdf_is_rejected(client: TestClient, admin: Account) -> None:
    writer = PdfWriter(clone_from=PdfReader(BytesIO(PDF)))
    writer.encrypt("secret")
    buffer = BytesIO()
    writer.write(buffer)
    response = upload(client, admin, {"file": ("a.pdf", buffer.getvalue(), "application/pdf")})
    assert response.status_code == 400
    assert code(response) == "pdf_encrypted"


def test_too_many_pages_is_rejected(client: TestClient, admin: Account, settings: Settings) -> None:
    client.app.state.settings = settings.model_copy(update={"max_pages": 1})  # type: ignore[attr-defined]
    two_pages = generate_invoice(2, layout="classic", items=40).pdf
    response = upload(client, admin, {"file": ("a.pdf", two_pages, "application/pdf")})
    assert code(response) == "too_many_pages"


def test_corrupt_image_is_rejected(client: TestClient, admin: Account) -> None:
    data = b"\x89PNG\r\n\x1a\n" + b"junk" * 10
    response = upload(client, admin, {"file": ("a.png", data, "image/png")})
    assert code(response) == "image_malformed"


@pytest.mark.parametrize(
    "name",
    ["../../etc/passwd.pdf", "..\\..\\windows\\evil.pdf", "/abs/path.pdf", "C:\\x\\y.pdf"],
)
def test_path_traversal_in_the_filename_is_neutralised(
    client: TestClient, admin: Account, settings: Settings, name: str
) -> None:
    response = upload(client, admin, {"file": (name, PDF, "application/pdf")})
    assert response.status_code == 201
    filename = response.json()["filename"]
    assert "/" not in filename
    assert "\\" not in filename
    assert ".." not in filename
    stored = [p for p in Path(settings.storage_dir).rglob("*") if p.is_file()]
    assert len(stored) == 1
    assert stored[0].name == response.json()["sha256"]
    assert stored[0].resolve().is_relative_to(Path(settings.storage_dir).resolve())


def test_batch_reports_each_file(client: TestClient, admin: Account) -> None:
    second = generate_invoice(5, layout="modern").pdf
    response = client.post(
        "/documents/batch",
        files=[
            ("files", ("a.pdf", PDF, "application/pdf")),
            ("files", ("b.pdf", second, "application/pdf")),
            ("files", ("bad.pdf", b"not a pdf", "application/pdf")),
        ],
        headers=admin.headers,
    )
    assert response.status_code == 200
    results = response.json()
    assert [bool(item["document"]) for item in results] == [True, True, False]
    assert results[2]["code"] == "unsupported_type"


def test_list_get_and_delete(client: TestClient, admin: Account, settings: Settings) -> None:
    document = upload(client, admin).json()
    listed = client.get("/documents", headers=admin.headers).json()
    assert [item["id"] for item in listed] == [document["id"]]
    assert client.get(f"/documents/{document['id']}", headers=admin.headers).status_code == 200
    assert client.delete(f"/documents/{document['id']}", headers=admin.headers).status_code == 204
    assert client.get(f"/documents/{document['id']}", headers=admin.headers).status_code == 404
    assert not [p for p in Path(settings.storage_dir).rglob("*") if p.is_file()]


def test_viewer_can_read_but_not_upload_or_delete(client: TestClient, admin: Account) -> None:
    viewer = add_user(client, admin, "viewer")
    document = upload(client, admin).json()
    assert client.get(f"/documents/{document['id']}", headers=viewer.headers).status_code == 200
    assert upload(client, viewer).status_code == 403
    assert client.delete(f"/documents/{document['id']}", headers=viewer.headers).status_code == 403


def test_reviewer_can_upload_but_not_delete(client: TestClient, admin: Account) -> None:
    reviewer = add_user(client, admin, "reviewer")
    document = upload(client, reviewer)
    assert document.status_code == 201
    url = f"/documents/{document.json()['id']}"
    assert client.delete(url, headers=reviewer.headers).status_code == 403


def test_other_organization_gets_404_on_every_document_route(
    client: TestClient, admin: Account, other_admin: Account
) -> None:
    document = upload(client, admin).json()
    url = f"/documents/{document['id']}"
    headers = other_admin.headers
    assert client.get(url, headers=headers).status_code == 404
    assert client.delete(url, headers=headers).status_code == 404
    assert client.get(f"/jobs/{document['job_id']}", headers=headers).status_code == 404
    assert client.get("/documents", headers=headers).json() == []
    assert client.get(url, headers=admin.headers).status_code == 200


def test_api_key_is_scoped_to_its_organization(
    client: TestClient, admin: Account, other_admin: Account
) -> None:
    document = upload(client, admin).json()
    key = client.post("/auth/api-keys", json={"name": "k"}, headers=other_admin.headers).json()
    response = client.get(f"/documents/{document['id']}", headers={"X-API-Key": key["key"]})
    assert response.status_code == 404


def test_upload_rate_limit_triggers(client: TestClient, admin: Account, settings: Settings) -> None:
    client.app.state.settings = settings.model_copy(update={"upload_rate_limit": 2})  # type: ignore[attr-defined]
    assert upload(client, admin).status_code == 201
    assert upload(client, admin).status_code == 200
    response = upload(client, admin)
    assert response.status_code == 429
    assert code(response) == "rate_limited"


def test_upload_is_audited_with_the_request_id(client: TestClient, admin: Account) -> None:
    document = client.post(
        "/documents", files=FILES, headers=admin.headers | {"X-Request-ID": "trace-1"}
    )
    assert document.headers["X-Request-ID"] == "trace-1"
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        row = session.scalars(select(AuditLog).where(AuditLog.action == "document.upload")).one()
    assert row.request_id == "trace-1"
    assert row.after_hash == document.json()["sha256"]


def test_retry_recovers_an_upload_that_missed_the_queue(
    client: TestClient, admin: Account, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis fails after the rate check but before the enqueue: the document is committed."""

    def fail(*_args: object, **_kwargs: object) -> None:
        raise redis.ConnectionError("down")

    with monkeypatch.context() as patch:
        patch.setattr(Queue, "enqueue", fail)
        assert upload(client, admin).status_code == 503
    assert count(client, Document) == 1
    retried = upload(client, admin)
    assert retried.status_code == 200
    assert retried.json()["duplicate"] is True
    assert count(client, Document) == 1
    queued = Queue("ledgerlens", connection=redis.Redis.from_url(REDIS_URL))
    assert queued.job_ids == [retried.json()["job_id"]]


def test_duplicate_upload_does_not_queue_the_job_twice(client: TestClient, admin: Account) -> None:
    upload(client, admin)
    upload(client, admin)
    queued = Queue("ledgerlens", connection=redis.Redis.from_url(REDIS_URL))
    assert len(queued.job_ids) == 1


def test_queue_outage_gives_a_clear_error(client: TestClient, admin: Account) -> None:
    good = client.app.state.redis  # type: ignore[attr-defined]
    client.app.state.redis = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=1)  # type: ignore[attr-defined]
    response = upload(client, admin)
    client.app.state.redis = good  # type: ignore[attr-defined]
    assert response.status_code == 503
    assert code(response) == "redis_unavailable"
    assert json.loads(response.text)["status"] == 503
