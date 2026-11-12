"""S5-S1 next to S5-S4h on validation. Never edited by hand.

    python -m evals.runners.make_s5_table s1 s4h
    python -m evals.runners.make_s5_table --final s1 s4h

With --final the table is built from the final test results (evals/results/final/).

Thresholds are chosen on validation, so these validation rates are in-sample for the thresholds
and optimistic. The calibrators were fitted on train only. Test is not read here.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "evals" / "results" / "dev"
OUTPUT = DEV / "cord_s5_validation_comparison_v1_1_1.md"
RESULTS = ROOT / "evals" / "results"
FINAL_OUTPUT = RESULTS / "final" / "cord_s5_test_v1_1_1.md"
WORKLOAD = RESULTS / "final" / "cord_s5_review_workload_v1_1_1.json"
# Below this many accepted values the bootstrap interval of precision is degenerate (all
# accepted values correct gives [1, 1]), so an exact Clopper-Pearson interval is added.
SMALL_SAMPLE = 30
# Test blocks per variant, with the label each gets in the table.
TEST_BLOCKS = {
    "all": (("test", "all"),),
    "grouped": (
        ("test_unseen_groups", "grouped, unseen groups"),
        ("test_calibration_groups", "grouped, calibration groups"),
    ),
}


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _ci(values: list[float] | None) -> str:
    return "" if not values else f" [{values[0]:.3f}, {values[1]:.3f}]"


def clopper_pearson(correct: int, accepted: int) -> list[float]:
    """Exact two-sided 95% interval for a binomial proportion."""
    from scipy.stats import beta

    low = 0.0 if correct == 0 else float(beta.ppf(0.025, correct, accepted - correct + 1))
    high = 1.0 if correct == accepted else float(beta.ppf(0.975, correct + 1, accepted - correct))
    return [low, high]


def exact_interval(values: dict[str, Any]) -> tuple[int, list[float]] | None:
    """(correct, exact interval) when fewer than SMALL_SAMPLE values were accepted, else None.
    The correct count is recovered from the recorded precision and checked to be whole."""
    accepted, precision = values["accepted"], values["achieved_precision"]
    if precision is None or not 0 < accepted < SMALL_SAMPLE:
        return None
    correct = round(precision * accepted)
    if abs(correct / accepted - precision) > 1e-9:
        raise ValueError(f"precision {precision} is not a whole count of {accepted}")
    return correct, clopper_pearson(correct, accepted)


def rows(name: str, variant: str, block: dict[str, Any], exact: bool = False) -> list[str]:
    lines = []
    for kind in ("header", "row"):
        report = block[kind]
        for target, values in report["targets"].items():
            small = exact_interval(values) if exact else None
            exact_cell = (
                ""
                if not exact
                else (f"| {small[0]} / {values['accepted']}{_ci(small[1])} " if small else "| ")
            )
            lines.append(
                f"| {name} | {variant} | {kind} | {target} "
                f"| {_rate(values['threshold'])} "
                f"| {values['accepted']} / {report['slots']} "
                f"| {_rate(values['automation_rate'])}{_ci(values['automation_rate_ci95'])} "
                f"| {_rate(values['achieved_precision'])}{_ci(values['achieved_precision_ci95'])} "
                f"{exact_cell}"
                f"| {'yes' if values['target_met'] else 'no'} "
                f"| {_rate(report['ece_10_bins'])} | {_rate(report['brier'])} "
                f"| {_rate(report['roc_auc'])} | {report['units']} |"
            )
    return lines


def workload_section() -> tuple[list[str], dict[str, Any] | None]:
    if not WORKLOAD.exists():
        return [], None
    data = json.loads(WORKLOAD.read_text(encoding="utf-8"))
    lines = [
        "",
        "## Review workload on test (variant all)",
        "",
        "Slots routed to human review per document: mean [95% document-bootstrap CI]. Header "
        "slots are 3 per document; row slots are predicted rows. Recomputed per document by "
        "`evals/runners/review_workload.py`, whose accepted totals equal the table above.",
        "",
        "| System | Target | Header slots routed | Rows routed | All slots routed "
        "| Share of slots routed | Predicted rows per document |",
        "|---|---|---|---|---|---|---|",
    ]
    for system, block in data["systems"].items():
        for target, values in block["targets"].items():
            cells = [
                values[key]
                for key in (
                    "header_slots_routed_per_document",
                    "rows_routed_per_document",
                    "all_slots_routed_per_document",
                )
            ]
            lines.append(
                f"| {system} | {target} | "
                + " | ".join(f"{_rate(c['mean'])}{_ci(c['ci95'])}" for c in cells)
                + f" | {_rate(values['share_of_slots_routed'])} "
                f"| {_rate(values['predicted_rows_per_document'])} |"
            )
    return lines, data


def records(name: str, variant: str, block: dict[str, Any], source: Path) -> list[dict[str, Any]]:
    """The table's rows as JSON, with full precision and the source file of each."""
    out = []
    for kind in ("header", "row"):
        report = block[kind]
        for target, values in report["targets"].items():
            small = exact_interval(values)
            out.append(
                {
                    "system": name,
                    "variant": variant,
                    "units": kind,
                    "target_precision": float(target),
                    "threshold": values["threshold"],
                    "accepted": values["accepted"],
                    "slots": report["slots"],
                    "automation_rate": values["automation_rate"],
                    "automation_rate_ci95": values["automation_rate_ci95"],
                    "achieved_precision": values["achieved_precision"],
                    "achieved_precision_ci95": values["achieved_precision_ci95"],
                    "correct_accepted": small[0] if small else None,
                    "achieved_precision_exact_ci95_clopper_pearson": small[1] if small else None,
                    "small_sample": small is not None,
                    "target_met": values["target_met"],
                    "ece_10_bins": report["ece_10_bins"],
                    "brier": report["brier"],
                    "roc_auc": report["roc_auc"],
                    "units_scored": report["units"],
                    "documents": report["documents"],
                    "source": source.relative_to(ROOT).as_posix(),
                }
            )
    return out


def final(bases: list[str]) -> None:
    lines = [
        "# S5 on test: S5-S1 next to S5-S4h (metrics 1.1.1, final read)",
        "",
        "Generated by `evals/runners/make_s5_table.py --final`. Do not edit by hand. Calibrators "
        "were fitted on CORD train only and thresholds chosen on validation only, before test "
        "was read, under docs/evaluation/final-test-protocol.md. Test was read once.",
        "",
        "| System | Variant | Units | Target precision | Threshold | Accepted / slots "
        "| Automation [95% CI] | Achieved precision [95% bootstrap CI] "
        "| Correct / accepted [exact 95% CI], if accepted < 30 | Target met | ECE | Brier "
        "| ROC-AUC | Units scored |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    summary: list[dict[str, Any]] = []
    for base in bases:
        for variant, suffix in (("all", ""), ("grouped", "_grouped")):
            path = RESULTS / f"cord_s5_{base}{suffix}_v1_1_1.json"
            if not path.exists():
                continue
            result = json.loads(path.read_text(encoding="utf-8"))
            for key, label in TEST_BLOCKS[variant]:
                lines += rows(result["system"], label, result[key], exact=True)
                summary += records(result["system"], label, result[key], path)
    lines += [
        "",
        "Slots: header slots are 3 per document, filled or not; row slots are predicted rows. "
        "Grouped: fitted and thresholded on calibration-group documents; test is reported "
        "separately for documents of the unseen evaluation groups and of the calibration groups.",
        "",
        f"Small samples: where fewer than {SMALL_SAMPLE} values were accepted, the bootstrap "
        "interval of achieved precision is degenerate (when every accepted value is correct it "
        "is [1.000, 1.000]), so an exact Clopper-Pearson 95% interval is shown. At these sizes "
        '"target met" is not evidence that the target holds: every such exact interval reaches '
        "well below 0.98.",
    ]
    workload_lines, workload = workload_section()
    lines += [*workload_lines, ""]
    FINAL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FINAL_OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    summary_json = {"metrics_version": "1.1.1", "split": "test", "rows": summary,
                    "review_workload": workload}  # fmt: skip
    FINAL_OUTPUT.with_suffix(".json").write_text(
        json.dumps(summary_json, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print("wrote", FINAL_OUTPUT, "and its JSON")


def main(argv: list[str] | None = None) -> None:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments[:1] == ["--final"]:
        final(arguments[1:])
        return
    lines = [
        "# S5 on validation: S5-S1 next to S5-S4h (metrics 1.1.1, development only)",
        "",
        "Generated by `evals/runners/make_s5_table.py`. Do not edit by hand. Calibrators were "
        "fitted on CORD train predictions only. Thresholds were chosen on these validation "
        "units, so the rates below are in-sample for the thresholds and optimistic. Test has "
        "not been read. Probabilities are from calibrators fitted on train; calibration error "
        "here is measured on validation, not on a separate test split.",
        "",
        "| System | Variant | Units | Target precision | Threshold | Accepted / slots "
        "| Automation [95% CI] | Achieved precision [95% CI] | Target met | ECE | Brier "
        "| ROC-AUC | Units scored |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for base in arguments:
        for suffix in ("", "_grouped"):
            path = DEV / f"cord_s5_{base}{suffix}_validation_v1_1_1.json"
            if not path.exists():
                continue
            result = json.loads(path.read_text(encoding="utf-8"))
            lines += rows(result["system"], result["variant"], result["validation"])
    lines += [
        "",
        "Slots: header slots are 3 per document, filled or not; row slots are predicted rows. "
        "In the grouped variant, validation holds only calibration-group documents.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote", OUTPUT)


if __name__ == "__main__":
    main()
