"""Review workload of S5 on CORD test: header slots and line-item rows routed to human review,
per document, with the mean and a 95% document-bootstrap interval.

The S5 test files hold totals only, so per-document counts are recomputed from the saved
predictions and records: the same calibrator is refitted on train (deterministic), and the
thresholds recorded in the S5 test file are applied. The script stops unless the recomputed
accepted totals equal the totals in the S5 test file exactly. No system, prompt, threshold or
rule changes. Variant: all.

    python -m evals.runners.review_workload
"""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from evals.atomic import write_text_atomic
from evals.metrics import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED
from evals.runners.run_s5 import load
from evals.s5 import Calibrator, Unit

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
OUTPUT = RESULTS / "final" / "cord_s5_review_workload_v1_1_1.json"
BASES = {"s1": "train_all_p1.0", "s4h": "train_all_p2.2"}


def _interval(values: np.ndarray, samples: np.ndarray) -> dict[str, Any]:
    means = values[samples].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5]).tolist()
    return {"mean": float(values.mean()), "ci95": [low, high]}


def workload(base: str, scope: str) -> dict[str, Any]:
    source = RESULTS / f"cord_s5_{base}_v1_1_1.json"
    recorded = json.loads(source.read_text(encoding="utf-8"))
    train_units = load(base, scope, "train")[0]
    test_units, slots = load(base, "test", "test")
    documents = sorted(slots)
    index = {d: i for i, d in enumerate(documents)}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = rng.integers(0, len(documents), size=(BOOTSTRAP_RESAMPLES, len(documents)))
    out: dict[str, Any] = {
        "source": source.relative_to(ROOT).as_posix(),
        "documents": len(documents),
    }
    accepted_by_kind: dict[str, dict[str, np.ndarray]] = {}
    units_by_kind: dict[str, list[Unit]] = {}
    for kind in ("header", "row"):
        calibrator = Calibrator.fit([u for u in train_units if u.kind == kind])
        units = [u for u in test_units if u.kind == kind]
        units_by_kind[kind] = units
        probabilities = calibrator.predict(units)
        accepted_by_kind[kind] = {}
        for target, threshold in recorded["thresholds"][kind].items():
            accepted = (
                probabilities >= threshold if threshold is not None else np.zeros(len(units), bool)
            )
            expected = recorded["test"][kind]["targets"][target]["accepted"]
            if int(accepted.sum()) != expected:
                sys.exit(f"{base} {kind} {target}: recomputed {int(accepted.sum())} != {expected}")
            accepted_by_kind[kind][target] = accepted
    header_slots = np.array([slots[d] for d in documents], dtype=float)
    rows = np.bincount(
        [index[u.document_id] for u in units_by_kind["row"]], minlength=len(documents)
    )
    out["targets"] = {}
    for target in recorded["thresholds"]["header"]:
        per_kind = {}
        for kind in ("header", "row"):
            units = units_by_kind[kind]
            accepted = accepted_by_kind[kind][target]
            per_kind[kind] = np.bincount(
                [index[u.document_id] for u, a in zip(units, accepted, strict=True) if a],
                minlength=len(documents),
            )
        header_review = header_slots - per_kind["header"]
        row_review = rows - per_kind["row"]
        total_review = header_review + row_review
        total_slots = header_slots + rows
        out["targets"][target] = {
            "header_slots_routed_per_document": _interval(header_review, samples),
            "rows_routed_per_document": _interval(row_review.astype(float), samples),
            "all_slots_routed_per_document": _interval(total_review, samples),
            "share_of_slots_routed": float(total_review.sum() / total_slots.sum()),
            "header_slots_per_document": float(header_slots.mean()),
            "predicted_rows_per_document": float(rows.mean()),
        }
    return out


def main() -> None:
    result = {
        "metrics_version": "1.1.1",
        "split": "test",
        "variant": "all",
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "unit": "document"},
        "method": __doc__.split("\n\n")[1].replace("\n", " "),
        "systems": {f"S5-{'S1' if b == 's1' else 'S4h'}": workload(b, s) for b, s in BASES.items()},
    }
    write_text_atomic(OUTPUT, json.dumps(result, indent=2) + "\n")
    print("wrote", OUTPUT)


if __name__ == "__main__":
    main()
