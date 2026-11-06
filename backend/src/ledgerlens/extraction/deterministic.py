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
_IGNORED = "__ignored__"
_TRAILING_PUNCTUATION = ".,:;"
_LEADING_QUANTITY = re.compile(r"^(\d{1,3})[xX×]?$")
_UNIT_PRICE_PREFIX = "@"

Claim = tuple[Line, tuple[Token, ...]]


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
        self, spec: FieldSpec, lines: list[Line], claimed: list[Claim]
    ) -> FieldRecord:
        if spec.position == "first_line" and lines:
            return _record(spec.name, lines[0], lines[0].tokens)
        for line, tokens in reversed(claimed) if spec.take == "last" else claimed:
            value = _value_tokens(spec.type, tokens)
            if value:
                return _record(spec.name, line, value, spec.type)
            if spec.type == "amount" and (following := _next_line_amount(lines, line)):
                return _record(spec.name, following[0], following[1], spec.type)
        if spec.scan:
            for line in lines:
                for token in line.tokens:
                    if normalize_currency(token.text) is not None:
                        return _record(spec.name, line, (token,))
        return FieldRecord(name=spec.name, value_raw=None, value_normalized=None, source=SOURCE)


def _claim_lines(lines: list[Line], schema: Schema) -> dict[str, list[Claim]]:
    """Find labels on each line. Longest labels win; a line may hold several fields."""
    labels = sorted(
        [(label, spec.name) for spec in schema.fields for label in spec.labels]
        + [(label, _IGNORED) for label in schema.ignore_labels],
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    patterns = [
        (re.compile(rf"(?<!\w){re.escape(label)}(?!\w)", re.IGNORECASE), name)
        for label, name in labels
    ]
    claims: dict[str, list[Claim]] = {}
    for line in lines:
        spans: list[tuple[int, int, str]] = []
        for pattern, name in patterns:
            for match in pattern.finditer(line.text):
                if all(match.end() <= s or match.start() >= e for s, e, _ in spans):
                    spans.append((match.start(), match.end(), name))
        spans.sort()
        for index, (_, end, name) in enumerate(spans):
            stop = spans[index + 1][0] if index + 1 < len(spans) else None
            if name != _IGNORED:
                claims.setdefault(name, []).append((line, line.tokens_between(end, stop)))
    return claims


def _value_tokens(field_type: FieldType, tokens: tuple[Token, ...]) -> tuple[Token, ...]:
    tokens = tuple(token for token in tokens if not _LABEL_NOISE.match(token.text))
    if not tokens:
        return ()
    if field_type == "amount":
        amounts = [token for token in tokens if _amount(token) is not None]
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


def _amount(token: Token) -> object | None:
    return normalize_amount(token.text.rstrip(_TRAILING_PUNCTUATION))


def _next_line_amount(lines: list[Line], line: Line) -> tuple[Line, tuple[Token, ...]] | None:
    """A value printed on the line below its label, when that line is only an amount."""
    following = lines[lines.index(line) + 1 :][:1]
    if not following or len(following[0].tokens) != 1:
        return None
    token = following[0].tokens[0]
    return (following[0], (token,)) if _amount(token) is not None else None


def _record(
    name: str, line: Line, tokens: tuple[Token, ...], field_type: FieldType = "text"
) -> FieldRecord:
    raw = " ".join(token.text for token in tokens)
    if field_type == "amount":
        raw = raw.rstrip(_TRAILING_PUNCTUATION)
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
    if spec.headerless:
        return _extract_headerless_rows(lines, spec)
    records: list[FieldRecord] = []
    in_table = False
    row = 0
    for line in lines:
        words = set(normalize_text(line.text).split())
        if not in_table:
            in_table = len(words & set(spec.header_labels)) >= 2
            continue
        cells = _row_cells(line.tokens)
        if cells is not None:
            for name, tokens in cells.items():
                records.append(_record(f"line_items[{row}].{name}", line, tokens))
            row += 1
        elif words & set(spec.end_labels):
            break
    return records


def _extract_headerless_rows(lines: list[Line], spec: LineItemSpec) -> list[FieldRecord]:
    """Receipts without a table header: rows run from the top to the first summary line."""
    records: list[FieldRecord] = []
    row = 0
    for line in lines:
        if set(normalize_text(line.text).split()) & set(spec.end_labels):
            break
        cells = _receipt_row(line.tokens)
        if cells is None:
            continue
        for name, tokens in cells.items():
            kind: FieldType = "text" if name == "description" else "amount"
            records.append(_record(f"line_items[{row}].{name}", line, tokens, kind))
        row += 1
    return records


def _receipt_row(tokens: tuple[Token, ...]) -> dict[str, tuple[Token, ...]] | None:
    """Read `[qty] description [@price] [qty] amount`. Requires a priced row with a name."""
    if len(tokens) < 2 or not _looks_like_price(tokens[-1]):
        return None
    cells: dict[str, tuple[Token, ...]] = {"amount": (tokens[-1],)}
    body = list(tokens[:-1])
    if body and body[-1].text.startswith(_UNIT_PRICE_PREFIX) and len(body[-1].text) > 1:
        price = body.pop()
        cells["unit_price"] = (price.model_copy(update={"text": price.text[1:]}),)
    if body and (match := _LEADING_QUANTITY.match(body[0].text)):
        cells["quantity"] = (body.pop(0).model_copy(update={"text": match[1]}),)
    elif body and (match := _LEADING_QUANTITY.match(body[-1].text)):
        cells["quantity"] = (body.pop().model_copy(update={"text": match[1]}),)
    if not any(sum(c.isalpha() for c in token.text) >= 2 for token in body):
        return None
    cells["description"] = tuple(body)
    return cells


def _looks_like_price(token: Token) -> bool:
    """An amount with grouping, or at least three digits, to skip codes and counts."""
    text = token.text.rstrip(_TRAILING_PUNCTUATION)
    return _amount(token) is not None and (
        "," in text or "." in text or sum(c.isdigit() for c in text) >= 3
    )


def _is_number(token: Token) -> bool:
    return normalize_amount(token.text) is not None


def _row_cells(tokens: tuple[Token, ...]) -> dict[str, tuple[Token, ...]] | None:
    """Read columns from the right: quantity, optional unit price, amount."""
    if len(tokens) >= 4 and all(_is_number(token) for token in tokens[-3:]):
        return {
            "description": tokens[:-3],
            "quantity": (tokens[-3],),
            "unit_price": (tokens[-2],),
            "amount": (tokens[-1],),
        }
    if len(tokens) >= 3 and all(_is_number(token) for token in tokens[-2:]):
        return {
            "description": tokens[:-2],
            "quantity": (tokens[-2],),
            "amount": (tokens[-1],),
        }
    return None
