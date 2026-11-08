"""Per-call latency of recorded llama3.2:3b replies, split by when they were recorded.

Segments are UTC time windows on the cache file's modification time (when the reply was first
recorded). Calls are not pooled across segments. Prompt 2.2, num_ctx 2304 only.

    python -m evals.runners.segment_latency NAME START END [NAME START END ...]
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "evals" / "cache" / "cord-v2"


def _stamp(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).timestamp()


def segment(start: float, end: float) -> dict[str, Any]:
    calls = []
    for path in CACHE.glob("*/*.json"):
        modified = path.stat().st_mtime
        if not start <= modified < end:
            continue
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry["model"] != "llama3.2:3b" or entry["params"].get("num_ctx") != 2304:
            continue
        response = entry["response"]
        generate = (response["latency_seconds"] or 0) - (response["load_seconds"] or 0)
        calls.append((generate, response["completion_tokens"] or 0, response["prompt_tokens"] or 0,
                      response["done_reason"]))  # fmt: skip
    if not calls:
        return {"calls": 0}
    seconds = np.array([c[0] for c in calls])
    tokens = np.array([c[1] for c in calls])
    return {
        "calls": len(calls),
        "seconds_p50": round(float(np.percentile(seconds, 50)), 2),
        "seconds_p95": round(float(np.percentile(seconds, 95)), 2),
        "completion_tokens_p50": int(np.percentile(tokens, 50)),
        "completion_tokens_per_second_median": round(float(np.median(tokens / seconds)), 1),
        "truncated": sum(c[3] == "length" for c in calls),
        "prompt_tokens_p50": int(np.percentile([c[2] for c in calls], 50)),
    }


def main() -> None:
    arguments = sys.argv[1:]
    result = {}
    for index in range(0, len(arguments), 3):
        name, start, end = arguments[index : index + 3]
        result[name] = {"window_utc": [start, end], **segment(_stamp(start), _stamp(end))}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
