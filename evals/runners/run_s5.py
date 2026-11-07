"""Fit and evaluate S5 from saved S4h predictions and records. No model is called.

    python -m evals.runners.run_s5 --train-scope train_all_p2.1 [--variant grouped] [--final]

Calibrators are fitted on train, thresholds chosen on validation. Without --final only
validation is reported. --final reads test once and refuses to replace a result. The grouped
variant uses evals/splits/cord_v2/layout_group_holdout.json: fit and thresholds on calibration
groups, report on test documents of the unseen evaluation groups (and of calibration groups).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from evals.datasets.cord import DEFAULT_RAW_DIR, HEADER_FIELDS, iter_documents
from evals.runners.run_cord_s1 import environment
from evals.s5 import TARGETS, Calibrator, Unit, build_units, choose_threshold, routing_report

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "cord-v2"
HOLDOUT = ROOT / "evals" / "splits" / "cord_v2" / "layout_group_holdout.json"
GROUPS = ROOT / "evals" / "splits" / "cord_v2" / "layout_groups.json"
RESULTS = ROOT / "evals" / "results"


def load(base: str, scope: str, split: str) -> tuple[list[Unit], dict[str, int]]:
    predictions = json.loads((DATA / "predictions" / f"{base}_{scope}.json").read_text("utf-8"))
    records = json.loads((DATA / "records" / f"{base}_{scope}.json").read_text("utf-8"))
    wanted = {p["document_id"] for p in predictions}
    headers: dict[str, dict[str, str | None]] = {}
    rows: dict[str, list[dict[str, str | None]]] = {}
    for document in iter_documents(split, DEFAULT_RAW_DIR, with_images=False):  # type: ignore[arg-type]
        if document.document_id in wanted:
            headers[document.document_id] = {f: document.gold[f] for f in HEADER_FIELDS}
            rows[document.document_id] = document.gold_rows
    return build_units(predictions, records, headers, rows)


def restrict(
    data: tuple[list[Unit], dict[str, int]], keep: set[str]
) -> tuple[list[Unit], dict[str, int]]:
    units, slots = data
    return [u for u in units if u.document_id in keep], {
        d: n for d, n in slots.items() if d in keep
    }


def evaluate(
    calibrators: dict[str, Calibrator],
    thresholds: dict[str, dict[float, float | None]],
    data: tuple[list[Unit], dict[str, int]],
) -> dict[str, Any]:
    units, slots = data
    report: dict[str, Any] = {}
    for kind in ("header", "row"):
        chosen = [u for u in units if u.kind == kind]
        probabilities = calibrators[kind].predict(chosen)
        kind_slots = slots if kind == "header" else dict.fromkeys(slots, 0)
        report[kind] = routing_report(chosen, probabilities, kind_slots, thresholds[kind])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="s4h")
    parser.add_argument("--train-scope", required=True)
    parser.add_argument("--variant", choices=["all", "grouped"], default="all")
    parser.add_argument("--final", action="store_true", help="read the test split, once")
    arguments = parser.parse_args()

    train = load(arguments.base, arguments.train_scope, "train")
    validation = load(arguments.base, "validation", "validation")
    roles: dict[str, str] = {}
    if arguments.variant == "grouped":
        holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))["group_roles"]
        assignments = json.loads(GROUPS.read_text(encoding="utf-8"))["assignments"]
        roles = {d: holdout[str(g)] for d, g in assignments.items()}
        calibration = {d for d, role in roles.items() if role == "calibration"}
        train, validation = restrict(train, calibration), restrict(validation, calibration)

    calibrators = {
        k: Calibrator.fit([u for u in train[0] if u.kind == k]) for k in ("header", "row")
    }
    thresholds: dict[str, dict[float, float | None]] = {}
    for kind, calibrator in calibrators.items():
        units = [u for u in validation[0] if u.kind == kind]
        probabilities = calibrator.predict(units)
        correct = np.array([u.correct for u in units], dtype=bool)
        thresholds[kind] = {t: choose_threshold(probabilities, correct, t) for t in TARGETS}

    suffix = "" if arguments.variant == "all" else "_grouped"
    result: dict[str, Any] = {
        "system": "S5",
        "base": arguments.base,
        "variant": arguments.variant,
        "train_scope": arguments.train_scope,
        "train_units": {k: sum(u.kind == k for u in train[0]) for k in ("header", "row")},
        "validation_units": {k: sum(u.kind == k for u in validation[0]) for k in ("header", "row")},
        "thresholds": {k: {str(t): v for t, v in th.items()} for k, th in thresholds.items()},
        "validation": evaluate(calibrators, thresholds, validation),
        "environment": environment(),
    }
    if arguments.final:
        output = RESULTS / f"cord_s5{suffix}_v1_1_1.json"
        if output.exists():
            sys.exit(f"{output} exists: test is read once per configuration")
        test = load(arguments.base, "test", "test")
        if arguments.variant == "grouped":
            unseen = {d for d, role in roles.items() if role == "evaluation"}
            seen = {d for d, role in roles.items() if role == "calibration"}
            result["test_unseen_groups"] = evaluate(calibrators, thresholds, restrict(test, unseen))
            result["test_calibration_groups"] = evaluate(
                calibrators, thresholds, restrict(test, seen)
            )
        else:
            result["test"] = evaluate(calibrators, thresholds, test)
    else:
        output = RESULTS / "dev" / f"cord_s5{suffix}_validation_v1_1_1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", output)


if __name__ == "__main__":
    main()
