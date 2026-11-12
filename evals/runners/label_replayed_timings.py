"""Label the replayed LLM timings of the final test results with when, and on what power, each
replayed call was originally recorded. Writes evals/results/final/replayed_timings_v1_1_1.json,
keyed by result file. The result files are not touched, so their done-marker hashes stay valid.

A call is "measured" if its cache entry was written during the step's successful attempt (from
the run metadata), and "replayed" otherwise. A replayed call's recording time is its cache file's
modification time; its power state must hold at both the start (time minus latency) and the end
of the call, otherwise it is "unknown" or "battery".

    python -m evals.runners.label_replayed_timings evals/results/final/final-run-metadata-X.json
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.atomic import write_text_atomic
from evals.power import PowerLog
from evals.runners.audit_power import cord_paths

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "evals" / "results" / "final" / "replayed_timings_v1_1_1.json"
GRACE_SECONDS = 5  # a cache entry can land just after the attempt's logged end


def _ts(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def _utc(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def call_state(log: PowerLog, path: Path) -> str:
    entry = json.loads(path.read_text(encoding="utf-8"))
    end = path.stat().st_mtime
    start = end - float(entry["response"].get("latency_seconds") or 0)
    states = {log.state_at(start), log.state_at(end)}
    if states == {"ac"}:
        return "ac"
    return "battery" if "battery" in states else "unknown"


def label(
    result: dict[str, Any], step: dict[str, Any], log: PowerLog, run_start: float
) -> dict[str, Any]:
    final = step["attempts"][-1]
    window = (_ts(final["started_utc"]), _ts(final["ended_utc"]) + GRACE_SECONDS)
    calls = [p for p in cord_paths(result) if "cache" in p.parts]
    replayed = [p for p in calls if not window[0] <= p.stat().st_mtime <= window[1]]
    states = {"ac": 0, "battery": 0, "unknown": 0}
    for path in replayed:
        states[call_state(log, path)] += 1
    times = sorted(p.stat().st_mtime for p in replayed)
    before = sum(t < run_start for t in times)
    return {
        "llm_calls": len(calls),
        "measured_in_final_attempt": len(calls) - len(replayed),
        "replayed": len(replayed),
        "replayed_recorded_first_utc": _utc(times[0]) if times else None,
        "replayed_recorded_last_utc": _utc(times[-1]) if times else None,
        "replayed_recorded_before_this_run": before,
        "replayed_recorded_earlier_in_this_run": len(replayed) - before,
        "replayed_power_at_recording": states,
        "method": "cache file time vs the step's final attempt window; power at call start and end",
    }


def main() -> None:
    metadata = json.loads((ROOT / sys.argv[1]).read_text(encoding="utf-8"))
    log = PowerLog.load(refresh=False)
    run_start = _ts(metadata["started_utc"])
    labels = {}
    for step in metadata["steps"]:
        result = json.loads((ROOT / step["output"]).read_text(encoding="utf-8"))
        if not result.get("llm"):
            continue
        labels[step["output"]] = label(result, step, log, run_start)
        print(step["name"], json.dumps(labels[step["output"]]))
    write_text_atomic(OUTPUT, json.dumps(labels, indent=2) + "\n")
    print("wrote", OUTPUT)


if __name__ == "__main__":
    main()
