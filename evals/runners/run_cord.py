"""Evaluate one system on CORD under metrics 1.1. One worker, no parallel model calls.

Validation results go to evals/results/dev/. Reading the test split needs --final and refuses
to replace a result. Per-document predictions are saved under data/ (gitignored), with their
hash in the results file. A replay miss or provider failure counts as a failed extraction.
"""

import argparse
import hashlib
import json
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import psutil

from evals.datasets.cord import DEFAULT_RAW_DIR, HEADER_FIELDS, ROW_FIELDS, iter_documents
from evals.runners.run_cord_s1 import OCR_CACHE, SPLIT_FILE, cached_parse, environment
from evals.scoring import DocumentPrediction, score, to_prediction
from evals.systems import LLM_SYSTEMS, SystemOutput, build_system
from ledgerlens.extraction.llm import DEFAULT_PARAMS, PROMPT_VERSIONS
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
PREDICTIONS = ROOT / "data" / "cord-v2" / "predictions"
CACHE_DIR = ROOT / "evals" / "cache" / "cord-v2"
SCHEMA = "cord_receipt"
DEFAULT_MODEL = "llama3.2:3b"
LOAD_THRESHOLD_SECONDS = 1.0
GIB = 1024**3


class MemoryLog(threading.Thread):
    """Samples this process, the model runner and free system RAM."""

    def __init__(self, interval: float = 2.0) -> None:
        super().__init__(daemon=True)
        self.interval = interval
        self.stop_event = threading.Event()
        self.peak_process = 0
        self.peak_runner = 0
        self.lowest_available = psutil.virtual_memory().available

    def run(self) -> None:
        own = psutil.Process()
        while not self.stop_event.wait(self.interval):
            self.peak_process = max(self.peak_process, own.memory_info().rss)
            self.lowest_available = min(self.lowest_available, psutil.virtual_memory().available)
            for process in psutil.process_iter(["name", "memory_info"]):
                name = (process.info.get("name") or "").lower()
                memory = process.info.get("memory_info")
                if memory is not None and ("llama-server" in name or "ollama" in name):
                    self.peak_runner = max(self.peak_runner, memory.rss)

    def report(self) -> dict[str, float | int]:
        self.stop_event.set()
        return {
            "peak_process_rss_gib": round(self.peak_process / GIB, 3),
            "peak_model_runner_rss_gib": round(self.peak_runner / GIB, 3),
            "lowest_available_system_ram_gib": round(self.lowest_available / GIB, 3),
            "total_system_ram_gib": round(psutil.virtual_memory().total / GIB, 3),
        }


def percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "p50": None, "p95": None}
    return {
        "n": len(values),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
    }


def llm_timing(output: SystemOutput) -> tuple[float, float]:
    """Return (LLM seconds with load removed, load seconds) for one document."""
    load = sum(r.load_seconds or 0 for r in output.responses)
    total = sum(r.latency_seconds or 0 for r in output.responses)
    return max(total - load, 0.0), load


def latency_report(rows: list[dict[str, Any]], *, replayed: bool) -> dict[str, Any]:
    cold = [row for row in rows if row["load_seconds"] > LOAD_THRESHOLD_SECONDS]
    warm = [row for row in rows if row["load_seconds"] <= LOAD_THRESHOLD_SECONDS]
    return {
        "source": "recorded when the call was first made" if replayed else "measured in this run",
        "ocr": percentiles([row["ocr_seconds"] for row in rows]),
        "extraction_excluding_llm": percentiles([row["local_seconds"] for row in rows]),
        "warm_llm": percentiles([row["llm_seconds"] for row in warm]),
        "warm_total": percentiles(
            [row["ocr_seconds"] + row["llm_seconds"] + row["local_seconds"] for row in warm]
        ),
        "cold": {
            "documents": len(cold),
            "model_load_seconds": [row["load_seconds"] for row in cold],
            "cold_llm_seconds_excluding_load": [row["llm_seconds"] for row in cold],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["S1", *LLM_SYSTEMS], required=True)
    parser.add_argument("--split", choices=["validation", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="required to read the test split")
    parser.add_argument("--replay", action="store_true", help="never call a model")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    arguments = parser.parse_args()

    name = arguments.system.lower()
    if arguments.split == "test":
        if not arguments.final:
            sys.exit("the test split needs --final: it is read once per configuration")
        output_path = RESULTS / f"cord_{name}_v1_1.json"
        if output_path.exists():
            sys.exit(f"{output_path} exists: a new configuration needs a new version")
    else:
        output_path = RESULTS / "dev" / f"cord_{name}_validation_v1_1.json"

    uses_llm = arguments.system in LLM_SYSTEMS
    live = OllamaProvider() if uses_llm and not arguments.replay else None
    provider = CachingProvider(ReplayCache(CACHE_DIR), live) if uses_llm else None
    system = build_system(arguments.system, provider, arguments.model)
    schema = load_schema(SCHEMA)
    ocr = RapidOcrParser()
    memory = MemoryLog()
    memory.start()

    predictions: list[DocumentPrediction] = []
    gold_headers: dict[str, dict[str, str | None]] = {}
    gold_rows: dict[str, list[dict[str, str | None]]] = {}
    rows: list[dict[str, Any]] = []
    crashes: list[str] = []

    for document in iter_documents(arguments.split, DEFAULT_RAW_DIR):
        gold_headers[document.document_id] = {f: document.gold[f] for f in HEADER_FIELDS}
        gold_rows[document.document_id] = document.gold_rows
        try:
            entry = cached_parse(document.document_id, document.image or b"", ocr, OCR_CACHE)
            parsed = ParsedDocument.model_validate(entry["parsed"])
            started = time.perf_counter()
            output = system(parsed, schema)
            elapsed = time.perf_counter() - started
        except Exception as error:
            crashes.append(f"{document.document_id}: {type(error).__name__}")
            predictions.append(
                DocumentPrediction(
                    document.document_id, dict.fromkeys(HEADER_FIELDS), [], failed=True
                )
            )
            continue
        predictions.append(
            to_prediction(
                document.document_id, output.records, HEADER_FIELDS, fell_back=output.failed
            )
        )
        llm_seconds, load_seconds = llm_timing(output)
        live_seconds = sum((r.latency_seconds or 0) for r in output.responses if not r.cache_hit)
        rows.append(
            {
                "document_id": document.document_id,
                "failed": output.failed,
                "fallbacks": output.fallbacks,
                "retries": output.retries,
                "attempts": output.attempts,
                "withheld": output.withheld,
                "errors": output.errors,
                "truncated": sum(r.done_reason == "length" for r in output.responses),
                "ocr_seconds": entry["ocr_seconds"],
                "llm_seconds": llm_seconds,
                "load_seconds": load_seconds,
                "local_seconds": max(elapsed - live_seconds, 0.0),
                "values_output": sum(r.value_raw is not None for r in output.records),
                "values_not_found": sum(
                    r.evidence_status == "not_found"
                    and r.evidence_independent
                    and r.value_raw is not None
                    for r in output.records
                ),
                "rule_failures": sum(
                    not v.passed for r in output.records for v in r.validation_results
                ),
            }
        )
        if len(predictions) % 10 == 0:
            print(
                f"processed {len(predictions)}, failed={sum(p.failed for p in predictions)}",
                flush=True,
            )

    split_info = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))[arguments.split]
    if len(predictions) != split_info["n"]:
        sys.exit(f"expected {split_info['n']} documents, saw {len(predictions)}")

    PREDICTIONS.mkdir(parents=True, exist_ok=True)
    dump = json.dumps([asdict(p) for p in predictions], sort_keys=True, indent=0)
    prediction_path = PREDICTIONS / f"{name}_{arguments.split}.json"
    prediction_path.write_text(dump, encoding="utf-8", newline="\n")

    replayed = provider is not None and provider.live_calls == 0
    result = score(predictions, gold_headers, gold_rows, tuple(HEADER_FIELDS), tuple(ROW_FIELDS))
    result |= {
        "system": arguments.system,
        "dataset": "cord-v2",
        "split": arguments.split,
        "n_documents": len(predictions),
        "schema": SCHEMA,
        "schema_version": schema.version,
        "split_sha256": split_info["sha256"],
        "bootstrap": {"resamples": 2000, "seed": 20261106, "unit": "document"},
        "predictions_sha256": hashlib.sha256(dump.encode()).hexdigest(),
        "failures": {
            "crashes": len(crashes),
            "crash_detail": crashes,
            "failed_extractions": sum(p.failed for p in predictions),
            "documents_with_a_fallback": sum(row["fallbacks"] > 0 for row in rows),
            "pass_fallbacks": sum(row["fallbacks"] for row in rows),
            "retries": sum(row["retries"] for row in rows),
            "truncated_replies": sum(row["truncated"] for row in rows),
        },
        "verification": {
            "values_output": sum(row["values_output"] for row in rows),
            "values_not_found_in_document": sum(row["values_not_found"] for row in rows),
            "values_withheld": sum(row["withheld"] for row in rows),
            "rule_failures": sum(row["rule_failures"] for row in rows),
        },
        "latency_seconds": latency_report(rows, replayed=replayed),
        "memory": memory.report(),
        "workers": 1,
        "cost_per_document_usd": 0,
        "output_file": output_path.relative_to(ROOT).as_posix(),
        "environment": environment(),
    }
    if uses_llm:
        result["llm"] = {
            "model": arguments.model,
            "params": DEFAULT_PARAMS,
            "prompt_versions": PROMPT_VERSIONS,
            "mode": "replay" if arguments.replay else "record",
            "live_calls": provider.live_calls if provider else 0,
            "cache_hits": provider.hits if provider else 0,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", output_path)


if __name__ == "__main__":
    main()
