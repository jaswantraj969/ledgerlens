"""S5 ablations, as fixed in docs/evaluation/final-test-protocol.md. No model is called.

Each ablation refits the calibrators from the saved predictions and records only: fitted on
train, thresholds chosen on validation at each target, then scored. Bases S5-S1 and S5-S4h, the
"all" variant. Without --final only validation is reported (in-sample for the thresholds).
--final also scores test, once, and refuses to replace its result.

    python -m evals.runners.run_s5_ablations [--final]
"""

import argparse
import json
import sys
from typing import Any

import numpy as np

from evals.runners.run_cord_s1 import environment
from evals.runners.run_s5 import RESULTS, evaluate, load
from evals.s5 import SIGNAL_FAMILIES, TARGETS, Calibrator, choose_threshold

BASES = {"s1": "train_all_p1.0", "s4h": "train_all_p2.2"}
# name: (removed signal families, calibrator)
ABLATIONS: dict[str, tuple[tuple[str, ...], str]] = {
    "full": ((), "logistic"),
    **{f"minus_{family}": ((family,), "logistic") for family in SIGNAL_FAMILIES},
    "isotonic": ((), "isotonic"),
}


def run_ablation(
    families: tuple[str, ...], method: str, train: Any, validation: Any
) -> tuple[dict[str, Calibrator], dict[str, dict[float, float | None]], dict[str, Any]]:
    drop = [key for family in families for key in SIGNAL_FAMILIES[family]]
    calibrators = {
        kind: Calibrator.fit([u for u in train[0] if u.kind == kind], drop, method)
        for kind in ("header", "row")
    }
    thresholds: dict[str, dict[float, float | None]] = {}
    for kind, calibrator in calibrators.items():
        units = [u for u in validation[0] if u.kind == kind]
        probabilities = calibrator.predict(units)
        correct = np.array([u.correct for u in units], dtype=bool)
        thresholds[kind] = {t: choose_threshold(probabilities, correct, t) for t in TARGETS}
    features = {kind: c.vectorizer.columns() for kind, c in calibrators.items()}
    return calibrators, thresholds, features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="also score test, once")
    arguments = parser.parse_args()
    if arguments.final:
        output = RESULTS / "cord_s5_ablations_v1_1_1.json"
        if output.exists():
            sys.exit(f"{output} exists: test is read once per configuration")
    else:
        output = RESULTS / "dev" / "cord_s5_ablations_validation_v1_1_1.json"

    result: dict[str, Any] = {
        "protocol": "docs/evaluation/final-test-protocol.md",
        "variant": "all",
        "families": {name: list(keys) for name, keys in SIGNAL_FAMILIES.items()},
        "bases": {},
        "environment": environment(),
    }
    for base, scope in BASES.items():
        train = load(base, scope, "train")
        validation = load(base, "validation", "validation")
        test = load(base, "test", "test") if arguments.final else None
        full_columns = run_ablation((), "logistic", train, validation)[2]
        entries = {}
        for name, (families, method) in ABLATIONS.items():
            calibrators, thresholds, features = run_ablation(families, method, train, validation)
            entry: dict[str, Any] = {
                "removed_families": list(families),
                "calibrator": method,
                "feature_columns": {kind: len(columns) for kind, columns in features.items()},
                "removed_columns_present_in_train": {
                    kind: sorted(set(full_columns[kind]) - set(columns))
                    for kind, columns in features.items()
                },
                "thresholds": {
                    k: {str(t): v for t, v in th.items()} for k, th in thresholds.items()
                },
                "validation": evaluate(calibrators, thresholds, validation),
            }
            if test is not None:
                entry["test"] = evaluate(calibrators, thresholds, test)
            entries[name] = entry
            print(base, name, "done", flush=True)
        result["bases"][f"S5-{base.upper().replace('S4H', 'S4h')}"] = {
            "train_scope": scope,
            "ablations": entries,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", output)


if __name__ == "__main__":
    main()
