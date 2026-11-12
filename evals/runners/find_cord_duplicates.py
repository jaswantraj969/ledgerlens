"""Find CORD v2 documents whose OCR output is identical across the official splits.

Two definitions, both reported: identical token text (the words the LLM prompt is built from,
in reading order), and identical full OCR output (text plus token positions and confidences).
For each cross-split pair involving test, it also reports whether the image bytes and the gold
labels are identical. Reads the OCR cache and the raw parquet files; changes nothing.

    python -m evals.runners.find_cord_duplicates
"""

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from evals.datasets.cord import DEFAULT_RAW_DIR, iter_documents
from evals.runners.run_cord import ocr_path

ROOT = Path(__file__).resolve().parents[2]
IDS = ROOT / "evals" / "splits" / "cord_v2" / "ids.json"


def _parsed(document_id: str) -> dict[str, Any]:
    return dict(json.loads(ocr_path(document_id).read_text(encoding="utf-8"))["parsed"])


def token_text(document_id: str) -> str:
    pages = _parsed(document_id)["pages"]
    return "\n".join(" ".join(token["text"] for token in page["tokens"]) for page in pages)


def full_output(document_id: str) -> str:
    return json.dumps(_parsed(document_id)["pages"], sort_keys=True)


def cross_split_groups(key: Callable[[str], str]) -> tuple[list[list[tuple[str, str]]], int]:
    splits = json.loads(IDS.read_text(encoding="utf-8"))
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for split in ("train", "validation", "test"):
        for document_id in splits[split]["ids"]:
            digest = hashlib.sha256(key(document_id).encode()).hexdigest()
            groups[digest].append((split, document_id))
    cross = [g for g in groups.values() if len({s for s, _ in g}) > 1]
    within = sum(1 for g in groups.values() if len(g) > 1 and len({s for s, _ in g}) == 1)
    return cross, within


def main() -> None:
    definitions = {"identical token text": token_text, "identical full OCR output": full_output}
    test_pairs: set[tuple[str, str]] = set()
    for name, key in definitions.items():
        cross, within = cross_split_groups(key)
        tests = sorted(d for g in cross for s, d in g if s == "test")
        print(f"{name}: {len(cross)} groups across splits, {within} within one split only; "
              f"test documents involved: {len(tests)}")  # fmt: skip
        for group in cross:
            print("  " + ", ".join(document for _, document in group))
            documents = [document for _, document in group]
            in_test = [d for d in documents if ":test:" in d]
            test_pairs |= {(other, t) for t in in_test for other in documents if other != t}
    wanted = {document for pair in test_pairs for document in pair}
    seen: dict[str, tuple[str, str]] = {}
    splits: tuple[Literal["train", "validation", "test"], ...] = ("train", "validation", "test")
    for split in splits:
        for document in iter_documents(split, DEFAULT_RAW_DIR, with_images=True):
            if document.document_id in wanted:
                gold = json.dumps([document.gold, document.gold_rows], sort_keys=True, default=str)
                seen[document.document_id] = (
                    hashlib.sha256(document.image or b"").hexdigest(),
                    gold,
                )
    print("pairs involving test:")
    for other, test in sorted(test_pairs, key=lambda pair: pair[1]):
        image = "identical" if seen[other][0] == seen[test][0] else "different"
        labels = "identical" if seen[other][1] == seen[test][1] else "different"
        print(f"  {other} / {test}: image bytes {image}, gold labels {labels}")


if __name__ == "__main__":
    main()
