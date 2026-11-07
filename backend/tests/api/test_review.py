"""Review, queue, page images, export and the evaluation report, on real PostgreSQL and Redis."""

import csv
import io
import json
import uuid
from pathlib import Path

import pytest
from evals.synthetic.generate import generate_invoice
from fastapi.testclient import TestClient
from sqlalchemy import select

from ledgerlens.core.config import Settings
from ledgerlens.db.models import AuditLog, Job
from tests.api.conftest import Account, add_user
from tests.api.test_worker import context_for, drain

PDF = generate_invoice(11, layout="classic").pdf


def processed(client: TestClient, account: Account, settings: Settings, seed: int = 11) -> dict:  # type: ignore[type-arg]
    data = PDF if seed == 11 else generate_invoice(seed, layout="modern").pdf
    body = client.post(
        "/documents", files={"file": ("invoice.pdf", data, "application/pdf")},
        headers=account.headers,
    ).json()  # fmt: skip
    drain(context_for(settings))
    response = client.get(f"/documents/{body['id']}/fields", headers=account.headers)
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def review(client: TestClient, account: Account, field_id: str, **body: object):  # type: ignore[no-untyped-def]
    return client.post(f"/fields/{field_id}/review", json=body, headers=account.headers)


def by_name(document: dict, name: str) -> dict:  # type: ignore[type-arg]
    return next(f for f in document["fields"] if f["name"] == name)


def test_fields_come_with_evidence_boxes_and_checks(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    assert document["provider"] == "deterministic"
    assert document["pages"][0]["coordinate_system"] == "pdf_points_top_left"
    total = by_name(document, "total_amount")
    assert total["value_raw"] and total["evidence"]
    assert len(total["evidence"][0]["bbox"]) == 4
    assert any(v["rule_id"] for v in total["validations"])
    assert {f["decision"] for f in document["fields"]} <= {"auto_accepted", "needs_review"}


def test_fields_before_processing_are_not_ready(client: TestClient, admin: Account) -> None:
    body = client.post(
        "/documents", files={"file": ("a.pdf", PDF, "application/pdf")}, headers=admin.headers
    ).json()
    response = client.get(f"/documents/{body['id']}/fields", headers=admin.headers)
    assert response.status_code == 409
    assert response.json()["code"] == "not_ready"


def test_other_organizations_see_nothing(
    client: TestClient, admin: Account, other_admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    field_id = document["fields"][0]["id"]
    document_id = document["document_id"]
    for path in (f"/documents/{document_id}/fields", f"/documents/{document_id}/export",
                 f"/documents/{document_id}/pages/1/image"):  # fmt: skip
        assert client.get(path, headers=other_admin.headers).status_code == 404
    assert review(client, other_admin, field_id, action="approve").status_code == 404
    assert client.get("/review/queue", headers=other_admin.headers).json() == []


def test_approve_reject_and_correct_record_decisions(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    total, subtotal, number = (by_name(document, n)["id"] for n in
                               ("total_amount", "subtotal", "invoice_number"))  # fmt: skip
    corrected = review(client, admin, total, action="correct", value="1,234.50").json()
    assert (corrected["decision"], corrected["final_value"]) == ("corrected", "1,234.50")
    assert corrected["value_raw"] != "1,234.50", "the extracted value is kept"
    rejected = review(client, admin, subtotal, action="reject").json()
    assert (rejected["decision"], rejected["final_value"]) == ("rejected", None)
    approved = review(client, admin, number, action="approve").json()
    assert approved["decision"] == "approved" and approved["final_value"] == approved["value_raw"]


@pytest.mark.parametrize(
    ("body", "code"),
    [({"action": "correct"}, "value_required"),
     ({"action": "correct", "value": "  "}, "value_required"),
     ({"action": "correct", "value": "not money"}, "value_invalid")],
)  # fmt: skip
def test_bad_corrections_are_refused(
    client: TestClient,
    admin: Account,
    settings: Settings,
    body: dict,
    code: str,  # type: ignore[type-arg]
) -> None:
    document = processed(client, admin, settings)
    response = review(client, admin, by_name(document, "total_amount")["id"], **body)
    assert response.status_code == 422
    assert response.json()["code"] == code


def test_viewers_cannot_review(client: TestClient, admin: Account, settings: Settings) -> None:
    document = processed(client, admin, settings)
    viewer = add_user(client, admin, "viewer")
    response = review(client, viewer, document["fields"][0]["id"], action="approve")
    assert response.status_code == 403
    assert client.get(f"/documents/{document['document_id']}/fields",
                      headers=viewer.headers).status_code == 200  # fmt: skip


def test_reviewing_every_pending_field_completes_the_document(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    pending = [f["id"] for f in document["fields"] if f["decision"] == "needs_review"]
    assert pending, "the synthetic invoice leaves something for review"
    for field_id in pending:
        assert review(client, admin, field_id, action="reject").status_code == 200
    status = client.get(f"/documents/{document['document_id']}", headers=admin.headers).json()
    assert status["status"] == "completed"
    with context_for(settings).sessions() as session:
        job = session.scalar(
            select(Job).where(Job.document_id == uuid.UUID(document["document_id"]))
        )
        assert job is not None and job.state == "completed"


def test_the_queue_lists_pending_fields_highest_risk_first(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    processed(client, admin, settings)
    processed(client, admin, settings, seed=12)
    queue = client.get("/review/queue?limit=200", headers=admin.headers).json()
    risks = [item["risk_score"] for item in queue]
    assert queue and risks == sorted(risks, reverse=True)
    first = queue[0]["field_id"]
    review(client, admin, first, action="approve")
    after = client.get("/review/queue?limit=200", headers=admin.headers).json()
    assert first not in {item["field_id"] for item in after}
    assert len(after) == len(queue) - 1


def test_page_images_render_pdf_pages(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    image = client.get(f"/documents/{document['document_id']}/pages/1/image", headers=admin.headers)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")
    missing = client.get(
        f"/documents/{document['document_id']}/pages/9/image", headers=admin.headers
    )
    assert missing.status_code == 404


def test_export_uses_final_values_and_audit_keeps_hashes_only(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    total = by_name(document, "total_amount")["id"]
    subtotal = by_name(document, "subtotal")["id"]
    review(client, admin, total, action="correct", value="99.95")
    review(client, admin, subtotal, action="reject")
    document_id = document["document_id"]

    exported = json.loads(client.get(f"/documents/{document_id}/export",
                                     headers=admin.headers).text)[document_id]  # fmt: skip
    values = {r["name"]: (r["value_raw"], r["value_normalized"], r["decision"]) for r in exported}
    assert values["total_amount"] == ("99.95", "99.95", "corrected")
    assert values["subtotal"] == (None, None, "rejected")
    rows = list(csv.DictReader(io.StringIO(client.get(
        f"/documents/{document_id}/export?format=csv", headers=admin.headers).text)))  # fmt: skip
    assert {r["name"]: r["value_raw"] for r in rows}["total_amount"] == "99.95"

    with context_for(settings).sessions() as session:
        entries = session.scalars(select(AuditLog).where(AuditLog.action == "field.correct")).all()
    assert len(entries) == 1 and entries[0].after_hash and len(entries[0].after_hash) == 64
    assert "99.95" not in json.dumps([vars(e) for e in entries], default=str)


def test_the_report_serves_results_files_and_flags_missing_ones(
    client: TestClient, admin: Account, settings: Settings, tmp_path: Path
) -> None:
    report = client.get("/evaluation/report", headers=admin.headers).json()
    comparison = report["validation_comparison"]
    assert comparison["available"] is True
    assert comparison["source"] == "evals/results/dev/cord_validation_comparison_v1_1_1.json"
    assert {"S1", "S4h"} <= {s["system"] for s in comparison["data"]["systems"]}
    assert report["s1_test"]["data"]["split"] == "test"
    client.app.state.settings = settings.model_copy(update={"results_dir": tmp_path})  # type: ignore[attr-defined]
    empty = client.get("/evaluation/report", headers=admin.headers).json()
    assert empty["validation_comparison"] == {
        "available": False, "source": "evals/results/dev/cord_validation_comparison_v1_1_1.json",
    }  # fmt: skip
    assert client.get("/evaluation/report").status_code == 401
