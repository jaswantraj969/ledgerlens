"""S1 on CORD v2: RapidOCR plus the deterministic extractor.

OCR is checkpointed per document, so an interrupted run resumes. Validation runs go to
evals/results/dev/. A test run needs --final and refuses to replace an existing result, so
the test split is read once per reported configuration.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np

from evals import normalization
from evals.datasets.cord import DEFAULT_RAW_DIR, EVALUABLE_FIELDS, HEADER_FIELDS, iter_documents
from evals.metrics import Outcome, header_outcome, multiset_outcome, summarize
from ledgerlens.fields import FieldRecord
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.pipeline import process
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
OCR_CACHE = ROOT / "data" / "cord-v2" / "ocr"
SPLIT_FILE = ROOT / "evals" / "splits" / "cord_v2" / "ids.json"
SCHEMA = "cord_receipt"
SYSTEM = "S1"
_CELL = re.compile(r"^line_items\[\d+\]\.(\w+)$")
_TEXT_FIELDS = {"line_items.description"}


def cached_parse(document_id: str, image: bytes, parser: RapidOcrParser) -> dict[str, Any]:
    path = OCR_CACHE / f"{hashlib.sha256(document_id.encode()).hexdigest()}.json"
    if path.exists():
        return dict(json.loads(path.read_text(encoding="utf-8")))
    started = time.perf_counter()
    parsed = parser.parse(image)
    entry = {
        "document_id": document_id,
        "ocr_seconds": time.perf_counter() - started,
        "parsed": parsed.model_dump(mode="json"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(entry), encoding="utf-8")
    temporary.replace(path)
    return entry


def predictions(records: list[FieldRecord]) -> dict[str, Any]:
    predicted: dict[str, Any] = dict.fromkeys(HEADER_FIELDS)
    predicted |= {name: [] for name in EVALUABLE_FIELDS if name.startswith("line_items.")}
    for record in records:
        if record.value_raw is None:
            continue
        if match := _CELL.match(record.name):
            predicted[f"line_items.{match[1]}"].append(record.value_raw)
        elif record.name in HEADER_FIELDS:
            predicted[record.name] = record.value_raw
    return predicted


def _key(field: str, value: str | None) -> Any:
    return normalization.text(value) if field in _TEXT_FIELDS else normalization.money(value)


def compare(field: str, predicted: Any, gold: Any) -> tuple[Outcome, int]:
    """Return the outcome and how many gold values were excluded as unparsable."""
    if field in HEADER_FIELDS:
        gold_key = _key(field, gold)
        return header_outcome(_key(field, predicted), gold_key), int(
            gold is not None and gold_key is None
        )
    gold_keys = [_key(field, value) for value in gold]
    usable = [key for key in gold_keys if key is not None]
    predicted_keys = [key for key in (_key(field, value) for value in predicted) if key is not None]
    return multiset_outcome(predicted_keys, usable), len(gold_keys) - len(usable)


def environment() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "backend/src", "evals/datasets", "evals/metrics.py"],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    ).stdout.strip()
    return {
        "git_commit": commit,
        "git_dirty": bool(dirty),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "packages": {
            name: version(name)
            for name in ("rapidocr", "onnxruntime", "numpy", "pypdfium2", "rapidfuzz")
        },
        "ocr_execution": "CPU, onnxruntime defaults",
    }


def run(split: str, output: Path) -> dict[str, Any]:
    parser = RapidOcrParser()
    schema = load_schema(SCHEMA)
    outcomes: dict[str, list[Outcome]] = {field: [] for field in EVALUABLE_FIELDS}
    excluded = dict.fromkeys(EVALUABLE_FIELDS, 0)
    seconds: list[float] = []
    extract_seconds: list[float] = []
    crashes: list[str] = []
    no_tokens: list[str] = []
    documents = 0

    for document in iter_documents(split, DEFAULT_RAW_DIR):  # type: ignore[arg-type]
        documents += 1
        try:
            entry = cached_parse(document.document_id, document.image or b"", parser)
            parsed = ParsedDocument.model_validate(entry["parsed"])
            started = time.perf_counter()
            records = process(parsed, schema)
            extract_time = time.perf_counter() - started
        except Exception as error:
            crashes.append(f"{document.document_id}: {type(error).__name__}")
            records, entry, extract_time = [], None, None  # type: ignore[assignment]
        if entry is not None:
            seconds.append(entry["ocr_seconds"] + extract_time)
            extract_seconds.append(extract_time)
            if not any(page["tokens"] for page in entry["parsed"]["pages"]):
                no_tokens.append(document.document_id)
        predicted = predictions(records)
        for field in EVALUABLE_FIELDS:
            outcome, dropped = compare(field, predicted[field], document.gold[field])
            outcomes[field].append(outcome)
            excluded[field] += dropped
        if documents % 10 == 0:
            print(f"processed {documents} documents, crashes={len(crashes)}", flush=True)

    split_info = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))[split]
    if documents != split_info["n"]:
        raise SystemExit(f"expected {split_info['n']} documents, saw {documents}")
    return {
        "system": SYSTEM,
        "dataset": "cord-v2",
        "split": split,
        "n_documents": documents,
        "schema": SCHEMA,
        "schema_version": schema.version,
        "split_sha256": split_info["sha256"],
        "normalization": {
            "version": normalization.NORMALIZATION_VERSION,
            "sha256": normalization.fingerprint(),
        },
        "bootstrap": {"resamples": 2000, "seed": 20261106, "unit": "document"},
        "fields": {field: summarize(outcomes[field]) for field in EVALUABLE_FIELDS},
        "gold_values_excluded_unparsable": excluded,
        "failures": {
            "crashes": len(crashes),
            "crash_detail": crashes,
            "documents_without_tokens": len(no_tokens),
        },
        "latency_seconds": {
            "scope": "OCR plus extraction, per document",
            "p50": float(np.percentile(seconds, 50)) if seconds else None,
            "p95": float(np.percentile(seconds, 95)) if seconds else None,
            "extraction_only_p50": float(np.percentile(extract_seconds, 50))
            if extract_seconds
            else None,
        },
        "cost_per_document_usd": 0,
        "environment": environment(),
        "output_file": output.relative_to(ROOT).as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["validation", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="required to read the test split")
    arguments = parser.parse_args()

    if arguments.split == "test":
        if not arguments.final:
            sys.exit("the test split needs --final: it is read once per configuration")
        output = RESULTS / "cord_s1_v1.json"
        if output.exists():
            sys.exit(f"{output} exists: a new configuration needs a new version")
    else:
        output = RESULTS / "dev" / "cord_s1_validation.json"

    result = run(arguments.split, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("wrote", output)


if __name__ == "__main__":
    main()
