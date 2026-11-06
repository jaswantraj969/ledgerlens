import csv
import io
import json
from decimal import Decimal

import pytest
from evals.synthetic.generate import generate_invoice

from ledgerlens.export.exporters import to_csv, to_json
from ledgerlens.fields import FieldRecord
from ledgerlens.parsing.pdfium import PdfiumParser
from ledgerlens.pipeline import process
from ledgerlens.schema import load_schema
from ledgerlens.verification.normalize import normalize_identifier, normalize_text


def run(seed: int, **options: object) -> tuple[object, dict[str, FieldRecord]]:
    invoice = generate_invoice(seed, **options)  # type: ignore[arg-type]
    records = process(PdfiumParser().parse(invoice.pdf), load_schema("default"))
    return invoice, {record.name: record for record in records}


@pytest.mark.parametrize("seed", range(10))
def test_header_fields_match_truth(seed: int) -> None:
    invoice, fields = run(seed)
    truth = invoice.truth  # type: ignore[attr-defined]
    assert fields["invoice_number"].value_normalized == normalize_identifier(
        truth["invoice_number"]
    )
    assert fields["invoice_date"].value_normalized == truth["invoice_date"]
    assert fields["currency"].value_normalized == truth["currency"]
    assert fields["vendor_name"].value_normalized == normalize_text(truth["vendor_name"])
    for name in ("subtotal", "total_amount"):
        assert Decimal(fields[name].value_normalized or "") == Decimal(truth[name])


def test_absent_tax_stays_null_and_goes_to_review() -> None:
    _, fields = run(1, tax=False)
    assert fields["tax_amount"].value_raw is None
    assert fields["tax_amount"].evidence_status == "not_found"
    assert fields["tax_amount"].decision == "needs_review"


def test_line_items_sum_to_subtotal() -> None:
    invoice, fields = run(2, items=5, tax=True)
    amounts = [record for name, record in fields.items() if name.endswith(".amount")]
    assert len(amounts) == len(invoice.items)  # type: ignore[attr-defined]
    results = {r.rule_id: r.passed for r in fields["subtotal"].validation_results}
    assert results == {
        "subtotal_plus_tax_equals_total": True,
        "line_amounts_sum_to_subtotal": True,
    }


def test_every_field_carries_the_required_record_parts() -> None:
    _, fields = run(3)
    for record in fields.values():
        assert record.evidence_status in {"exact", "fuzzy", "not_found"}
        assert record.risk_score is not None
        assert record.decision in {"auto_accepted", "needs_review"}
        assert "value_present" in record.signals


def test_calibrated_prob_stays_null_without_a_calibrator() -> None:
    _, fields = run(4)
    assert all(record.calibrated_prob is None for record in fields.values())


def test_evidence_box_points_at_the_value() -> None:
    _, fields = run(5)
    evidence = fields["total_amount"].evidence[0]
    assert evidence.text == fields["total_amount"].value_raw
    assert evidence.bbox is not None
    assert evidence.coordinate_system == "pdf_points_top_left"


def test_wrong_total_fails_arithmetic_and_needs_review() -> None:
    invoice = generate_invoice(6, tax=True)
    document = PdfiumParser().parse(invoice.pdf)
    page = document.pages[0]
    index = max(i for i, token in enumerate(page.tokens) if token.text[0].isdigit())
    page.tokens[index] = page.tokens[index].model_copy(update={"text": "1.00"})
    fields = {r.name: r for r in process(document, load_schema("default"))}
    assert fields["total_amount"].decision == "needs_review"
    assert not all(r.passed for r in fields["total_amount"].validation_results)


def test_alternative_schema_comes_from_config_alone() -> None:
    invoice = generate_invoice(7)
    records = process(PdfiumParser().parse(invoice.pdf), load_schema("receipt_minimal"))
    fields = {record.name: record for record in records}
    assert set(fields) == {"merchant", "paid_total"}
    assert Decimal(fields["paid_total"].value_normalized or "") == Decimal(
        invoice.truth["total_amount"] or ""
    )


def test_multi_page_invoice_keeps_all_rows() -> None:
    invoice, fields = run(8, items=40, tax=True)
    amounts = [record for name, record in fields.items() if name.endswith(".amount")]
    assert len(amounts) == 40
    assert {record.evidence[0].page for record in amounts} == {1, 2}
    assert Decimal(fields["total_amount"].value_normalized or "") == Decimal(
        invoice.truth["total_amount"]  # type: ignore[attr-defined]
    )


def test_export_round_trip_keeps_exact_amounts() -> None:
    invoice = generate_invoice(9)
    records = process(PdfiumParser().parse(invoice.pdf), load_schema("default"))
    documents = {invoice.document_id: records}
    exported = json.loads(to_json(documents))[invoice.document_id]
    total = next(row for row in exported if row["name"] == "total_amount")
    assert total["value_normalized"] == invoice.truth["total_amount"]
    assert isinstance(total["value_normalized"], str)
    rows = list(csv.DictReader(io.StringIO(to_csv(documents))))
    assert len(rows) == len(records)
    assert {row["document_id"] for row in rows} == {invoice.document_id}


def test_csv_neutralises_formula_injection() -> None:
    record = FieldRecord(name="vendor_name", value_raw='=HYPERLINK("x")', value_normalized=None,
                         source="test")  # fmt: skip
    row = next(csv.DictReader(io.StringIO(to_csv({"d": [record]}))))
    assert row["value_raw"].startswith("'=")
