"""Estimate LLM time for the final test protocol from replies already recorded on AC power.

Uses llama3.2:3b replies at num_ctx 2304 (prompt 2.2) whose recording time falls in an AC
interval of the Windows power log, and the calls per document of S4h on validation. Touches no
test data.

    python -m evals.runners.estimate_runtime
"""

import json
from pathlib import Path

import numpy as np

from evals.power import PowerLog

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "evals" / "cache" / "cord-v2"
S4H_VALIDATION = ROOT / "evals" / "results" / "dev" / "cord_s4h_validation_v1_1_1.json"
NUM_PREDICT = 1024
DOCUMENTS = 100
# LLM document runs in the protocol: clean test once (S2', S3', S4', S4h share passes A and B),
# then S4h on 4 degraded variants (2 perturbations x 2 severities).
LLM_DOCUMENT_RUNS = {"clean test": DOCUMENTS, "degradation, S4h": 4 * DOCUMENTS}


def main() -> None:
    log = PowerLog.load(refresh=False)
    seconds, rates = [], []
    for path in CACHE.glob("*/*.json"):
        finished = path.stat().st_mtime
        if log.state_at(finished) != "ac":
            continue
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry["model"] != "llama3.2:3b" or entry["params"].get("num_ctx") != 2304:
            continue
        response = entry["response"]
        # A call must start on AC too: one call spanning a sleep ends on AC after 8 hours.
        if log.state_at(finished - (response["latency_seconds"] or 0)) != "ac":
            continue
        generate = (response["latency_seconds"] or 0) - (response["load_seconds"] or 0)
        if generate > 0 and response["completion_tokens"]:
            seconds.append(generate)
            rates.append(response["completion_tokens"] / generate)
    validation = json.loads(S4H_VALIDATION.read_text(encoding="utf-8"))
    llm = validation["llm"]
    calls_per_document = (llm["live_calls"] + llm["cache_hits"]) / validation["n_documents"]
    mean = float(np.mean(seconds))
    worst = NUM_PREDICT / float(np.median(rates))  # every reply runs to num_predict
    runs = sum(LLM_DOCUMENT_RUNS.values())
    report = {
        "ac_calls_used": len(seconds),
        "seconds_per_call_mean": round(mean, 2),
        "seconds_per_call_p95": round(float(np.percentile(seconds, 95)), 2),
        "tokens_per_second_median": round(float(np.median(rates)), 1),
        "calls_per_document_s4h_validation": round(calls_per_document, 2),
        "document_runs": LLM_DOCUMENT_RUNS,
        "expected_llm_hours": round(runs * calls_per_document * mean / 3600, 2),
        "worst_case_llm_hours_every_reply_truncated": round(
            runs * calls_per_document * worst / 3600, 2
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
