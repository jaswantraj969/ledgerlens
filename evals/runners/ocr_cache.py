"""Fill the OCR cache for one CORD split. Reads images only; no label is used.

python -m evals.runners.ocr_cache --split train
"""

import argparse

from evals.datasets.cord import DEFAULT_RAW_DIR, iter_documents
from evals.memory_guard import MemoryLog
from evals.runners.run_cord_s1 import OCR_CACHE, cached_parse
from ledgerlens.parsing.ocr import RapidOcrParser


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    arguments = parser.parse_args()
    ocr = RapidOcrParser()
    memory = MemoryLog()
    memory.start()
    count = 0
    for document in iter_documents(arguments.split, DEFAULT_RAW_DIR):
        if memory.abort_reason:
            raise SystemExit(f"ABORTED after {count} documents: {memory.abort_reason}")
        cached_parse(document.document_id, document.image or b"", ocr, OCR_CACHE)
        count += 1
        if count % 50 == 0:
            print(f"cached {count}", flush=True)
    print(f"done: {count} documents; memory {memory.report()}", flush=True)


if __name__ == "__main__":
    main()
