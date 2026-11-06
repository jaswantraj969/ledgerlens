"""In-process pipeline: parse, extract, verify, score, route."""

import re

from ledgerlens.confidence.features import build_features
from ledgerlens.confidence.risk import route
from ledgerlens.extraction.deterministic import DeterministicExtractor, normalized_value
from ledgerlens.extraction.layout import build_lines
from ledgerlens.fields import FieldRecord
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.schema import FieldType, Schema
from ledgerlens.verification.evidence import assess_evidence
from ledgerlens.verification.rules import check_arithmetic

_LINE_CELL = re.compile(r"^line_items\[\d+\]\.(\w+)$")
_LINE_TYPES: dict[str, FieldType] = {
    "description": "text",
    "quantity": "amount",
    "unit_price": "amount",
    "amount": "amount",
}


def field_type(schema: Schema, name: str) -> FieldType:
    if match := _LINE_CELL.match(name):
        return _LINE_TYPES[match[1]]
    spec = schema.field(name)
    if spec is None:
        raise KeyError(name)
    return spec.type


def process(document: ParsedDocument, schema: Schema) -> list[FieldRecord]:
    records = DeterministicExtractor().extract(document, schema)
    lines = build_lines(document)
    for record in records:
        kind = field_type(schema, record.name)
        record.value_normalized = normalized_value(kind, record.value_raw)
        assess_evidence(record, lines, is_amount=kind == "amount")
    check_arithmetic(records)
    for record in records:
        route(record)
        record.signals.update(build_features(record))
    return records
