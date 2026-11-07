"""Combine pass A, pass B and the deterministic extractor by normalised agreement.

The chosen value is the one most sources agree on. A tie goes to the earliest source in
(pass A, pass B, deterministic). Each record keeps agreement signals, and its `source` names
the first agreeing source, so a value only the rules found stays self-sourced. Line items
come from the first LLM pass that produced rows, because rows cannot be voted cell by cell
without aligning them; each cell records how many sources printed that value.
"""

from collections import Counter
from collections.abc import Sequence

from ledgerlens.extraction.deterministic import normalized_value
from ledgerlens.extraction.llm import SOURCE_PASS_A, SOURCE_PASS_B
from ledgerlens.fields import FieldRecord
from ledgerlens.schema import FieldType, Schema

DETERMINISTIC = "deterministic"
SOURCE_ORDER = (SOURCE_PASS_A, SOURCE_PASS_B, DETERMINISTIC)
_CELL_TYPES: dict[str, FieldType] = {
    "description": "text",
    "quantity": "amount",
    "unit_price": "amount",
    "amount": "amount",
}


def _cell_name(name: str) -> str | None:
    return name.split(".", 1)[1] if name.startswith("line_items[") else None


def _key(kind: FieldType, record: FieldRecord | None) -> str | None:
    return None if record is None else normalized_value(kind, record.value_raw)


def _agreement(keys: dict[str, str | None], chosen: str | None) -> dict[str, bool | int | None]:
    a, b, rules = (keys.get(source) for source in SOURCE_ORDER)
    return {
        "sources_with_value": sum(key is not None for key in keys.values()),
        "agree_count": sum(key is not None and key == chosen for key in keys.values()),
        "agree_pass_a_b": None if a is None or b is None else a == b,
        "agree_pass_a_deterministic": None if a is None or rules is None else a == rules,
    }


def _merge_header(
    name: str, kind: FieldType, by_source: dict[str, dict[str, FieldRecord]]
) -> FieldRecord:
    candidates = {source: records.get(name) for source, records in by_source.items()}
    keys = {source: _key(kind, record) for source, record in candidates.items()}
    votes = Counter(key for key in keys.values() if key is not None)
    if not votes:
        return FieldRecord(name=name, value_raw=None, value_normalized=None, source="merged")
    best = max(votes.values())
    chosen = next(
        key
        for source in SOURCE_ORDER
        if (key := keys.get(source)) is not None and votes[key] == best
    )
    winner = next(source for source in SOURCE_ORDER if keys.get(source) == chosen)
    record = candidates[winner]
    assert record is not None  # noqa: S101 - a key exists only for a present record
    merged = record.model_copy(deep=True, update={"source": winner})
    merged.signals.update(_agreement(keys, chosen))
    return merged


def _row_cells(records: Sequence[FieldRecord]) -> list[FieldRecord]:
    return [record for record in records if _cell_name(record.name) is not None]


def _cell_values(records: Sequence[FieldRecord]) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {}
    for record in _row_cells(records):
        cell = _cell_name(record.name) or ""
        key = normalized_value(_CELL_TYPES[cell], record.value_raw)
        if key is not None:
            values.setdefault(cell, set()).add(key)
    return values


def merge_sources(
    pass_a: Sequence[FieldRecord],
    pass_b: Sequence[FieldRecord],
    deterministic: Sequence[FieldRecord],
    schema: Schema,
) -> list[FieldRecord]:
    """Merge three sources. Pass an empty sequence for a source that failed."""
    sources = {SOURCE_PASS_A: pass_a, SOURCE_PASS_B: pass_b, DETERMINISTIC: deterministic}
    by_source = {
        source: {record.name: record for record in records} for source, records in sources.items()
    }
    merged = [_merge_header(spec.name, spec.type, by_source) for spec in schema.fields]

    rows_from = next((s for s in (pass_a, pass_b) if _row_cells(s)), ())
    source_values = {source: _cell_values(records) for source, records in sources.items()}
    for record in _row_cells(rows_from):
        cell = _cell_name(record.name) or ""
        key = normalized_value(_CELL_TYPES[cell], record.value_raw)
        keys = {
            source: key if key in values.get(cell, set()) else None
            for source, values in source_values.items()
        }
        copied = record.model_copy(deep=True)
        copied.signals.update(_agreement(keys, key))
        merged.append(copied)
    return merged
