"""S1 or S2 on synthetic invoices, per layout, under the current metrics version. Reported apart
from real data. The output name carries the metrics version, so an older result is never
overwritten.

Two routes: native PDF text, and OCR on rendered pages. Development layouts and the held-out
layout are scored separately, and the gap between them is reported. Seeds are fixed in advance.
"""

import argparse
import json
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.atomic import write_text_atomic
from evals.memory_guard import MemoryLog
from evals.metrics import METRICS_VERSION
from evals.power import PowerLog
from evals.runners.run_cord_s1 import environment
from evals.scoring import DocumentPrediction, row_key, score, to_prediction
from evals.synthetic.generate import (
    DEV_LAYOUTS,
    HELD_OUT_LAYOUTS,
    RECEIPT_DESCRIPTION_CHARS,
    SyntheticInvoice,
    generate_invoice,
)
from evals.systems import SystemOutput, build_system
from ledgerlens.extraction.deterministic import normalized_value
from ledgerlens.extraction.llm import DEFAULT_PARAMS
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.parsing.pdfium import PdfiumParser
from ledgerlens.pipeline import process
from ledgerlens.schema import FieldType, load_schema

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "evals" / "results" / "synthetic_s1_v1_1.json"
CACHE_DIR = ROOT / "evals" / "cache" / "synthetic"
SEED_BASE = 700000
NATIVE_PER_LAYOUT = 40
OCR_PER_LAYOUT = 20
ROW_FIELDS = ("description", "quantity", "unit_price", "amount")
HEADER_TYPES: dict[str, FieldType] = {
    "vendor_name": "text",
    "invoice_number": "identifier",
    "invoice_date": "date",
    "currency": "currency",
    "subtotal": "amount",
    "tax_amount": "amount",
    "total_amount": "amount",
}
GAP_FIELDS = (*HEADER_TYPES, "line_items_row_level")


def header_key(name: str, value: str | None) -> str | None:
    return normalized_value(HEADER_TYPES[name], value)


def gold_rows(invoice: SyntheticInvoice) -> list[dict[str, str | None]]:
    """Rows as printed. The receipt layout prints no unit price and clips descriptions."""
    receipt = invoice.layout == "receipt"
    return [
        {
            "description": item.description[:RECEIPT_DESCRIPTION_CHARS].strip()
            if receipt
            else item.description,
            "quantity": str(item.quantity),
            "unit_price": None if receipt else str(item.unit_price),
            "amount": str(item.amount),
        }
        for item in invoice.items
    ]


def evaluate(
    layout: str, count: int, parser: Any, system: Callable[..., SystemOutput] | None = None,
    memory: MemoryLog | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Score one layout. With `system`, an LLM failure is a failed extraction, scored empty."""
    schema = load_schema("default")
    predictions: list[DocumentPrediction] = []
    failed = fallbacks = 0
    seconds: list[float] = []
    headers: dict[str, dict[str, str | None]] = {}
    rows: dict[str, list[dict[str, str | None]]] = {}
    for index in range(count):
        invoice = generate_invoice(SEED_BASE + index, layout=layout)
        headers[invoice.document_id] = {name: invoice.truth[name] for name in HEADER_TYPES}
        rows[invoice.document_id] = gold_rows(invoice)
        if memory is not None and memory.abort_reason:
            raise SystemExit(f"ABORTED in {layout} at {index}: {memory.abort_reason}. No results.")
        parsed = parser.parse(invoice.pdf)
        if system is None:
            records, fell_back = process(parsed, schema), False
        else:
            output = system(parsed, schema)
            records, fell_back = output.records, output.failed
            fallbacks += output.fallbacks
            seconds += [r.latency_seconds or 0.0 for r in output.responses if not r.cache_hit]
        failed += int(fell_back)
        predictions.append(
            to_prediction(invoice.document_id, records, tuple(HEADER_TYPES), fell_back=fell_back)
        )
    print(f"{layout}: {count} documents, {failed} failed", flush=True)
    result = score(predictions, headers, rows, tuple(HEADER_TYPES), ROW_FIELDS, header_key)
    result["failures"] = {"failed_extractions": failed, "pass_fallbacks": fallbacks}
    result["live_llm_seconds"] = seconds
    return result


def _pooled(layouts: dict[str, Any], names: tuple[str, ...], field: str) -> float | None:
    """F1 pooled from counts across layouts."""
    tp = fp = fn = 0
    for name in names:
        result = layouts[name]
        if field == "line_items_row_level":
            row = result[field]
            tp += row["rows_correct"]
            fp += row["rows_predicted"] - row["rows_correct"]
            fn += row["rows_gold"] - row["rows_correct"]
        else:
            row = result["fields"][field]
            tp, fp, fn = tp + row["tp"], fp + row["fp"], fn + row["fn"]
    return 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else None


def gaps(layouts: dict[str, Any]) -> dict[str, Any]:
    table = {}
    for field in GAP_FIELDS:
        dev = _pooled(layouts, DEV_LAYOUTS, field)
        held = _pooled(layouts, HELD_OUT_LAYOUTS, field)
        table[field] = {
            "dev_f1": dev,
            "held_out_f1": held,
            "gap": None if dev is None or held is None else dev - held,
        }
    return table


def run_route(
    parser: Any, count: int, system: Callable[..., SystemOutput] | None = None,
    memory: MemoryLog | None = None,
) -> dict[str, Any]:  # fmt: skip
    layouts = {
        name: evaluate(name, count, parser, system, memory)
        for name in (*DEV_LAYOUTS, *HELD_OUT_LAYOUTS)
    }
    return {"documents_per_layout": count, "layouts": layouts, "dev_vs_held_out": gaps(layouts)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="three native documents per layout")
    parser.add_argument("--system", choices=["S1", "S2"], default="S1")
    parser.add_argument("--label", help="reported name, e.g. S2'")
    parser.add_argument("--prompt", default="1.0")
    parser.add_argument("--num-ctx", type=int)
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--replay", action="store_true", help="never call a model")
    arguments = parser.parse_args()

    system = None
    llm: dict[str, Any] = {}
    provider = None
    if arguments.system == "S2":
        params = dict(DEFAULT_PARAMS)
        if arguments.num_ctx:
            params["num_ctx"] = arguments.num_ctx
        live = None if arguments.replay else OllamaProvider()
        provider = CachingProvider(ReplayCache(CACHE_DIR), live)
        system = build_system("S2", provider, arguments.model, params, arguments.prompt)
        llm = {"model": arguments.model, "params": params, "prompt": arguments.prompt}
    label = arguments.label or arguments.system
    memory = MemoryLog()
    memory.start()
    started = time.time()

    routes: dict[str, Any] = {}
    if arguments.smoke:
        routes["native_pdf"] = run_route(PdfiumParser(), 3, system, memory)
        output = ROOT / "evals" / "results" / "dev" / "synthetic_smoke.json"
    else:
        routes["native_pdf"] = run_route(PdfiumParser(), NATIVE_PER_LAYOUT, system, memory)
        routes["ocr"] = run_route(RapidOcrParser(), OCR_PER_LAYOUT, system, memory)
        name = label.lower().replace("'", "p")
        suffix = "v" + METRICS_VERSION.replace(".", "_")
        output = OUTPUT.with_name(f"synthetic_{name}_{suffix}.json")
        if output.exists():
            raise SystemExit(f"{output} exists: a new run needs a new metrics version")
    if provider is not None:
        llm |= {"live_calls": provider.live_calls, "cache_hits": provider.hits}
    result = {
        "system": label,
        "llm": llm or None,
        "memory": memory.report(),
        "dataset": "synthetic",
        "note": "Synthetic results are reported apart and are not real-dataset claims.",
        "dev_layouts": DEV_LAYOUTS,
        "held_out_layouts": HELD_OUT_LAYOUTS,
        "seed_base": SEED_BASE,
        "routes": routes,
        "environment": environment(),
        "power": PowerLog.load(refresh=True).summarize([started, time.time()])
        | {"method": "run window (start and end of this run)"},
    }
    write_text_atomic(output, json.dumps(result, indent=2, default=_plain) + "\n")
    print("wrote", output)


def _plain(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


__all__ = ["evaluate", "gaps", "gold_rows", "header_key", "row_key"]


if __name__ == "__main__":
    main()
