"""Field metrics with document-level bootstrap intervals. Definitions: docs/evaluation.md."""

from collections import Counter
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass

import numpy as np

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261106


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


def _rates(counts: np.ndarray) -> tuple[float | None, float | None, float | None, float]:
    tp, fp, fn, agrees, documents = counts
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None
    return precision, recall, f1, agrees / documents


def _interval(values: list[float]) -> list[float] | None:
    if not values:
        return None
    low, high = np.percentile(values, [2.5, 97.5])
    return [float(low), float(high)]


def summarize(outcomes: Sequence[Outcome]) -> dict[str, object]:
    """Point estimates and 95% percentile intervals, resampling documents."""
    table = np.array([[o.tp, o.fp, o.fn, o.agrees, 1] for o in outcomes], dtype=np.int64)
    precision, recall, f1, exact = _rates(table.sum(axis=0))

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples: list[list[float]] = [[], [], [], []]
    picks = rng.integers(0, len(table), size=(BOOTSTRAP_RESAMPLES, len(table)))
    for pick in picks:
        for values, rate in zip(samples, _rates(table[pick].sum(axis=0)), strict=True):
            if rate is not None:
                values.append(rate)
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
        "precision_ci95": _interval(samples[0]),
        "recall_ci95": _interval(samples[1]),
        "f1_ci95": _interval(samples[2]),
        "exact_match_ci95": _interval(samples[3]),
    }
