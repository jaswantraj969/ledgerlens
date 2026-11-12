"""The document audit trail (A5) and batch export (A6), on real PostgreSQL and Redis."""

import csv
import io
import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from ledgerlens.core.config import Settings
from ledgerlens.db.models import AuditLog, User
from tests.api.conftest import Account, add_user
from tests.api.test_review import by_name, processed, review
from tests.api.test_worker import context_for


def reviewed(client: TestClient, account: Account, settings: Settings, seed: int = 11) -> str:
    """A processed document with every pending field rejected, so its status is completed."""
    document = processed(client, account, settings, seed=seed)
    for field in document["fields"]:
        if field["decision"] == "needs_review":
            assert review(client, account, field["id"], action="reject").status_code == 200
    status = client.get(f"/documents/{document['document_id']}", headers=account.headers).json()
    assert status["status"] == "completed"
    return str(document["document_id"])


def export(client: TestClient, account: Account | None, ids: list[str], format: str = "json"):  # type: ignore[no-untyped-def]
    headers = account.headers if account else {}
    return client.post(
        "/documents/export", json={"document_ids": ids, "format": format}, headers=headers
    )


# Audit trail


def test_audit_trail_lists_events_newest_first_with_old_and_new_values(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    document_id = document["document_id"]
    total = by_name(document, "total_amount")
    number = by_name(document, "invoice_number")
    review(client, admin, total["id"], action="correct", value="99.95")
    review(client, admin, total["id"], action="correct", value="100.00")
    review(client, admin, number["id"], action="approve")

    response = client.get(f"/documents/{document_id}/audit", headers=admin.headers)
    assert response.status_code == 200, response.text
    events = response.json()
    assert [e["action"] for e in events] == [
        "field.approve", "field.correct", "field.correct", "document.upload",
    ]  # fmt: skip
    times = [e["created_at"] for e in events]
    assert times == sorted(times, reverse=True)
    assert {e["actor_email"] for e in events} == {admin.email}
    approve, second, first, upload = events
    assert (approve["field_name"], approve["old_value"], approve["new_value"]) == (
        "invoice_number", number["value_raw"], number["value_raw"],
    )  # fmt: skip
    assert (first["field_name"], first["old_value"], first["new_value"]) == (
        "total_amount", total["value_raw"], "99.95",
    )  # fmt: skip
    assert (second["old_value"], second["new_value"]) == ("99.95", "100.00")
    assert (upload["entity"], upload["field_name"], upload["old_value"]) == ("document", None, None)


def test_a_rejection_has_no_new_value(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    subtotal = by_name(document, "subtotal")
    review(client, admin, subtotal["id"], action="reject")
    events = client.get(f"/documents/{document['document_id']}/audit", headers=admin.headers).json()
    assert (events[0]["action"], events[0]["old_value"], events[0]["new_value"]) == (
        "field.reject", subtotal["value_raw"], None,
    )  # fmt: skip


def test_audit_trail_never_shows_another_organizations_events(
    client: TestClient, admin: Account, other_admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    document_id = document["document_id"]
    # The other organization cannot read this document's trail at all.
    assert (
        client.get(f"/documents/{document_id}/audit", headers=other_admin.headers).status_code
        == 404
    )
    # The other organization reviews its own copy of the same file: separate events.
    theirs = processed(client, other_admin, settings)
    review(
        client, other_admin, by_name(theirs, "total_amount")["id"], action="correct", value="5.00"
    )
    # Even an event of the other organization that names this document is not shown.
    with context_for(settings).sessions() as session:
        other_org = session.scalar(
            select(User.organization_id).where(User.email == other_admin.email)
        )
        assert other_org is not None
        session.add(
            AuditLog(
                organization_id=other_org,
                actor_id=None,
                action="document.planted",
                entity="document",
                entity_id=document_id,
            )
        )
        session.commit()
    events = client.get(f"/documents/{document_id}/audit", headers=admin.headers).json()
    assert [e["action"] for e in events] == ["document.upload"]
    assert {e["actor_email"] for e in events} == {admin.email}
    mine = client.get(f"/documents/{theirs['document_id']}/audit", headers=admin.headers)
    assert mine.status_code == 404


def test_viewers_can_read_the_audit_trail(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    viewer = add_user(client, admin, "viewer")
    response = client.get(f"/documents/{document['document_id']}/audit", headers=viewer.headers)
    assert response.status_code == 200
    assert response.json()[0]["action"] == "document.upload"


def test_the_audit_trail_needs_credentials(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document = processed(client, admin, settings)
    assert client.get(f"/documents/{document['document_id']}/audit").status_code == 401


# Batch export


def test_batch_export_returns_every_document_in_the_single_export_format(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    first, second = reviewed(client, admin, settings, 11), reviewed(client, admin, settings, 12)
    response = export(client, admin, [first, second, first])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    exported = json.loads(response.text)
    assert list(exported) == [first, second], "duplicates are exported once, in request order"
    for document_id in (first, second):
        single = json.loads(
            client.get(f"/documents/{document_id}/export", headers=admin.headers).text
        )
        assert exported[document_id] == single[document_id]

    as_csv = export(client, admin, [first, second], format="csv")
    assert as_csv.status_code == 200
    assert as_csv.headers["content-type"].startswith("text/csv")
    assert 'filename="ledgerlens-export.csv"' in as_csv.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(as_csv.text)))
    single_csv = client.get(f"/documents/{first}/export?format=csv", headers=admin.headers).text
    assert as_csv.text.splitlines()[0] == single_csv.splitlines()[0], "same columns"
    assert {r["document_id"] for r in rows} == {first, second}


def test_batch_export_refuses_documents_of_another_organization(
    client: TestClient, admin: Account, other_admin: Account, settings: Settings
) -> None:
    mine = reviewed(client, admin, settings, 11)
    theirs = reviewed(client, other_admin, settings, 12)
    response = export(client, admin, [mine, theirs])
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert theirs in body["detail"] and mine not in body["detail"]
    unknown = str(uuid.uuid4())
    assert export(client, admin, [unknown]).json()["code"] == "not_found"


def test_batch_export_refuses_documents_that_are_not_reviewed(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    done = reviewed(client, admin, settings, 11)
    pending = processed(client, admin, settings, seed=12)["document_id"]
    response = export(client, admin, [done, pending])
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "not_reviewed"
    assert pending in body["detail"] and done not in body["detail"]


def test_batch_export_enforces_the_size_cap(client: TestClient, admin: Account) -> None:
    ids = [str(uuid.uuid4()) for _ in range(51)]
    response = export(client, admin, ids)
    assert response.status_code == 413
    assert response.json()["code"] == "batch_too_large"
    assert export(client, admin, []).status_code == 422


def test_batch_export_needs_credentials(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    document_id = reviewed(client, admin, settings)
    assert export(client, None, [document_id]).status_code == 401
