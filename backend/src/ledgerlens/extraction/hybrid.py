"""S4h, the hybrid pre-registered on 2026-11-07 (docs/evaluation.md).

Per single-valued field:
1. If the rules produced a value equal (normalised) to pass A or pass B, take the rule value.
2. Otherwise, among LLM values that parse and that the independent evidence check finds, take
   the one with the most support (+1 label-supported, +1 pass A and B agree); a tie goes to A.
3. Otherwise null.

Line items, as one unit: the rule rows if at least one of them equals (all four cells,
normalised) a row from pass A or B; otherwise the rows of the LLM pass with more rows whose
description the evidence check finds, tie to A; otherwise no rows.

The inputs must already have been through `process` one source at a time, so values are
normalised and checked. The result holds fresh records that carry only the choice signals,
to be processed once more as a whole.
"""

import re
from collections import defaultdict
from collections.abc import Sequence

from ledgerlens.fields import FieldRecord, SignalValue
from ledgerlens.schema import Schema

_CELL = re.compile(r"^line_items\[(\d+)\]\.(\w+)$")
_CELLS = ("description", "quantity", "unit_price", "amount")
Row = dict[str, FieldRecord]


def _headers(records: Sequence[FieldRecord]) -> dict[str, FieldRecord]:
    return {r.name: r for r in records if not r.name.startswith("line_items[")}


def _rows(records: Sequence[FieldRecord]) -> list[Row]:
    grouped: dict[int, Row] = defaultdict(dict)
    for record in records:
        if match := _CELL.match(record.name):
            grouped[int(match[1])][match[2]] = record
    return [grouped[index] for index in sorted(grouped)]


def _key(record: FieldRecord | None) -> str | None:
    return None if record is None else record.value_normalized


def _row_key(row: Row) -> tuple[str | None, ...]:
    return tuple(_key(row.get(cell)) for cell in _CELLS)


def _verified(record: FieldRecord | None) -> bool:
    return (
        record is not None
        and record.value_normalized is not None
        and record.evidence_independent
        and record.evidence_status != "not_found"
    )


def _fresh(record: FieldRecord | None, name: str, signals: dict[str, SignalValue]) -> FieldRecord:
    if record is None:
        return FieldRecord(name=name, value_raw=None, value_normalized=None, source="none",
                           signals=signals)  # fmt: skip
    return FieldRecord(name=name, value_raw=record.value_raw, value_normalized=None,
                       source=record.source, signals=signals)  # fmt: skip


def _agree(first: str | None, second: str | None) -> bool | None:
    return None if first is None or second is None else first == second


def choose_header(
    name: str, rules: FieldRecord | None, pass_a: FieldRecord | None, pass_b: FieldRecord | None
) -> FieldRecord:
    rule_key, a_key, b_key = _key(rules), _key(pass_a), _key(pass_b)
    llm_keys = [k for k in (a_key, b_key) if k is not None]
    signals: dict[str, SignalValue] = {
        "agree_pass_a_b": _agree(a_key, b_key),
        "agree_rules_llm": None if rule_key is None or not llm_keys else rule_key in llm_keys,
    }
    if rule_key is not None and rule_key in llm_keys:
        return _fresh(rules, name, signals | {"s4h_choice": "rules"})
    candidates = []
    for order, (label, record) in enumerate((("pass_a", pass_a), ("pass_b", pass_b))):
        if _verified(record):
            assert record is not None  # noqa: S101 - checked by _verified
            support = int(record.signals.get("label_supported") is True)
            support += int(signals["agree_pass_a_b"] is True)
            candidates.append((-support, order, label, record))
    if candidates:
        _, _, label, record = min(candidates, key=lambda c: (c[0], c[1]))
        return _fresh(record, name, signals | {"s4h_choice": label})
    return _fresh(None, name, signals | {"s4h_choice": "none"})


def choose_rows(rules: list[Row], pass_a: list[Row], pass_b: list[Row]) -> tuple[str, list[Row]]:
    llm_keys = {_row_key(row) for row in pass_a + pass_b}
    if rules and any(_row_key(row) in llm_keys for row in rules):
        return "rules", rules
    verified = [sum(_verified(row.get("description")) for row in rows) for rows in (pass_a, pass_b)]
    if verified[1] > verified[0]:
        return "pass_b", pass_b
    # A tie goes to pass A, as registered, even when pass A has no rows.
    return ("pass_a", pass_a) if pass_a else ("none", [])


def hybrid(
    schema: Schema,
    rules: Sequence[FieldRecord],
    pass_a: Sequence[FieldRecord],
    pass_b: Sequence[FieldRecord],
) -> list[FieldRecord]:
    """Fresh records for S4h. A failed pass is passed in as an empty source."""
    by_rules, by_a, by_b = _headers(rules), _headers(pass_a), _headers(pass_b)
    records = [
        choose_header(spec.name, by_rules.get(spec.name), by_a.get(spec.name), by_b.get(spec.name))
        for spec in schema.fields
    ]
    if schema.line_items is None:
        return records
    choice, rows = choose_rows(_rows(rules), _rows(pass_a), _rows(pass_b))
    for index, row in enumerate(rows):
        for cell in _CELLS:
            if (record := row.get(cell)) is not None and record.value_raw is not None:
                name = f"line_items[{index}].{cell}"
                records.append(_fresh(record, name, {"s4h_choice": choice}))
    return records
