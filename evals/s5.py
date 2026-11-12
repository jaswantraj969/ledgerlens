"""S5: calibrated routing on top of S4h, as pre-registered in docs/evaluation.md.

Units: a filled header field slot, or a predicted line-item row. An empty header slot is not a
unit for the calibrator but always goes to review and counts against automation.
Labels: a header unit is correct if its value equals gold under the frozen normalisation; a row
unit is correct if the metrics 1.1.1 row assignment matches it fully (`correct_rows`).
Calibrator: logistic regression (L2, C=1.0), one for header units and one for rows, fitted on
train only. Thresholds: chosen on validation only. Test is read once, at the end.
"""

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from evals.metrics import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, correct_rows
from evals.scoring import money_key, row_key

HEADER_FIELDS = ("subtotal", "tax_amount", "total_amount")
ROW_FIELDS = ("description", "quantity", "unit_price", "amount")
TARGETS = (0.98, 0.99)
GRID = np.round(np.arange(0, 1.0005, 0.001), 3)
_CELL = re.compile(r"^line_items\[(\d+)\]\.(\w+)$")
_CATEGORICAL = ("s4h_choice", "source")
ISOTONIC_FOLDS = 5
# Signal families for the ablations in docs/evaluation/final-test-protocol.md. A feature is in a
# family if its name equals a listed key or ends with "_" + key (row features carry a cell
# prefix, such as "amount_rules_passed"). agree_count and sources_with_value count agreement over
# all sources, so both agreement families remove them.
SIGNAL_FAMILIES: dict[str, tuple[str, ...]] = {
    "label_proximity": ("label_supported",),
    "ab_agreement": ("agree_pass_a_b", "cross_pass_available", "agree_count", "sources_with_value"),
    "rule_llm_agreement": (
        "agree_rules_llm",
        "agree_pass_a_deterministic",
        "agree_count",
        "sources_with_value",
    ),
    "ocr_confidence": ("ocr_confidence_mean", "ocr_confidence_min", "ocr_confidence_available"),
    "format_validation": ("value_valid", "rules_passed", "rules_failed", "rules_checked"),
}


def in_family(feature: str, keys: Sequence[str]) -> bool:
    return any(feature == key or feature.endswith(f"_{key}") for key in keys)


@dataclass
class Unit:
    document_id: str
    kind: str  # "header" or "row"
    name: str  # field name, or "row"
    features: dict[str, Any]
    correct: bool


def _row_features(cells: dict[str, dict[str, Any]]) -> dict[str, Any]:
    features: dict[str, Any] = {"cells": len(cells)}
    for cell in ("description", "amount", "quantity"):
        record = cells.get(cell)
        features[f"{cell}_present"] = record is not None
        if record is None:
            continue
        for key in ("independent_match_exact", "independent_match_fuzzy",
                    "independent_match_absent", "rules_failed", "rules_passed"):  # fmt: skip
            features[f"{cell}_{key}"] = record["features"].get(key)
        features["s4h_choice"] = record["features"].get("s4h_choice")
        features["source"] = record["source"]
    return features


def build_units(
    predictions: Sequence[dict[str, Any]],
    records: dict[str, list[dict[str, Any]]],
    gold_headers: dict[str, dict[str, str | None]],
    gold_rows: dict[str, list[dict[str, str | None]]],
) -> tuple[list[Unit], dict[str, int]]:
    """Units, and the number of header slots per document (filled or not)."""
    units: list[Unit] = []
    slots: dict[str, int] = {}
    for prediction in predictions:
        document_id = prediction["document_id"]
        by_name = {r["name"]: r for r in records.get(document_id, [])}
        slots[document_id] = len(HEADER_FIELDS)
        for name in HEADER_FIELDS:
            value = prediction["header"].get(name)
            if value is None or prediction["failed"]:
                continue
            record = by_name.get(name, {"features": {}, "source": "none"})
            gold = money_key(name, gold_headers[document_id][name])
            features = dict(record["features"]) | {"source": record["source"]}
            correct = gold is not None and money_key(name, value) == gold
            units.append(Unit(document_id, "header", name, features, correct))
        if prediction["failed"]:
            continue
        cells: dict[int, dict[str, dict[str, Any]]] = {}
        for record in by_name.values():
            if (match := _CELL.match(record["name"])) and record["value_present"]:
                cells.setdefault(int(match[1]), {})[match[2]] = record
        predicted_rows = [row_key(dict(row), ROW_FIELDS) for row in prediction["rows"]]
        reference = [row_key(row, ROW_FIELDS) for row in gold_rows.get(document_id, [])]
        flags = correct_rows(predicted_rows, reference)
        if len(cells) != len(flags):
            raise ValueError(f"{document_id}: {len(cells)} record rows, {len(flags)} predicted")
        for index, flag in zip(sorted(cells), flags, strict=True):
            units.append(Unit(document_id, "row", "row", _row_features(cells[index]), flag))
    return units, slots


class Vectorizer:
    """Fixed feature order from training units. None becomes 0 plus a missing indicator."""

    def __init__(self, units: Sequence[Unit], drop: Sequence[str] = ()) -> None:
        numeric: set[str] = set()
        categories: dict[str, set[str]] = {key: set() for key in (*_CATEGORICAL, "name")}
        for unit in units:
            categories["name"].add(unit.name)
            for key, value in unit.features.items():
                if in_family(key, drop):
                    continue
                if key in _CATEGORICAL:
                    categories[key].add(str(value))
                elif value is None or isinstance(value, bool | int | float):
                    numeric.add(key)
        self.numeric = sorted(numeric)
        self.categories = {key: sorted(values) for key, values in categories.items()}

    def columns(self) -> list[str]:
        columns = [c for key in self.numeric for c in (key, f"{key}_missing")]
        return columns + [f"{k}={v}" for k, values in self.categories.items() for v in values]

    def transform(self, units: Sequence[Unit]) -> np.ndarray:
        rows = []
        for unit in units:
            row: list[float] = []
            for key in self.numeric:
                value = unit.features.get(key)
                row += [0.0 if value is None else float(value), float(value is None)]
            for key, values in self.categories.items():
                actual = unit.name if key == "name" else str(unit.features.get(key))
                row += [float(actual == value) for value in values]
            rows.append(row)
        return np.array(rows, dtype=float)


@dataclass
class Calibrator:
    vectorizer: Vectorizer
    model: LogisticRegression | CalibratedClassifierCV | None
    constant: float | None = None  # when train holds only one class

    @classmethod
    def fit(
        cls, units: Sequence[Unit], drop: Sequence[str] = (), method: str = "logistic"
    ) -> "Calibrator":
        """Logistic regression; or, for "isotonic", the same model's scores mapped by isotonic
        regression, cross-fitted on train in folds grouped by document."""
        vectorizer = Vectorizer(units, drop)
        labels = np.array([unit.correct for unit in units], dtype=int)
        if len(set(labels.tolist())) < 2:
            return cls(vectorizer, None, float(labels.mean()) if len(labels) else 0.0)
        features = vectorizer.transform(units)
        base = LogisticRegression(C=1.0, max_iter=2000)
        if method == "logistic":
            return cls(vectorizer, base.fit(features, labels))
        if method != "isotonic":
            raise ValueError(f"unknown calibrator {method}")
        groups = [unit.document_id for unit in units]
        folds = list(GroupKFold(n_splits=ISOTONIC_FOLDS).split(features, labels, groups))
        model = CalibratedClassifierCV(base, method="isotonic", cv=folds)
        return cls(vectorizer, model.fit(features, labels))

    def predict(self, units: Sequence[Unit]) -> np.ndarray:
        if not units:
            return np.zeros(0)
        if self.model is None:
            return np.full(len(units), self.constant)
        return np.asarray(self.model.predict_proba(self.vectorizer.transform(units))[:, 1])


def choose_threshold(probabilities: np.ndarray, correct: np.ndarray, target: float) -> float | None:
    """Lowest grid threshold whose accepted units reach `target` precision; None if none does."""
    for threshold in GRID:
        accepted = probabilities >= threshold
        if accepted.any() and correct[accepted].mean() >= target:
            return float(threshold)
    return None


def ece(probabilities: np.ndarray, correct: np.ndarray, bins: int = 10) -> float | None:
    if not len(probabilities):
        return None
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for low, high in itertools.pairwise(edges):
        inside = (probabilities >= low) & (
            (probabilities < high) if high < 1 else (probabilities <= high)
        )
        if inside.any():
            total += inside.mean() * abs(probabilities[inside].mean() - correct[inside].mean())
    return float(total)


def _rates(
    accepted: np.ndarray, correct: np.ndarray, slots: np.ndarray, pick: np.ndarray
) -> tuple[float, float | None]:
    taken = accepted[pick].sum()
    precision = float(correct[pick].sum() / taken) if taken else None
    return float(taken / slots[pick].sum()), precision


def routing_report(
    units: Sequence[Unit],
    probabilities: np.ndarray,
    slots: dict[str, int],
    thresholds: dict[float, float | None],
) -> dict[str, Any]:
    """Automation and achieved precision per target, with document-bootstrap intervals."""
    documents = sorted(slots)
    index = {d: i for i, d in enumerate(documents)}
    correct = np.array([unit.correct for unit in units], dtype=bool)
    unit_doc = np.array([index[unit.document_id] for unit in units], dtype=int)
    rows_per_doc = np.bincount(
        [index[u.document_id] for u in units if u.kind == "row"], minlength=len(documents)
    )
    slots_per_doc = np.array([slots[d] for d in documents]) + rows_per_doc
    report: dict[str, Any] = {
        "units": len(units),
        "slots": int(slots_per_doc.sum()),
        "documents": len(documents),
        "ece_10_bins": ece(probabilities, correct.astype(float)),
        "brier": float(brier_score_loss(correct, probabilities)) if len(units) else None,
        "roc_auc": float(roc_auc_score(correct, probabilities))
        if len(set(correct.tolist())) == 2
        else None,
        "targets": {},
    }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = rng.integers(0, len(documents), size=(BOOTSTRAP_RESAMPLES, len(documents)))
    for target, threshold in thresholds.items():
        accepted = (
            probabilities >= threshold if threshold is not None else np.zeros(len(units), bool)
        )
        per_doc_accepted = np.bincount(unit_doc[accepted], minlength=len(documents))
        per_doc_correct = np.bincount(unit_doc[accepted & correct], minlength=len(documents))

        automation, precision = _rates(
            per_doc_accepted, per_doc_correct, slots_per_doc, np.arange(len(documents))
        )
        boot = [
            _rates(per_doc_accepted, per_doc_correct, slots_per_doc, sample) for sample in samples
        ]
        auto_ci = np.percentile([b[0] for b in boot], [2.5, 97.5]).tolist()
        precisions = [b[1] for b in boot if b[1] is not None]
        report["targets"][str(target)] = {
            "threshold": threshold,
            "accepted": int(accepted.sum()),
            "automation_rate": automation,
            "automation_rate_ci95": auto_ci,
            "achieved_precision": precision,
            "achieved_precision_ci95": np.percentile(precisions, [2.5, 97.5]).tolist()
            if precisions
            else None,
            "target_met": precision is not None and precision >= target,
        }
    return report
