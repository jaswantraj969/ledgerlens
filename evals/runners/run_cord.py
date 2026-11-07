"""Evaluate one system on CORD under metrics 1.1. One worker, no parallel model calls.

Validation results go to evals/results/dev/. Reading the test split needs --final and refuses
to replace a result. If free RAM falls below 0.4 GiB the run stops, the abort is recorded in
evals/results/aborted/, and no results or predictions are written. Per-document predictions
are saved under data/ (gitignored), with their hash in the results file. A replay miss or
provider failure counts as a failed extraction.
"""

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from evals.datasets.cord import DEFAULT_RAW_DIR, HEADER_FIELDS, ROW_FIELDS, iter_documents
from evals.memory_guard import MemoryLog, abort_run
from evals.metrics import METRICS_VERSION
from evals.runners.run_cord_s1 import OCR_CACHE, SPLIT_FILE, cached_parse, environment
from evals.scoring import DocumentPrediction, score, to_prediction
from evals.systems import LLM_SYSTEMS, SystemOutput, build_system
from ledgerlens.confidence.features import build_features
from ledgerlens.extraction.llm import DEFAULT_PARAMS
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.schema import load_schema
from ledgerlens.verification.label_proximity import RULE_ID as LABEL_RULE

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
PREDICTIONS = ROOT / "data" / "cord-v2" / "predictions"
RECORDS = ROOT / "data" / "cord-v2" / "records"
CACHE_DIR = ROOT / "evals" / "cache" / "cord-v2"
SCHEMA = "cord_receipt"
DEFAULT_MODEL = "llama3.2:3b"
LOAD_THRESHOLD_SECONDS = 1.0
ABORTED = RESULTS / "aborted"


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


def latency_report(rows: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
    cold = [row for row in rows if row["load_seconds"] > LOAD_THRESHOLD_SECONDS]
    warm = [row for row in rows if row["load_seconds"] <= LOAD_THRESHOLD_SECONDS]
    return {
        "source": source,
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


def stop_if_low_memory(memory: MemoryLog, system: str, split: str, processed: int) -> None:
    """Abort before the next document, so a partial run never becomes a result."""
    if memory.abort_reason:
        details = {"system": system, "split": split, "documents_processed": processed}
        abort_run(
            memory,
            ABORTED,
            f"cord_{system.lower()}_{split}",
            details | {"environment": environment()},
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["S1", *LLM_SYSTEMS], required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--subset", type=Path, help="ID file; required for train")
    parser.add_argument("--final", action="store_true", help="required to read the test split")
    parser.add_argument("--replay", action="store_true", help="never call a model")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default="1.0", help="prompt version for passes A and B")
    parser.add_argument("--num-ctx", type=int, help="context length; default from DEFAULT_PARAMS")
    parser.add_argument("--label", help="reported system name, e.g. S2' for the round-2 prompt")
    parser.add_argument(
        "--save-records", action="store_true", help="also save per-field features (for S5)"
    )
    arguments = parser.parse_args()

    label = arguments.label or arguments.system
    name = label.lower().replace("'", "p")
    suffix = "v" + METRICS_VERSION.replace(".", "_")
    wanted: set[str] | None = None
    if arguments.split == "train":
        if arguments.subset is None:
            sys.exit("train is read only through a fixed subset file (--subset)")
        subset = json.loads(arguments.subset.read_text(encoding="utf-8"))
        wanted = set(subset["ids"])
        output_path = (
            RESULTS / "dev" / "prompt_round"
            / f"cord_{name}_{arguments.subset.stem}_p{arguments.prompt}_{suffix}.json"
        )  # fmt: skip
    elif arguments.split == "test":
        if not arguments.final:
            sys.exit("the test split needs --final: it is read once per configuration")
        output_path = RESULTS / f"cord_{name}_{suffix}.json"
        if output_path.exists():
            sys.exit(f"{output_path} exists: a new configuration needs a new version")
    else:
        output_path = RESULTS / "dev" / f"cord_{name}_validation_{suffix}.json"

    params = dict(DEFAULT_PARAMS)
    if arguments.num_ctx:
        params["num_ctx"] = arguments.num_ctx
    uses_llm = arguments.system in LLM_SYSTEMS
    live = OllamaProvider() if uses_llm and not arguments.replay else None
    provider = CachingProvider(ReplayCache(CACHE_DIR), live) if uses_llm else None
    system = build_system(arguments.system, provider, arguments.model, params, arguments.prompt)
    schema = load_schema(SCHEMA)
    ocr = RapidOcrParser()
    memory = MemoryLog()
    memory.start()

    predictions: list[DocumentPrediction] = []
    saved_records: dict[str, list[dict[str, Any]]] = {}
    gold_headers: dict[str, dict[str, str | None]] = {}
    gold_rows: dict[str, list[dict[str, str | None]]] = {}
    rows: list[dict[str, Any]] = []
    crashes: list[str] = []

    # OCR is cached for every CORD split; images are loaded only if some document lacks it.
    with_images = any(
        not (OCR_CACHE / f"{hashlib.sha256(d.encode()).hexdigest()}.json").exists()
        for d in (
            wanted or json.loads(SPLIT_FILE.read_text(encoding="utf-8"))[arguments.split]["ids"]
        )
    )
    for document in iter_documents(arguments.split, DEFAULT_RAW_DIR, with_images=with_images):
        if wanted is not None and document.document_id not in wanted:
            continue
        stop_if_low_memory(memory, label, arguments.split, len(predictions))
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
        if arguments.save_records:
            saved_records[document.document_id] = [
                {
                    "name": r.name,
                    "value_normalized": None if output.failed else r.value_normalized,
                    "value_present": r.value_raw is not None and not output.failed,
                    "source": r.source,
                    "decision": r.decision,
                    "risk_score": r.risk_score,
                    "features": build_features(r) | {"s4h_choice": r.signals.get("s4h_choice")},
                }
                for r in output.records
            ]
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
                    not v.passed
                    for r in output.records
                    for v in r.validation_results
                    if v.rule_id != LABEL_RULE
                ),
                "label_supported": sum(
                    r.signals.get("label_supported") is True for r in output.records
                ),
                "label_unsupported": sum(
                    r.signals.get("label_supported") is False for r in output.records
                ),
            }
        )
        if len(predictions) % 10 == 0:
            print(
                f"processed {len(predictions)}, failed={sum(p.failed for p in predictions)}",
                flush=True,
            )

    stop_if_low_memory(memory, label, arguments.split, len(predictions))
    if wanted is None:
        split_info = json.loads(SPLIT_FILE.read_text(encoding="utf-8"))[arguments.split]
    else:
        split_info = {"n": subset["n"], "sha256": subset["sha256"]}
    if len(predictions) != split_info["n"]:
        sys.exit(f"expected {split_info['n']} documents, saw {len(predictions)}")

    PREDICTIONS.mkdir(parents=True, exist_ok=True)
    dump = json.dumps([asdict(p) for p in predictions], sort_keys=True, indent=0)
    scope = arguments.split if wanted is None else f"{arguments.subset.stem}_p{arguments.prompt}"
    prediction_path = PREDICTIONS / f"{name}_{scope}.json"
    prediction_path.write_text(dump, encoding="utf-8", newline="\n")
    if arguments.save_records:
        records_path = RECORDS / f"{name}_{scope}.json"
        records_path.parent.mkdir(parents=True, exist_ok=True)
        records_path.write_text(json.dumps(saved_records), encoding="utf-8", newline="\n")

    replayed = provider is not None and provider.live_calls == 0
    if provider is None or provider.hits == 0:
        timing_source = "measured in this run"
    elif replayed:
        timing_source = "recorded when the call was first made"
    else:
        timing_source = (
            f"mixed: {provider.live_calls} calls measured in this run, {provider.hits} recorded "
            "earlier (an aborted run or an earlier system) and replayed"
        )
    result = score(predictions, gold_headers, gold_rows, tuple(HEADER_FIELDS), tuple(ROW_FIELDS))
    result |= {
        "system": label,
        "system_definition": arguments.system,
        "dataset": "cord-v2",
        "split": arguments.split
        if wanted is None
        else f"{arguments.split} ({arguments.subset.stem})",
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
            "label_supported": sum(row["label_supported"] for row in rows),
            "label_unsupported": sum(row["label_unsupported"] for row in rows),
        },
        "latency_seconds": latency_report(rows, source=timing_source),
        "memory": memory.report(),
        "workers": 1,
        "cost_per_document_usd": 0,
        "output_file": output_path.relative_to(ROOT).as_posix(),
        "environment": environment(),
    }
    if uses_llm:
        result["llm"] = {
            "model": arguments.model,
            "params": params,
            "prompt_versions": {"a": f"a-{arguments.prompt}", "b": f"b-{arguments.prompt}"},
            "mode": "replay" if arguments.replay else "record",
            "live_calls": provider.live_calls if provider else 0,
            "cache_hits": provider.hits if provider else 0,
        }
    if arguments.replay and output_path.exists():
        # Replay exercises no model, so the live run's memory figures stay the reported ones.
        previous = json.loads(output_path.read_text(encoding="utf-8"))
        recorded_live = previous.get("llm", {}).get("mode") == "record"
        live_memory = previous.get("memory_live_run") or (
            previous["memory"] if recorded_live else None
        )
        if live_memory:
            result["memory_live_run"] = live_memory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", output_path)


if __name__ == "__main__":
    main()
