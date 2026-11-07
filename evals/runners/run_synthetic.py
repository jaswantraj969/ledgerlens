"""S1 on synthetic invoices, per layout, under metrics 1.1. Reported apart from real data.

Two routes: native PDF text, and OCR on rendered pages. Development layouts and the held-out
layout are scored separately, and the gap between them is reported. Seeds are fixed in advance.
"""

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from evals.runners.run_cord_s1 import environment
from evals.scoring import DocumentPrediction, row_key, score, to_prediction
from evals.synthetic.generate import (
    DEV_LAYOUTS,
    HELD_OUT_LAYOUTS,
    RECEIPT_DESCRIPTION_CHARS,
    SyntheticInvoice,
    generate_invoice,
)
from ledgerlens.extraction.deterministic import normalized_value
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.parsing.pdfium import PdfiumParser
from ledgerlens.pipeline import process
from ledgerlens.schema import FieldType, load_schema

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "evals" / "results" / "synthetic_s1_v1_1.json"
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


def evaluate(layout: str, count: int, parser: Any) -> dict[str, Any]:
    schema = load_schema("default")
    predictions: list[DocumentPrediction] = []
    headers: dict[str, dict[str, str | None]] = {}
    rows: dict[str, list[dict[str, str | None]]] = {}
    for index in range(count):
        invoice = generate_invoice(SEED_BASE + index, layout=layout)
        headers[invoice.document_id] = {name: invoice.truth[name] for name in HEADER_TYPES}
        rows[invoice.document_id] = gold_rows(invoice)
        records = process(parser.parse(invoice.pdf), schema)
        predictions.append(to_prediction(invoice.document_id, records, tuple(HEADER_TYPES)))
    print(f"{layout}: {count} documents", flush=True)
    return score(predictions, headers, rows, tuple(HEADER_TYPES), ROW_FIELDS, header_key)


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


def run_route(parser: Any, count: int) -> dict[str, Any]:
    layouts = {name: evaluate(name, count, parser) for name in (*DEV_LAYOUTS, *HELD_OUT_LAYOUTS)}
    return {"documents_per_layout": count, "layouts": layouts, "dev_vs_held_out": gaps(layouts)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="three native documents per layout")
    arguments = parser.parse_args()

    routes: dict[str, Any] = {}
    if arguments.smoke:
        routes["native_pdf"] = run_route(PdfiumParser(), 3)
        output = ROOT / "evals" / "results" / "dev" / "synthetic_smoke.json"
    else:
        routes["native_pdf"] = run_route(PdfiumParser(), NATIVE_PER_LAYOUT)
        routes["ocr"] = run_route(RapidOcrParser(), OCR_PER_LAYOUT)
        output = OUTPUT
    result = {
        "system": "S1",
        "dataset": "synthetic",
        "note": "Synthetic results are reported apart and are not real-dataset claims.",
        "dev_layouts": DEV_LAYOUTS,
        "held_out_layouts": HELD_OUT_LAYOUTS,
        "seed_base": SEED_BASE,
        "routes": routes,
        "environment": environment(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, default=_plain) + "\n", encoding="utf-8", newline="\n"
    )
    print("wrote", output)


def _plain(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


__all__ = ["evaluate", "gaps", "gold_rows", "header_key", "row_key"]


if __name__ == "__main__":
    main()
