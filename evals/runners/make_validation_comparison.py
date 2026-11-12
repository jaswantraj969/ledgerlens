"""One table of every CORD validation result under metrics 1.1.1. Never edited by hand.

Rows: S1-S4 with prompt 1.0 (rescored from saved predictions), then S2', S3', S4' (round-two
prompt) and S4h, each read once.

    python -m evals.runners.make_validation_comparison [--split test]

With --split test it builds the same tables from the final test results, for the systems fixed in
docs/evaluation/final-test-protocol.md, into evals/results/final/.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
DEV = RESULTS / "dev"
OUTPUT = DEV / "cord_validation_comparison_v1_1_1.md"
SYSTEMS = ("s1", "s2", "s3", "s4", "s2p", "s3p", "s4p", "s4h")
TEST_SYSTEMS = ("s1", "s2p", "s3p", "s4p", "s4h")
TEST_OUTPUT = RESULTS / "final" / "cord_test_comparison_v1_1_1.md"


def source_path(name: str, split: str) -> Path:
    if split == "test":
        return RESULTS / f"cord_{name}_v1_1_1.json"
    return DEV / f"cord_{name}_validation_v1_1_1.json"


FIELDS = (("total_amount", "Total"), ("subtotal", "Subtotal"), ("tax_amount", "Tax"))


def _cell(row: dict[str, Any], name: str) -> str:
    value, interval = row[name], row[f"{name}_ci95"]
    if value is None:
        return "n/a"
    return f"{value:.3f} [{interval[0]:.3f}, {interval[1]:.3f}]" if interval else f"{value:.3f}"


def _power(result: dict[str, Any]) -> str:
    power = result.get("power")
    if not power:
        return "not recorded"
    if power["label"] == "battery-affected":
        total = power["timings_ac"] + power["timings_battery"] + power["timings_unknown"]
        return f"**battery-affected** ({power['timings_battery']} of {total} timings)"
    return str(power["label"])


def _timings(result: dict[str, Any]) -> str:
    """The timing source, plus when and on what power any replayed calls were first recorded."""
    text = str(result["latency_seconds"]["source"])
    labels_path = RESULTS / "final" / "replayed_timings_v1_1_1.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    replayed = labels.get(result.get("output_file", ""))
    if not replayed or not replayed["replayed"]:
        return text
    states = replayed["replayed_power_at_recording"]
    return str(
        f"{text}. Replayed calls ({replayed['replayed']}) recorded "
        f"{replayed['replayed_recorded_first_utc']} to {replayed['replayed_recorded_last_utc']}, "
        f"{replayed['replayed_recorded_before_this_run']} of them before this run; power at "
        f"recording: ac {states['ac']}, battery {states['battery']}, unknown {states['unknown']}"
    )


def _seconds(block: dict[str, Any]) -> str:
    return "n/a" if not block["n"] else f"{block['p50']:.2f} / {block['p95']:.2f}"


_FIELD_METRICS = (
    *("n_present", "n_absent", "precision", "precision_ci95", "recall", "recall_ci95"),
    *("f1", "f1_ci95", "false_fill_rate", "false_fill_rate_ci95"),
)


def _summary(loaded: dict[str, dict[str, Any]], split: str = "validation") -> dict[str, Any]:
    """The table's numbers as JSON, one entry per system, with the source file of each."""
    systems = []
    for name, result in loaded.items():
        latency = result["latency_seconds"]
        llm = result.get("llm") or {}
        systems.append(
            {
                "system": result["system"],
                "source": source_path(name, split).relative_to(ROOT).as_posix(),
                "model": llm.get("model"),
                "prompt": llm.get("prompt_versions", {}).get("a"),
                "n_documents": result["n_documents"],
                "fields": {
                    key: {metric: result["fields"][key][metric] for metric in _FIELD_METRICS}
                    for key, _ in FIELDS
                },
                "line_items_row_level": result["line_items_row_level"],
                "failures": result["failures"],
                "values_withheld": result["verification"]["values_withheld"],
                "latency_seconds": {
                    "source": latency["source"],
                    "warm_llm": latency["warm_llm"] if llm else None,
                    "warm_total": latency["warm_total"],
                    "cold": latency.get("cold"),
                },
                "power": result.get("power"),
                "lowest_available_system_ram_gib": result.get("memory_live_run", result["memory"])[
                    "lowest_available_system_ram_gib"
                ],
            }
        )
    return {
        "metrics_version": next(iter(loaded.values()))["metrics_version"],
        "split": split,
        "note": "Development only. Test has not been read for these systems."
        if split == "validation"
        else "Final test read, once per configuration (docs/evaluation/final-test-protocol.md).",
        "systems": systems,
    }


def main(argv: list[str] | None = None) -> None:
    arguments = sys.argv[1:] if argv is None else argv
    split = "test" if arguments == ["--split", "test"] else "validation"
    output = TEST_OUTPUT if split == "test" else OUTPUT
    loaded = {}
    for name in TEST_SYSTEMS if split == "test" else SYSTEMS:
        path = source_path(name, split)
        if path.exists():
            loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    heading = (
        "# CORD test, final read (metrics 1.1.1)"
        if split == "test"
        else "# CORD validation, all systems (metrics 1.1.1, development only)"
    )
    note = (
        "Each configuration was read once on test under docs/evaluation/final-test-protocol.md; "
        "S1 is the Phase 4 test read."
        if split == "test"
        else "Primed systems use the round-two prompt chosen on the train subset; S4h was "
        "pre-registered before any result. Each was read once on validation."
    )
    lines = [
        heading,
        "",
        "Generated by `evals/runners/make_validation_comparison.py`. Do not edit by hand. " + note,
        "",
        "## Single-valued fields: precision / recall / F1 [95% CI], false fill rate",
        "",
        "| System | Prompt | Field | Precision | Recall | F1 | False fill |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in loaded.values():
        prompt = (result.get("llm") or {}).get("prompt_versions", {}).get("a", "none")
        for key, label in FIELDS:
            row = result["fields"][key]
            lines.append(
                f"| {result['system']} | {prompt} | {label} | {_cell(row, 'precision')} "
                f"| {_cell(row, 'recall')} | {_cell(row, 'f1')} | {_cell(row, 'false_fill_rate')} |"
            )
    lines += [
        "",
        "## Rows, failures and latency",
        "",
        "| System | Rows correct / predicted / gold | Row F1 [95% CI] | Failed | Pass fallbacks "
        "| Retries | Truncated | Withheld | Warm LLM p50 / p95 s | Warm total p50 / p95 s "
        "| Cold docs: load s; cold LLM s excl. load | Lowest free RAM GiB | Timings | Power |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in loaded.values():
        rows = result["line_items_row_level"]
        failures = result["failures"]
        latency = result["latency_seconds"]
        cold = latency.get("cold", {"documents": 0})
        cold_text = (
            "none"
            if not cold["documents"]
            else "; ".join(
                f"{load:.1f}; {llm:.1f}"
                for load, llm in zip(
                    cold["model_load_seconds"], cold["cold_llm_seconds_excluding_load"], strict=True
                )
            )
        )
        memory = result.get("memory_live_run", result["memory"])
        warm_llm = _seconds(latency["warm_llm"]) if result.get("llm") else "none (no model)"
        lines.append(
            f"| {result['system']} | {rows['rows_correct']} / {rows['rows_predicted']} / "
            f"{rows['rows_gold']} | {_cell(rows, 'f1')} | {failures['failed_extractions']} "
            f"| {failures['pass_fallbacks']} | {failures['retries']} "
            f"| {failures['truncated_replies']} | {result['verification']['values_withheld']} "
            f"| {warm_llm} | {_seconds(latency['warm_total'])} | {cold_text} "
            f"| {memory['lowest_available_system_ram_gib']} | {_timings(result)} "
            f"| {_power(result)} |"
        )
    lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    output.with_suffix(".json").write_text(
        json.dumps(_summary(loaded, split), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print("wrote", output, "systems:", ", ".join(r["system"] for r in loaded.values()))


if __name__ == "__main__":
    main()
