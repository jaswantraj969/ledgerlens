"""Ollama smoke test on a seeded sample of CORD validation. Development only.

Validation is the only split this runner can read: it is fixed in code, not an argument. It
measures JSON validity, latency and where the model ran. Field counts are a sanity check on
ten documents, not a result. Every call goes through the replay cache. With --replay no
provider exists, so a missing entry fails instead of reaching a model.
"""

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np

from evals.datasets.cord import HEADER_FIELDS, iter_documents
from evals.runners.run_cord_s1 import OCR_CACHE, compare, environment, predictions
from ledgerlens.extraction.llm import DEFAULT_PARAMS, PROMPT_VERSION, LlmExtractor
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.pipeline import PrecomputedExtractor, process
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
SPLIT = "validation"
SAMPLE_SIZE = 10
SAMPLE_SEED = 20261106
SCHEMA = "cord_receipt"
CACHE_DIR = ROOT / "evals" / "cache" / "cord-v2"
OUTPUT = ROOT / "evals" / "results" / "dev" / "llm_smoke_{model}.json"


def sample_ids() -> list[str]:
    splits = json.loads((ROOT / "evals/splits/cord_v2/ids.json").read_text(encoding="utf-8"))
    return sorted(random.Random(SAMPLE_SEED).sample(splits[SPLIT]["ids"], SAMPLE_SIZE))  # noqa: S311


def gpu_memory_used_mib() -> int | None:
    command = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
    try:
        output = subprocess.run(command, capture_output=True, text=True, check=True)  # noqa: S603
    except (OSError, subprocess.CalledProcessError):
        return None
    return int(output.stdout.strip().splitlines()[0])


def percentile(values: list[float], q: float) -> float | None:
    return float(np.percentile(values, q)) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--replay", action="store_true")
    arguments = parser.parse_args()

    live = None if arguments.replay else OllamaProvider()
    provider = CachingProvider(ReplayCache(CACHE_DIR), live)
    extractor = LlmExtractor(provider, arguments.model)
    schema = load_schema(SCHEMA)
    wanted = set(sample_ids())
    placements: list[dict[str, Any]] = []
    gpu_before = gpu_memory_used_mib()
    rows: list[dict[str, Any]] = []

    for document in iter_documents(cast(Literal["validation"], SPLIT), with_images=False):
        if document.document_id not in wanted:
            continue
        name = hashlib.sha256(document.document_id.encode()).hexdigest()
        entry = json.loads((OCR_CACHE / f"{name}.json").read_text(encoding="utf-8"))
        parsed = ParsedDocument.model_validate(entry["parsed"])
        started = time.perf_counter()
        result = extractor.run(parsed, schema)
        seconds = time.perf_counter() - started
        records = process(parsed, schema, PrecomputedExtractor(result.records))
        predicted = predictions(records)
        counts = {
            field: compare(field, predicted[field], document.gold[field])[0]
            for field in HEADER_FIELDS
        }
        first = result.responses[0] if result.responses else None
        rows.append(
            {
                "document_id": document.document_id,
                "first_attempt_valid": result.first_attempt_valid,
                "attempts": result.attempts,
                "fell_back": result.fell_back,
                "errors": result.errors,
                "done_reason": first.done_reason if first else None,
                "cache_hit": first.cache_hit if first else None,
                "extract_seconds": seconds,
                "llm_seconds": sum(r.latency_seconds or 0 for r in result.responses),
                "load_seconds": first.load_seconds if first else None,
                "prompt_tokens": first.prompt_tokens if first else None,
                "completion_tokens": first.completion_tokens if first else None,
                "ocr_seconds": entry["ocr_seconds"],
                "header_correct": sum(o.tp for o in counts.values()),
                "header_labelled": sum(o.labelled for o in counts.values()),
                "values_absent_from_document": sum(
                    r.evidence_status == "not_found" and r.value_raw is not None for r in records
                ),
                "values_total": sum(r.value_raw is not None for r in records),
            }
        )
        print(
            f"{len(rows)}/{SAMPLE_SIZE} {seconds:.2f}s valid={result.first_attempt_valid}",
            flush=True,
        )
        if live is not None:
            placements.append(
                {
                    "after_document": len(rows),
                    "gpu_memory_used_mib": gpu_memory_used_mib(),
                    "loaded": [
                        {k: m.get(k) for k in ("name", "size", "size_vram", "context_length")}
                        for m in live.loaded_models()
                    ],
                }
            )

    if len(rows) != SAMPLE_SIZE:
        sys.exit(f"expected {SAMPLE_SIZE} documents, saw {len(rows)}")

    recorded = [row["llm_seconds"] for row in rows]
    warm = recorded[1:]
    totals = [row["llm_seconds"] + row["ocr_seconds"] for row in rows]
    n = len(rows)
    summary = {
        "purpose": "development smoke test; not an evaluation result",
        "split": SPLIT,
        "document_ids": [row["document_id"] for row in rows],
        "sample_seed": SAMPLE_SEED,
        "model": arguments.model,
        "params": DEFAULT_PARAMS,
        "prompt_version": PROMPT_VERSION,
        "schema": f"{schema.name}:{schema.version}",
        "mode": "replay" if arguments.replay else "record",
        "live_calls": provider.live_calls,
        "cache_hits": provider.hits,
        "json_valid_first_attempt": sum(r["first_attempt_valid"] for r in rows) / n,
        "json_valid_after_retry": sum(not r["fell_back"] for r in rows) / n,
        "fallbacks": sum(r["fell_back"] for r in rows),
        "truncated": sum(r["done_reason"] == "length" for r in rows),
        "llm_latency_seconds": {
            "scope": "recorded provider time per document, including any retry",
            "p50": percentile(recorded, 50),
            "p95": percentile(recorded, 95),
            "max": max(recorded),
            "first_document": recorded[0],
            "warm_p50": percentile(warm, 50),
            "warm_p95": percentile(warm, 95),
            "note": "with n=10, p95 sits close to the slowest document",
        },
        "ocr_plus_llm_latency_seconds": {
            "p50": percentile(totals, 50),
            "p95": percentile(totals, 95),
        },
        "gpu_memory_used_mib_before": gpu_before,
        "placement": placements,
        "header_correct": sum(r["header_correct"] for r in rows),
        "header_labelled": sum(r["header_labelled"] for r in rows),
        "values_absent_from_document": sum(r["values_absent_from_document"] for r in rows),
        "values_total": sum(r["values_total"] for r in rows),
        "documents": rows,
        "environment": environment(),
    }
    suffix = "_replay" if arguments.replay else ""
    output = Path(str(OUTPUT).format(model=arguments.model.replace(":", "-") + suffix))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", output)


if __name__ == "__main__":
    main()
