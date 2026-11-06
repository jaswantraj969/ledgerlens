"""Print S1 errors on the CORD validation split. Refuses every other split by construction."""

import collections
import json
import sys

from evals import normalization
from evals.datasets.cord import HEADER_FIELDS, iter_documents
from evals.runners.run_cord_s1 import OCR_CACHE, SCHEMA, compare, predictions
from ledgerlens.extraction.layout import build_lines
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.pipeline import process
from ledgerlens.schema import load_schema
import hashlib


def main() -> None:
    show = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    schema = load_schema(SCHEMA)
    kinds: collections.Counter[str] = collections.Counter()
    shown = 0
    for document in iter_documents("validation", with_images=False):
        path = OCR_CACHE / f"{hashlib.sha256(document.document_id.encode()).hexdigest()}.json"
        parsed = ParsedDocument.model_validate(json.loads(path.read_text("utf-8"))["parsed"])
        lines = build_lines(parsed)
        text = [line.text for line in lines]
        predicted = predictions(process(parsed, schema))
        problem = False
        for field in HEADER_FIELDS:
            gold = document.gold[field]
            outcome, _ = compare(field, predicted[field], gold)
            if outcome.fp or outcome.fn:
                problem = True
                in_ocr = gold is not None and any(
                    normalization.money(token.text) == normalization.money(gold)
                    for line in lines
                    for token in line.tokens
                )
                kind = "gold_absent" if gold is None else ("missed" if predicted[field] is None else "wrong")
                kinds[f"{field}:{kind}:gold_token_in_ocr={in_ocr}"] += 1
        if problem and shown < show:
            shown += 1
            print("=====", document.document_id, {f: document.gold[f] for f in HEADER_FIELDS})
            print("pred", {f: predicted[f] for f in HEADER_FIELDS})
            print("\n".join(text[-14:]))
    print()
    for key, count in sorted(kinds.items()):
        print(count, key)


if __name__ == "__main__":
    main()
