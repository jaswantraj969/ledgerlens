"""JSON and CSV export. Amounts stay strings so no value passes through a float."""

import csv
import io
import json

from ledgerlens.fields import FieldRecord

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_CSV_COLUMNS = ("document_id", "name", "value_raw", "value_normalized", "evidence_status",
                "risk_score", "calibrated_prob", "decision")  # fmt: skip


def to_json(documents: dict[str, list[FieldRecord]]) -> str:
    payload = {
        document_id: [record.model_dump(mode="json") for record in records]
        for document_id, records in documents.items()
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def to_csv(documents: dict[str, list[FieldRecord]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    for document_id, records in documents.items():
        for record in records:
            writer.writerow(
                [
                    _safe_cell(document_id),
                    _safe_cell(record.name),
                    _safe_cell(record.value_raw),
                    _safe_cell(record.value_normalized),
                    record.evidence_status,
                    record.risk_score,
                    record.calibrated_prob,
                    record.decision,
                ]
            )
    return buffer.getvalue()


def _safe_cell(value: str | None) -> str | None:
    """Neutralise spreadsheet formulas: cell text comes from untrusted documents."""
    if value and value.startswith(_FORMULA_PREFIXES) and not _is_number(value):
        return "'" + value
    return value


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
