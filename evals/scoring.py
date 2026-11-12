"""Turn extracted records into predictions and score them under metrics 1.1."""

import re
from collections import defaultdict
from collections.abc import Callable, Collection, Hashable, Sequence
from dataclasses import dataclass, field
from typing import Any

from evals import normalization
from evals.metrics import (
    METRICS_VERSION,
    SET_BASED_LABEL,
    match_rows,
    multiset_outcome,
    single_outcome,
    summarize,
    summarize_rows,
    summarize_single,
)
from ledgerlens.fields import FieldRecord

_CELL = re.compile(r"^line_items\[(\d+)\]\.(\w+)$")
TEXT_CELLS = {"description"}
HeaderKey = Callable[[str, str | None], Hashable | None]


@dataclass
class DocumentPrediction:
    """What a system output for one document. `failed` means it produced nothing to score."""

    document_id: str
    header: dict[str, str | None]
    rows: list[dict[str, str]] = field(default_factory=list)
    failed: bool = False


def to_prediction(
    document_id: str,
    records: list[FieldRecord],
    header_fields: Collection[str],
    *,
    fell_back: bool = False,
) -> DocumentPrediction:
    """Build a prediction. A fallback is a failed extraction: its values are never scored."""
    empty: dict[str, str | None] = dict.fromkeys(header_fields)
    if fell_back:
        return DocumentPrediction(document_id, empty, [], failed=True)
    rows: dict[int, dict[str, str]] = defaultdict(dict)
    for record in records:
        if record.value_raw is None:
            continue
        if match := _CELL.match(record.name):
            rows[int(match[1])][match[2]] = record.value_raw
        elif record.name in empty:
            empty[record.name] = record.value_raw
    return DocumentPrediction(document_id, empty, [rows[index] for index in sorted(rows)])


def _value_key(name: str, value: str | None) -> Any:
    return normalization.text(value) if name in TEXT_CELLS else normalization.money(value)


def row_key(row: dict[str, str | None], fields: Sequence[str]) -> dict[str, Any]:
    return {name: _value_key(name, row.get(name)) for name in fields}


def money_key(_name: str, value: str | None) -> Hashable | None:
    return normalization.money(value)


def score(
    predictions: Sequence[DocumentPrediction],
    gold_headers: dict[str, dict[str, str | None]],
    gold_rows: dict[str, list[dict[str, str | None]]],
    header_fields: Collection[str],
    row_fields: Sequence[str],
    header_key: HeaderKey = money_key,
) -> dict[str, Any]:
    """Score every document. `gold_rows` empty and `row_fields` empty skips line items."""
    single: dict[str, list[Any]] = {name: [] for name in header_fields}
    excluded = dict.fromkeys(header_fields, 0)
    row_outcomes = []
    columns: dict[str, list[Any]] = {name: [] for name in row_fields}

    for prediction in predictions:
        gold = gold_headers[prediction.document_id]
        for name in header_fields:
            gold_value = header_key(name, gold[name])
            key = header_key(name, prediction.header.get(name))
            excluded[name] += int(gold[name] is not None and gold_value is None)
            single[name].append(single_outcome(key, gold_value))
        if row_fields:
            predicted_rows = [row_key(dict(row), row_fields) for row in prediction.rows]
            reference = [
                row_key(row, row_fields) for row in gold_rows.get(prediction.document_id, [])
            ]
            row_outcomes.append(match_rows(predicted_rows, reference))
            for name in row_fields:
                columns[name].append(
                    multiset_outcome(
                        [r[name] for r in predicted_rows if r[name] is not None],
                        [r[name] for r in reference if r[name] is not None],
                    )
                )

    result: dict[str, Any] = {
        "metrics_version": METRICS_VERSION,
        "normalization": {
            "version": normalization.NORMALIZATION_VERSION,
            "sha256": normalization.fingerprint(),
        },
        "fields": {name: summarize_single(single[name]) for name in header_fields},
        "gold_values_excluded_unparsable": excluded,
    }
    if row_fields:
        result["line_items_row_level"] = summarize_rows(row_outcomes)
        result["line_items_set_based"] = {
            "label": SET_BASED_LABEL,
            "fields": {name: summarize(columns[name]) for name in row_fields},
        }
    return result
