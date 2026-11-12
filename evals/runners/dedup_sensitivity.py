"""Duplicate-exclusion sensitivity check, as registered in
docs/evaluation/addendum-01-duplicate-sensitivity.md (post hoc). Changes no result file.

From the saved test predictions and records only: S1-S4h scored on the 93 test documents outside
the exclusion set, and on the 7 excluded documents alone (for information); S5-S1 and S5-S4h
re-applied with the recorded thresholds (after checking the accepted counts on all 100 documents
equal the recorded ones) and reported on the 93. No model is called.

    python -m evals.runners.dedup_sensitivity
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from evals.atomic import write_text_atomic
from evals.datasets.cord import DEFAULT_RAW_DIR, HEADER_FIELDS, ROW_FIELDS, iter_documents
from evals.runners.make_s5_table import exact_interval
from evals.runners.run_s5 import load, restrict
from evals.s5 import Calibrator, routing_report
from evals.scoring import DocumentPrediction, score

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
PREDICTIONS = ROOT / "data" / "cord-v2" / "predictions"
OUTPUT = RESULTS / "final" / "cord_test_dedup_sensitivity_v1_1_1.json"
ADDENDUM = "docs/evaluation/addendum-01-duplicate-sensitivity.md"
EXCLUDED = tuple(f"cord-v2:test:{n}" for n in (25, 28, 31, 33, 38, 44, 75))
SYSTEMS = {"S1": "s1", "S2'": "s2p", "S3'": "s3p", "S4'": "s4p", "S4h": "s4h"}
S5_BASES = {"S5-S1": ("s1", "train_all_p1.0"), "S5-S4h": ("s4h", "train_all_p2.2")}
FIELDS = ("total_amount", "subtotal", "tax_amount")
FIELD_NAMES = (tuple(HEADER_FIELDS), tuple(ROW_FIELDS))


def _gold() -> tuple[dict[str, Any], dict[str, Any]]:
    headers, rows = {}, {}
    for document in iter_documents("test", DEFAULT_RAW_DIR, with_images=False):
        headers[document.document_id] = {f: document.gold[f] for f in HEADER_FIELDS}
        rows[document.document_id] = document.gold_rows
    return headers, rows


def _predictions(name: str) -> tuple[list[DocumentPrediction], str]:
    raw = (PREDICTIONS / f"{name}_test.json").read_text(encoding="utf-8")
    return [DocumentPrediction(**p) for p in json.loads(raw)], hashlib.sha256(
        raw.encode()
    ).hexdigest()


def _f1(scored: dict[str, Any], with_ci: bool) -> dict[str, Any]:
    out = {}
    for key in FIELDS:
        block = scored["fields"][key]
        out[key] = {"f1": block["f1"], "n_present": block["n_present"]}
        if with_ci:
            out[key]["f1_ci95"] = block["f1_ci95"]
    rows = scored["line_items_row_level"]
    out["rows"] = {"f1": rows["f1"], "rows_gold": rows["rows_gold"]}
    if with_ci:
        out["rows"]["f1_ci95"] = rows["f1_ci95"]
    return out


def extraction(gold: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    headers, rows = gold
    out = {}
    for label, name in SYSTEMS.items():
        predictions, digest = _predictions(name)
        recorded = json.loads((RESULTS / f"cord_{name}_v1_1_1.json").read_text(encoding="utf-8"))
        if digest != recorded["predictions_sha256"]:
            sys.exit(f"{label}: predictions file does not match the recorded hash")
        full = score(predictions, headers, rows, tuple(HEADER_FIELDS), tuple(ROW_FIELDS))
        for key in FIELDS:  # the saved predictions must reproduce the recorded result
            if full["fields"][key]["f1"] != recorded["fields"][key]["f1"]:
                sys.exit(f"{label}: full-set {key} F1 does not reproduce the recorded value")
        kept = [p for p in predictions if p.document_id not in EXCLUDED]
        dropped = [p for p in predictions if p.document_id in EXCLUDED]
        out[label] = {
            "predictions_sha256": digest,
            "all_100": _f1(full, with_ci=True),
            "without_excluded": _f1(score(kept, headers, rows, *FIELD_NAMES), True),
            "excluded_only": _f1(score(dropped, headers, rows, *FIELD_NAMES), False),
            "documents": {"without_excluded": len(kept), "excluded_only": len(dropped)},
        }
    return out


def _with_exact(report: dict[str, Any]) -> dict[str, Any]:
    for values in report["targets"].values():
        small = exact_interval(values)
        values["correct_accepted"] = small[0] if small else None
        values["achieved_precision_exact_ci95_clopper_pearson"] = small[1] if small else None
    return report


def routing() -> dict[str, Any]:
    out = {}
    for label, (base, scope) in S5_BASES.items():
        recorded = json.loads((RESULTS / f"cord_s5_{base}_v1_1_1.json").read_text(encoding="utf-8"))
        train_units = load(base, scope, "train")[0]
        test = load(base, "test", "test")
        keep = {d for d in test[1] if d not in EXCLUDED}
        subset = restrict(test, keep)
        entry: dict[str, Any] = {"documents": len(subset[1])}
        out[label] = entry
        for kind in ("header", "row"):
            calibrator = Calibrator.fit([u for u in train_units if u.kind == kind])
            thresholds = {float(t): v for t, v in recorded["thresholds"][kind].items()}
            units = [u for u in test[0] if u.kind == kind]
            probabilities = calibrator.predict(units)
            for target, threshold in thresholds.items():
                accepted = int((probabilities >= threshold).sum()) if threshold is not None else 0
                expected = recorded["test"][kind]["targets"][str(target)]["accepted"]
                if accepted != expected:
                    sys.exit(f"{label} {kind} {target}: recomputed {accepted} != {expected}")
            sub_units = [u for u in subset[0] if u.kind == kind]
            sub_slots = subset[1] if kind == "header" else dict.fromkeys(subset[1], 0)
            report = routing_report(sub_units, calibrator.predict(sub_units), sub_slots, thresholds)
            entry[kind] = _with_exact(report)
    return out


def _cell(block: dict[str, Any]) -> str:
    ci = block.get("f1_ci95")
    value = "n/a" if block["f1"] is None else f"{block['f1']:.3f}"
    return value if not ci else f"{value} [{ci[0]:.3f}, {ci[1]:.3f}]"


def orderings(extract: dict[str, Any]) -> list[dict[str, Any]]:
    """S1 against S4h on each field, on all 100 and on the 93: which is higher."""
    out = []
    for key in (*FIELDS, "rows"):
        row: dict[str, Any] = {"field": key}
        for scope in ("all_100", "without_excluded"):
            s1, s4h = extract["S1"][scope][key]["f1"], extract["S4h"][scope][key]["f1"]
            row[scope] = {"S1": s1, "S4h": s4h,
                          "higher": "S1" if s1 > s4h else "S4h" if s4h > s1 else "tie"}  # fmt: skip
        row["ordering_changes"] = row["all_100"]["higher"] != row["without_excluded"]["higher"]
        out.append(row)
    return out


def render(result: dict[str, Any]) -> str:
    names = {"total_amount": "Total", "subtotal": "Subtotal", "tax_amount": "Tax", "rows": "Rows"}
    lines = [
        "# CORD test: duplicate-exclusion sensitivity check (post hoc, metrics 1.1.1)",
        "",
        f"Generated by `evals/runners/dedup_sensitivity.py`. Do not edit by hand. Registered in "
        f"`{ADDENDUM}` before computing. Primary results are unchanged; this is reported beside "
        "them. Excluded: " + ", ".join(d.split(":")[-1] for d in EXCLUDED) + " (test document "
        "numbers). No model call, refit beyond the recorded calibrator, or threshold change.",
        "",
        "## S1 to S4h: F1 [95% document-bootstrap CI]",
        "",
        "| System | Documents | Total F1 | Subtotal F1 | Tax F1 | Row F1 |",
        "|---|---|---|---|---|---|",
    ]
    for label, block in result["extraction"].items():
        for scope, n in (("all_100", 100), ("without_excluded", 93)):
            cells = " | ".join(_cell(block[scope][k]) for k in names)
            lines.append(f"| {label} | {n}{' (primary)' if n == 100 else ''} | {cells} |")
    lines += [
        "",
        "## On the 7 excluded documents alone (for information; no intervals)",
        "",
        "| System | Total F1 | Subtotal F1 | Tax F1 | Row F1 |",
        "|---|---|---|---|---|",
    ]
    for label, block in result["extraction"].items():
        lines.append(
            f"| {label} | " + " | ".join(_cell(block["excluded_only"][k]) for k in names) + " |"
        )
    lines += [
        "",
        "## S1 against S4h, by field",
        "",
        "| Field | All 100: S1 / S4h, higher | 93: S1 / S4h, higher | Ordering changes |",
        "|---|---|---|---|",
    ]
    for row in result["s1_vs_s4h"]:
        a, b = row["all_100"], row["without_excluded"]
        lines.append(
            f"| {names[row['field']]} | {a['S1']:.3f} / {a['S4h']:.3f}, {a['higher']} "
            f"| {b['S1']:.3f} / {b['S4h']:.3f}, {b['higher']} "
            f"| {'yes' if row['ordering_changes'] else 'no'} |"
        )
    lines += [
        "",
        "## S5 on the 93 documents (variant all, recorded thresholds)",
        "",
        "| System | Units | Target | Threshold | Accepted / slots | Automation [95% CI] "
        "| Achieved precision [95% CI] | Correct / accepted [exact 95% CI], if accepted < 30 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, block in result["s5"].items():
        for kind in ("header", "row"):
            report = block[kind]
            for target, v in report["targets"].items():
                precision = "n/a" if v["achieved_precision"] is None else (
                    f"{v['achieved_precision']:.3f} [{v['achieved_precision_ci95'][0]:.3f}, "
                    f"{v['achieved_precision_ci95'][1]:.3f}]"
                )  # fmt: skip
                exact = v["achieved_precision_exact_ci95_clopper_pearson"]
                exact_cell = (
                    f"{v['correct_accepted']} / {v['accepted']} [{exact[0]:.3f}, {exact[1]:.3f}]"
                    if exact else ""
                )  # fmt: skip
                ci = v["automation_rate_ci95"]
                lines.append(
                    f"| {label} | {kind} | {target} | {v['threshold']} "
                    f"| {v['accepted']} / {report['slots']} "
                    f"| {v['automation_rate']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] | {precision} "
                    f"| {exact_cell} |"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    result: dict[str, Any] = {
        "addendum": ADDENDUM,
        "post_hoc": True,
        "excluded_documents": list(EXCLUDED),
        "metrics_version": "1.1.1",
        "bootstrap": {"resamples": 2000, "seed": 20261106, "unit": "document"},
        "extraction": extraction(_gold()),
        "s5": routing(),
    }
    result["s1_vs_s4h"] = orderings(result["extraction"])
    write_text_atomic(OUTPUT, json.dumps(result, indent=2) + "\n")
    write_text_atomic(OUTPUT.with_suffix(".md"), render(result))
    print("wrote", OUTPUT, "and its markdown")
    changes = [row["field"] for row in result["s1_vs_s4h"] if row["ordering_changes"]]
    print("S1 vs S4h ordering changes:", changes or "none")


if __name__ == "__main__":
    main()
