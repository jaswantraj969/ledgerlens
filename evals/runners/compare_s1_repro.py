"""Compare a reproduction of S1 with cord_s1_v1.json, value by value. Exit 1 on any difference.

Every metric, count and interval must match exactly. Latency is a timing, so it is printed but
not compared. Environment fields are expected to change.
"""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "evals" / "results" / "cord_s1_v1.json"
REPRODUCTION = ROOT / "evals" / "results" / "repro" / "cord_s1_test_repro.json"
COMPARED = (
    "system",
    "dataset",
    "split",
    "n_documents",
    "schema",
    "schema_version",
    "split_sha256",
    "normalization",
    "bootstrap",
    "fields",
    "gold_values_excluded_unparsable",
    "failures",
)


def leaves(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        return {k: v for key in value for k, v in leaves(value[key], f"{path}.{key}").items()}
    if isinstance(value, list):
        return {
            k: v for i, item in enumerate(value) for k, v in leaves(item, f"{path}[{i}]").items()
        }
    return {path: value}


def main() -> int:
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    reproduction = json.loads(REPRODUCTION.read_text(encoding="utf-8"))
    left = {k: v for key in COMPARED for k, v in leaves(original[key], key).items()}
    right = {k: v for key in COMPARED for k, v in leaves(reproduction[key], key).items()}
    differences = [
        (key, left.get(key, "<absent>"), right.get(key, "<absent>"))
        for key in sorted(left.keys() | right.keys())
        if left.get(key) != right.get(key)
    ]
    print(f"original commit      {original['environment']['git_commit']}")
    print(f"reproduction commit  {reproduction['environment']['git_commit']}")
    print(f"reproduction dirty   {reproduction['environment']['git_dirty']}")
    print(f"values compared      {len(left)}")
    print(f"values different     {len(differences)}")
    for key, before, after in differences:
        print(f"DIFF {key}: {before} -> {after}")
    for name in ("p50", "p95", "extraction_only_p50"):
        print(
            f"latency {name}: {original['latency_seconds'][name]:.4f} s -> "
            f"{reproduction['latency_seconds'][name]:.4f} s (timing, not compared)"
        )
    print("RESULT: IDENTICAL" if not differences else "RESULT: DIFFERENT")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
