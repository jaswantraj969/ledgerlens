"""Field metrics with document-level bootstrap intervals. Formulas: docs/evaluation.md.

Metrics 1.1 is current. `Outcome`, `header_outcome` and `summarize` are metrics 1.0: they stay
for reproducing old results, and `multiset_outcome` remains as the secondary set-based score.
"""

from collections import Counter
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

METRICS_VERSION = "1.1"
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261106
SET_BASED_LABEL = "set-based, ignores row alignment"
# Larger than any total of partial scores, so full matches are maximised first.
_FULL_MATCH_WEIGHT = 1000.0

Row = Mapping[str, Hashable | None]


@dataclass(frozen=True)
class Outcome:
    """Counts for one field on one document. `agrees` feeds exact match."""

    tp: int
    fp: int
    fn: int
    agrees: bool
    labelled: bool


def header_outcome(predicted: Hashable | None, gold: Hashable | None) -> Outcome:
    if gold is None:
        return Outcome(0, int(predicted is not None), 0, predicted is None, False)
    if predicted is None:
        return Outcome(0, 0, 1, False, True)
    if predicted == gold:
        return Outcome(1, 0, 0, True, True)
    return Outcome(0, 1, 1, False, True)


def multiset_outcome(predicted: Iterable[Hashable], gold: Iterable[Hashable]) -> Outcome:
    predicted_counts, gold_counts = Counter(predicted), Counter(gold)
    matched = sum((predicted_counts & gold_counts).values())
    return Outcome(
        matched,
        sum(predicted_counts.values()) - matched,
        sum(gold_counts.values()) - matched,
        predicted_counts == gold_counts,
        bool(gold_counts),
    )


def _prf(tp: float, fp: float, fn: float) -> tuple[float | None, float | None, float | None]:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return precision, recall, f1


def _rates(counts: np.ndarray) -> tuple[float | None, float | None, float | None, float]:
    tp, fp, fn, agrees, documents = counts
    return (*_prf(tp, fp, fn), agrees / documents)


def _interval(values: list[float]) -> list[float] | None:
    if not values:
        return None
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def _bootstrap(
    table: np.ndarray, rates: Callable[[np.ndarray], tuple[float | None, ...]]
) -> list[list[float] | None]:
    """Percentile intervals for each rate, resampling documents (rows of `table`)."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    width = len(rates(table.sum(axis=0)))
    samples: list[list[float]] = [[] for _ in range(width)]
    picks = rng.integers(0, len(table), size=(BOOTSTRAP_RESAMPLES, len(table)))
    for pick in picks:
        for values, rate in zip(samples, rates(table[pick].sum(axis=0)), strict=True):
            if rate is not None:
                values.append(rate)
    return [_interval(values) for values in samples]


def summarize(outcomes: Sequence[Outcome]) -> dict[str, object]:
    """Metrics 1.0: point estimates and 95% percentile intervals, resampling documents."""
    table = np.array([[o.tp, o.fp, o.fn, o.agrees, 1] for o in outcomes], dtype=np.int64)
    precision, recall, f1, exact = _rates(table.sum(axis=0))
    intervals = _bootstrap(table, _rates)
    return {
        "n_documents": len(outcomes),
        "n_labelled": sum(o.labelled for o in outcomes),
        "tp": int(table[:, 0].sum()),
        "fp": int(table[:, 1].sum()),
        "fn": int(table[:, 2].sum()),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match": exact,
        "precision_ci95": intervals[0],
        "recall_ci95": intervals[1],
        "f1_ci95": intervals[2],
        "exact_match_ci95": intervals[3],
    }


@dataclass(frozen=True)
class SingleOutcome:
    """One single-valued field on one document, under metrics 1.1."""

    predicted: bool
    gold_present: bool
    correct: bool


def single_outcome(predicted: Hashable | None, gold: Hashable | None) -> SingleOutcome:
    return SingleOutcome(
        predicted is not None, gold is not None, gold is not None and predicted == gold
    )


def _single_rates(counts: np.ndarray) -> tuple[float | None, ...]:
    tp, fp, fn, present, absent, filled = counts
    return (
        *_prf(tp, fp, fn),
        tp / present if present else None,
        filled / absent if absent else None,
    )


def summarize_single(outcomes: Sequence[SingleOutcome]) -> dict[str, object]:
    """Metrics 1.1 for a single-valued field."""
    table = np.array(
        [
            [
                o.correct,
                o.predicted and not o.correct,
                o.gold_present and not o.correct,
                o.gold_present,
                not o.gold_present,
                o.predicted and not o.gold_present,
            ]
            for o in outcomes
        ],
        dtype=np.int64,
    )
    totals = table.sum(axis=0)
    precision, recall, f1, exact, false_fill = _single_rates(totals)
    intervals = _bootstrap(table, _single_rates)
    return {
        "n_documents": len(outcomes),
        "n_present": int(totals[3]),
        "n_absent": int(totals[4]),
        "tp": int(totals[0]),
        "fp": int(totals[1]),
        "fn": int(totals[2]),
        "false_fills": int(totals[5]),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match": exact,
        "false_fill_rate": false_fill,
        "precision_ci95": intervals[0],
        "recall_ci95": intervals[1],
        "f1_ci95": intervals[2],
        "exact_match_ci95": intervals[3],
        "false_fill_rate_ci95": intervals[4],
    }


@dataclass(frozen=True)
class RowOutcome:
    """Row counts for one document after one-to-one assignment."""

    correct: int
    predicted: int
    gold: int


def _scored_fields(gold: Row) -> list[str]:
    return [name for name, value in gold.items() if value is not None]


def row_score(predicted: Row, gold: Row) -> tuple[bool, float]:
    """Whether every field the gold row labels matches, and the share that do."""
    fields = _scored_fields(gold)
    matches = sum(predicted.get(name) == gold[name] for name in fields)
    return matches == len(fields), matches / len(fields)


def match_rows(predicted: Sequence[Row], gold: Sequence[Row]) -> RowOutcome:
    """One-to-one Hungarian assignment. Gold rows with no labelled field are not scored."""
    gold_rows = [row for row in gold if _scored_fields(row)]
    if not predicted or not gold_rows:
        return RowOutcome(0, len(predicted), len(gold_rows))
    weights = np.zeros((len(predicted), len(gold_rows)))
    full = np.zeros_like(weights, dtype=bool)
    for i, candidate in enumerate(predicted):
        for j, reference in enumerate(gold_rows):
            all_match, share = row_score(candidate, reference)
            full[i, j] = all_match
            weights[i, j] = share + (_FULL_MATCH_WEIGHT if all_match else 0.0)
    assigned = linear_sum_assignment(weights, maximize=True)
    return RowOutcome(int(full[assigned].sum()), len(predicted), len(gold_rows))


def _row_rates(counts: np.ndarray) -> tuple[float | None, ...]:
    correct, predicted, gold, perfect, labelled = counts
    return (
        *_prf(correct, predicted - correct, gold - correct),
        perfect / labelled if labelled else None,
    )


def summarize_rows(outcomes: Sequence[RowOutcome]) -> dict[str, object]:
    """Row-level precision, recall and F1, pooled over documents."""
    table = np.array(
        [
            [
                o.correct,
                o.predicted,
                o.gold,
                o.gold > 0 and o.correct == o.predicted == o.gold,
                o.gold > 0,
            ]
            for o in outcomes
        ],
        dtype=np.int64,
    )
    totals = table.sum(axis=0)
    precision, recall, f1, perfect = _row_rates(totals)
    intervals = _bootstrap(table, _row_rates)
    return {
        "n_documents": len(outcomes),
        "n_documents_with_rows": int(totals[4]),
        "rows_correct": int(totals[0]),
        "rows_predicted": int(totals[1]),
        "rows_gold": int(totals[2]),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "documents_all_rows_correct": perfect,
        "precision_ci95": intervals[0],
        "recall_ci95": intervals[1],
        "f1_ci95": intervals[2],
        "documents_all_rows_correct_ci95": intervals[3],
    }
