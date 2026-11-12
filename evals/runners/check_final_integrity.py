"""Integrity checks on the final test run, from its saved files only. Changes nothing.

    python -m evals.runners.check_final_integrity evals/results/final/final-run-metadata-X.json

Checks: the S1 records rerun reproduced the recorded predictions; every done-marker matches its
output; every timed result was recorded on AC only; the abort records and their resumption; the
fixed settings of every LLM result; one code commit across results; and that the S5 test
thresholds are the ones chosen on validation. Prints one PASS/FAIL line per check; exits 1 on any
FAIL.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
S1_RECORDED_SHA = "8b3fccde4d463e2d75c1f0ce007d2b34f256dfe60c5518a943b039cca9ab7e47"
FIXED_LLM = {
    "model": "llama3.2:3b",
    "prompt_versions": {"a": "a-2.2", "b": "b-2.2"},
    "params": {"temperature": 0, "seed": 20261106, "num_ctx": 2304, "num_predict": 1024},
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_rerun() -> tuple[bool, str]:
    rerun = _load(RESULTS / "repro" / "cord_s1_test_records_rerun_v1_1_1.json")
    actual = rerun["predictions_sha256"]
    match = actual == rerun["records_rerun_of_predictions_sha256"] == S1_RECORDED_SHA
    verdict = "match" if match else "MISMATCH"
    return (
        match,
        f"S1 records rerun predictions {actual[:12]} vs recorded {S1_RECORDED_SHA[:12]}: {verdict}",
    )


def check_markers(steps: list[dict[str, Any]]) -> list[tuple[bool, str]]:
    markers = sorted((RESULTS / "final" / "done").glob("*.json"))
    mismatched, recovered = [], []
    for path in markers:
        marker = _load(path)
        actual = hashlib.sha256((ROOT / marker["output"]).read_bytes()).hexdigest()
        if actual != marker["output_sha256"]:
            mismatched.append(marker["step"])
        if marker["recovered_without_marker"]:
            recovered.append(marker["step"])
    counted = f"done-markers: {len(markers)} for {len(steps)} steps"
    return [
        (not mismatched and len(markers) == len(steps),
         f"{counted}; hash mismatches {mismatched or 'none'}"),
        (not recovered, f"recovered markers: {recovered or 'none'}"),
    ]  # fmt: skip


def check_power(steps: list[dict[str, Any]]) -> tuple[bool, str]:
    battery = []
    for step in steps:
        power = _load(ROOT / step["output"]).get("power")
        if power is None:
            continue
        counts = (
            f"ac {power['timings_ac']}, battery {power['timings_battery']}, "
            f"unknown {power['timings_unknown']}"
        )
        print(f"  power {step['name']}: {power['label']} ({counts})")
        if power["label"] != "ac":
            battery.append(step["name"])
    return not battery, f"timed results not AC-only: {battery or 'none'}"


def check_aborts(metadata: dict[str, Any]) -> tuple[bool, str]:
    by_step: dict[str, list[str]] = {}
    for step in metadata["steps"]:
        for attempt in step["attempts"]:
            by_step.setdefault(step["name"], []).extend(attempt["abort_records"])
    by_step = {name: records for name, records in by_step.items() if records}
    records = [record for names in by_step.values() for record in names]
    reasons = [str(_load(RESULTS / "aborted" / r).get("reason", "")).lower() for r in records]
    memory_only = all("ram" in reason or "memory" in reason for reason in reasons)
    resumed = all(s["status"] == "done" for s in metadata["steps"] if s["name"] in by_step)
    counts = json.dumps({name: len(names) for name, names in by_step.items()})
    passed = len(records) == metadata["memory_aborts"] and memory_only and resumed
    detail = (
        f"aborts: {len(records)} (metadata {metadata['memory_aborts']}), memory only "
        f"{memory_only}, each aborted step then completed with its one fixed command "
        f"{resumed}: {counts}"
    )
    return passed, detail


def check_settings(steps: list[dict[str, Any]]) -> list[tuple[bool, str]]:
    commits, off = set(), []
    for step in steps:
        result = _load(ROOT / step["output"])
        environment = result.get("environment", {})
        commits.add((environment.get("git_commit", "")[:7], environment.get("git_dirty")))
        llm = result.get("llm")
        if llm and {key: llm[key] for key in FIXED_LLM} != FIXED_LLM:
            off.append(step["name"])
    one_clean = len(commits) == 1 and next(iter(commits))[1] is False
    return [
        (one_clean, f"code commit and dirty flag across results: {sorted(commits)}"),
        (not off, f"LLM results off the fixed settings: {off or 'none'}"),
    ]


def check_thresholds() -> tuple[bool, str]:
    changed = []
    for base in ("s1", "s1_grouped", "s4h", "s4h_grouped"):
        test = _load(RESULTS / f"cord_s5_{base}_v1_1_1.json")["thresholds"]
        validation = _load(RESULTS / "dev" / f"cord_s5_{base}_validation_v1_1_1.json")
        if test != validation["thresholds"]:
            changed.append(base)
    return not changed, f"S5 test thresholds differ from validation-chosen: {changed or 'none'}"


def main() -> int:
    metadata = _load(ROOT / sys.argv[1])
    steps = metadata["steps"]
    lines = [check_rerun(), *check_markers(steps), check_power(steps), check_aborts(metadata),
             *check_settings(steps), check_thresholds()]  # fmt: skip
    for passed, text in lines:
        print(("PASS " if passed else "FAIL ") + text)
    return 0 if all(passed for passed, _ in lines) else 1


if __name__ == "__main__":
    sys.exit(main())
