"""SROIE adapter and vendor-grouped split. Research-only: see LICENSES.md.

Evaluable fields come from the key files: vendor_name (company), invoice_date (date) and
total_amount (total). The address has no field in the default schema, and SROIE labels
neither subtotal, tax, line items, invoice number nor currency.

Group output holds document IDs and group numbers only. Company names must never leave
data/, so `split_payload` is the single place that builds what gets committed.
"""

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from ledgerlens.verification.normalize import normalize_text

DEFAULT_KEY_DIR = Path(__file__).resolve().parents[2] / "data" / "sroie" / "key"
EVALUABLE_FIELDS = ("vendor_name", "invoice_date", "total_amount")
SPLIT_SEED = 20261106
SPLIT_SHARES = {"train": 0.6, "calibration": 0.2, "test": 0.2}
VENDOR_MATCH_THRESHOLD = 92.0
_LEGAL_SUFFIX = re.compile(r"\b(sdn\.?\s*bhd\.?|s/b|bhd\.?|enterprise|trading|plt)\b")
_NOT_NAME = re.compile(r"[^\w\s]")


@dataclass(frozen=True)
class SroieDocument:
    document_id: str
    company: str
    date: str | None
    total: str | None


def load_documents(key_dir: Path = DEFAULT_KEY_DIR) -> list[SroieDocument]:
    documents = []
    for path in sorted(key_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        documents.append(
            SroieDocument(
                document_id=f"sroie:{path.stem}",
                company=record["company"],
                date=record.get("date"),
                total=record.get("total"),
            )
        )
    return documents


def vendor_key(company: str) -> str:
    """Name with case, punctuation and legal suffixes removed."""
    text = _LEGAL_SUFFIX.sub(" ", normalize_text(company))
    return " ".join(_NOT_NAME.sub(" ", text).split())


def vendor_groups(documents: list[SroieDocument]) -> dict[str, int]:
    """Assign group numbers. Near-identical vendor keys merge; sorted order keeps it stable."""
    representatives: list[str] = []
    key_group: dict[str, int] = {}
    for key in sorted({vendor_key(document.company) for document in documents}):
        for group, representative in enumerate(representatives):
            if fuzz.ratio(key, representative) >= VENDOR_MATCH_THRESHOLD:
                key_group[key] = group
                break
        else:
            key_group[key] = len(representatives)
            representatives.append(key)
    return {d.document_id: key_group[vendor_key(d.company)] for d in documents}


def split_groups(groups: dict[str, int], seed: int = SPLIT_SEED) -> dict[str, str]:
    """Assign whole vendors to splits, so no vendor appears in two of them."""
    sizes: dict[int, int] = {}
    for group in groups.values():
        sizes[group] = sizes.get(group, 0) + 1
    order = sorted(sizes)
    random.Random(seed).shuffle(order)  # noqa: S311 - reproducible split, not security

    targets = {name: share * len(groups) for name, share in SPLIT_SHARES.items()}
    filled = dict.fromkeys(SPLIT_SHARES, 0)
    assigned: dict[int, str] = {}
    # Largest vendors first, so one dominant vendor cannot overfill a small split.
    for group in sorted(order, key=lambda g: sizes[g], reverse=True):
        split = max(filled, key=lambda name: targets[name] - filled[name])
        assigned[group] = split
        filled[split] += sizes[group]
    return {document_id: assigned[group] for document_id, group in groups.items()}


def split_payload(documents: list[SroieDocument]) -> dict[str, Any]:
    """Build the committed split file: IDs and group numbers only."""
    groups = vendor_groups(documents)
    splits = split_groups(groups)
    return {
        "method": "normalised company, fuzzy merge, whole vendors assigned to splits",
        "seed": SPLIT_SEED,
        "shares": SPLIT_SHARES,
        "vendor_match_threshold": VENDOR_MATCH_THRESHOLD,
        "documents": {
            document_id: {"split": splits[document_id], "vendor_group": groups[document_id]}
            for document_id in sorted(groups)
        },
    }
