"""Rescore saved CORD predictions under the current metrics version. Nothing is rerun.

The predictions file must hash to the value recorded in the source results file. Every block
that does not come from scoring (failures, latency, memory, environment) is copied from the
source. The rescored metrics must equal the source's, apart from keys the new version adds.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from evals.datasets.cord import (
    DEFAULT_RAW_DIR,
    HEADER_FIELDS,
    ROW_FIELDS,
    iter_documents,
)
from evals.metrics import METRICS_VERSION
from evals.runners.run_cord_s1 import environment
from evals.scoring import DocumentPrediction, score

ROOT = Path(__file__).resolve().parents[2]
SCORED_KEYS = (
    "fields",
    "gold_values_excluded_unparsable",
    "line_items_row_level",
    "line_items_set_based",
)


def differences(old: Any, new: Any, path: str = "") -> list[str]:
    """Paths where `old` and `new` differ. Keys only in `new` are additions, not differences."""
    if isinstance(old, dict) and isinstance(new, dict):
        found = []
        for key in old:
            if key not in new:
                found.append(f"{path}.{key} missing")
            else:
                found += differences(old[key], new[key], f"{path}.{key}")
        return found
    return [] if old == new else [f"{path}: {old!r} != {new!r}"]


def output_name(source: Path) -> Path:
    stem = source.stem
    if not stem.endswith("_v1_1"):
        sys.exit(f"{source.name}: expected a metrics 1.1 results file")
    return source.with_name(f"{stem}_1.json")


def rescore(source: Path, predictions_path: Path) -> tuple[dict[str, Any], int]:
    result = json.loads(source.read_text(encoding="utf-8"))
    raw = predictions_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != result["predictions_sha256"]:
        sys.exit(f"{predictions_path.name}: sha256 {digest} does not match the results file")
    predictions = [DocumentPrediction(**row) for row in json.loads(raw)]
    wanted = {p.document_id for p in predictions}
    gold_headers: dict[str, dict[str, str | None]] = {}
    gold_rows: dict[str, list[dict[str, str | None]]] = {}
    for document in iter_documents(result["split"], DEFAULT_RAW_DIR, with_images=False):
        if document.document_id in wanted:
            gold_headers[document.document_id] = {f: document.gold[f] for f in HEADER_FIELDS}
            gold_rows[document.document_id] = document.gold_rows
    if set(gold_headers) != wanted:
        sys.exit("gold labels do not cover every prediction")
    scored = score(predictions, gold_headers, gold_rows, tuple(HEADER_FIELDS), tuple(ROW_FIELDS))
    found = [d for key in SCORED_KEYS for d in differences(result[key], scored[key], key)]
    if found:
        sys.exit("rescored metrics differ from the source:\n" + "\n".join(found))
    compared = sum(1 for key in SCORED_KEYS for _ in _leaves(result[key]))
    rescored = dict(result) | {key: scored[key] for key in SCORED_KEYS}
    rescored["metrics_version"] = METRICS_VERSION
    rescored["normalization"] = scored["normalization"]
    rescored["rescored_from"] = {
        "results_file": source.relative_to(ROOT).as_posix(),
        "metrics_version": result["metrics_version"],
        "values_compared": compared,
        "values_different": 0,
        "environment": environment(),
    }
    return rescored, compared


def _leaves(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    return [value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("predictions", type=Path)
    arguments = parser.parse_args()
    arguments.source = arguments.source.resolve()
    arguments.predictions = arguments.predictions.resolve()
    output = output_name(arguments.source)
    rescored, compared = rescore(arguments.source, arguments.predictions)
    if rescored["split"] == "test" and output.exists():
        sys.exit(f"{output} exists: test results are never replaced")
    if rescored["normalization"] != json.loads(arguments.source.read_text())["normalization"]:
        sys.exit("normalisation changed since the source was scored")
    rescored["output_file"] = output.relative_to(ROOT).as_posix()
    output.write_text(json.dumps(rescored, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{arguments.source.name}: {compared} values compared, 0 different; wrote {output.name}")


if __name__ == "__main__":
    main()
