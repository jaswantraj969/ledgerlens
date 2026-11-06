"""Rule-based extractor. The offline default: needs no model and no network.

Each line is claimed by the field whose longest label it contains, so "Subtotal" can never be
read as "Total". The value is then taken from the tokens after the label.
"""

import re

from ledgerlens.extraction.layout import Line, build_lines
from ledgerlens.fields import Evidence, FieldRecord
from ledgerlens.parsing.model import ParsedDocument, Token
from ledgerlens.schema import FieldSpec, FieldType, LineItemSpec, Schema
from ledgerlens.verification.normalize import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_identifier,
    normalize_text,
)

SOURCE = "deterministic"
_LABEL_NOISE = re.compile(r"^[:#.\-]+$")
_MAX_DATE_TOKENS = 4


class DeterministicExtractor:
    name = SOURCE

    def extract(self, document: ParsedDocument, schema: Schema) -> list[FieldRecord]:
        lines = build_lines(document)
        claims = _claim_lines(lines, schema)
        records = [
            self._extract_field(spec, lines, claims.get(spec.name, [])) for spec in schema.fields
        ]
        if schema.line_items is not None:
            records.extend(_extract_line_items(lines, schema.line_items))
        return records

    def _extract_field(
        self, spec: FieldSpec, lines: list[Line], claimed: list[tuple[Line, int]]
    ) -> FieldRecord:
        if spec.position == "first_line" and lines:
            return _record(spec.name, lines[0], lines[0].tokens)
        for line, label_end in reversed(claimed) if spec.take == "last" else claimed:
            value = _value_tokens(spec.type, line.tokens_after(label_end))
            if value:
                return _record(spec.name, line, value)
        if spec.scan:
            for line in lines:
                for token in line.tokens:
                    if normalize_currency(token.text) is not None:
                        return _record(spec.name, line, (token,))
        return FieldRecord(name=spec.name, value_raw=None, value_normalized=None, source=SOURCE)


def _claim_lines(lines: list[Line], schema: Schema) -> dict[str, list[tuple[Line, int]]]:
    labels = sorted(
        ((label, spec.name) for spec in schema.fields for label in spec.labels),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    patterns = [
        (re.compile(rf"(?<!\w){re.escape(label)}(?!\w)", re.IGNORECASE), name)
        for label, name in labels
    ]
    claims: dict[str, list[tuple[Line, int]]] = {}
    for line in lines:
        for pattern, name in patterns:
            if match := pattern.search(line.text):
                claims.setdefault(name, []).append((line, match.end()))
                break
    return claims


def _value_tokens(field_type: FieldType, tokens: tuple[Token, ...]) -> tuple[Token, ...]:
    tokens = tuple(token for token in tokens if not _LABEL_NOISE.match(token.text))
    if not tokens:
        return ()
    if field_type == "amount":
        amounts = [token for token in tokens if normalize_amount(token.text) is not None]
        return (amounts[-1],) if amounts else ()
    if field_type == "currency":
        return next(((t,) for t in tokens if normalize_currency(t.text) is not None), ())
    if field_type == "date":
        for size in range(min(_MAX_DATE_TOKENS, len(tokens)), 0, -1):
            window = tokens[:size]
            if normalize_date(" ".join(token.text for token in window)) is not None:
                return window
        return ()
    if field_type == "identifier":
        return (tokens[0],)
    return tokens


def _record(name: str, line: Line, tokens: tuple[Token, ...]) -> FieldRecord:
    raw = " ".join(token.text for token in tokens)
    return FieldRecord(
        name=name,
        value_raw=raw,
        value_normalized=None,
        source=SOURCE,
        evidence=[
            Evidence(
                page=line.page,
                text=token.text,
                bbox=token.bbox,
                coordinate_system=line.coordinate_system,
                confidence=token.confidence,
            )
            for token in tokens
        ],
    )


def normalized_value(field_type: FieldType, raw: str | None) -> str | None:
    """Canonical string for a raw value, or None if it does not parse as `field_type`."""
    if raw is None:
        return None
    if field_type == "amount":
        amount = normalize_amount(raw)
        return None if amount is None else str(amount)
    if field_type == "date":
        parsed = normalize_date(raw)
        return None if parsed is None else parsed.isoformat()
    if field_type == "currency":
        return normalize_currency(raw)
    if field_type == "identifier":
        return normalize_identifier(raw) or None
    return normalize_text(raw) or None


def _extract_line_items(lines: list[Line], spec: LineItemSpec) -> list[FieldRecord]:
    records: list[FieldRecord] = []
    in_table = False
    row = 0
    for line in lines:
        text = normalize_text(line.text)
        words = set(text.split())
        if not in_table:
            in_table = all(label in words for label in spec.header_labels[:1]) and any(
                label in words for label in spec.header_labels[1:]
            )
            continue
        if words & set(spec.end_labels):
            break
        cells = _row_cells(line.tokens)
        if cells is None:
            continue
        for name, tokens in cells.items():
            records.append(_record(f"line_items[{row}].{name}", line, tokens))
        row += 1
    return records


def _row_cells(tokens: tuple[Token, ...]) -> dict[str, tuple[Token, ...]] | None:
    """Split a row into description, quantity, unit_price and amount from the right."""
    if len(tokens) < 4:
        return None
    description, quantity, unit_price, amount = tokens[:-3], tokens[-3], tokens[-2], tokens[-1]
    if any(normalize_amount(token.text) is None for token in (quantity, unit_price, amount)):
        return None
    return {
        "description": description,
        "quantity": (quantity,),
        "unit_price": (unit_price,),
        "amount": (amount,),
    }
