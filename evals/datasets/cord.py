"""CORD v2 adapter. Maps dataset labels to LedgerLens fields and declares what is evaluable."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pyarrow.parquet as pq

Split = Literal["train", "validation", "test"]

DEFAULT_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "cord-v2" / "raw"
HEADER_FIELDS = {
    "total_amount": ("total", "total_price"),
    "subtotal": ("sub_total", "subtotal_price"),
    "tax_amount": ("sub_total", "tax_price"),
}
LINE_ITEM_FIELDS = {
    "line_items.amount": "price",
    "line_items.description": "nm",
    "line_items.quantity": "cnt",
    "line_items.unit_price": "unitprice",
}
EVALUABLE_FIELDS = (*HEADER_FIELDS, *LINE_ITEM_FIELDS)
ROW_FIELDS = {"description": "nm", "quantity": "cnt", "unit_price": "unitprice", "amount": "price"}
_ABSENT = {"", "-"}


@dataclass(frozen=True)
class CordDocument:
    document_id: str
    split: Split
    image: bytes | None
    gold: dict[str, Any]
    gold_rows: list[dict[str, str | None]]
    word_boxes: list[tuple[float, float]]
    width: int
    height: int


def _rows(node: Any) -> list[dict[str, Any]]:
    rows = node if isinstance(node, list) else [node]
    return [row for row in rows if isinstance(row, dict)]


def _values(row: dict[str, Any], key: str) -> list[str]:
    value = row.get(key)
    values = value if isinstance(value, list) else [value]
    return [str(v).strip() for v in values if v is not None and str(v).strip() not in _ABSENT]


def map_gold(parse: dict[str, Any]) -> dict[str, Any]:
    """Header fields map to one string or None; line-item fields map to lists."""
    gold: dict[str, Any] = {}
    for name, (section, key) in HEADER_FIELDS.items():
        values = [value for row in _rows(parse.get(section)) for value in _values(row, key)]
        gold[name] = values[-1] if values else None
    for name, key in LINE_ITEM_FIELDS.items():
        gold[name] = [value for row in _rows(parse.get("menu")) for value in _values(row, key)]
    return gold


def map_gold_rows(parse: dict[str, Any]) -> list[dict[str, str | None]]:
    """Menu rows with cells kept together. A list-valued cell uses its last value."""
    rows = []
    for row in _rows(parse.get("menu")):
        cells: dict[str, str | None] = {}
        for name, key in ROW_FIELDS.items():
            values = _values(row, key)
            cells[name] = values[-1] if values else None
        if any(cells.values()):
            rows.append(cells)
    return rows


def _word_centers(lines: list[dict[str, Any]]) -> list[tuple[float, float]]:
    centers = []
    for line in lines:
        for word in line.get("words", []):
            quad = word["quad"]
            centers.append(
                (
                    (quad["x1"] + quad["x2"] + quad["x3"] + quad["x4"]) / 4,
                    (quad["y1"] + quad["y2"] + quad["y3"] + quad["y4"]) / 4,
                )
            )
    return centers


def iter_documents(
    split: Split, raw_dir: Path = DEFAULT_RAW_DIR, *, with_images: bool = True
) -> Iterator[CordDocument]:
    columns = ["image", "ground_truth"] if with_images else ["ground_truth"]
    for path in sorted(raw_dir.glob(f"{split}-*.parquet")):
        for batch in pq.ParquetFile(path).iter_batches(batch_size=16, columns=columns):
            images = batch.column("image").to_pylist() if with_images else None
            for index, raw in enumerate(batch.column("ground_truth").to_pylist()):
                record = json.loads(raw)
                meta = record["meta"]
                size = meta["image_size"]
                yield CordDocument(
                    document_id=f"cord-v2:{split}:{meta['image_id']}",
                    split=split,
                    image=images[index]["bytes"] if images is not None else None,
                    gold=map_gold(record["gt_parse"]),
                    gold_rows=map_gold_rows(record["gt_parse"]),
                    word_boxes=_word_centers(record.get("valid_line", [])),
                    width=size["width"],
                    height=size["height"],
                )
