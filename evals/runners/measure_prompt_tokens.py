"""Measure the longest CORD prompt in tokens, and the smallest num_ctx that holds it.

Pre-registered in docs/evaluation.md: all splits, input only (no labels are read). Prompts are
ranked by characters; the TOP longest per pass are sent to the model with num_predict=1 to get
the exact prompt token count, twice each, so a prompt-cache effect on the count would show.
num_ctx is the smallest multiple of 256 that holds the longest prompt plus num_predict.

    python -m evals.runners.measure_prompt_tokens --prompt 2.0
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any

import httpx

from evals.datasets.cord import DEFAULT_RAW_DIR, iter_documents
from evals.memory_guard import MemoryLog
from evals.runners.run_cord_s1 import OCR_CACHE, cached_parse, environment
from ledgerlens.extraction import prompts
from ledgerlens.extraction.llm import DEFAULT_PARAMS, SYSTEM_PROMPT, LlmExtractor, _output_model
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.parsing.ocr import RapidOcrParser
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "evals" / "results" / "dev" / "prompt_round"
TOP = 30
MEASURE_CTX = 4096  # holds every prompt measured; the count does not depend on it
STEP = 256


class _NoProvider:
    def complete(self, request: object) -> object:
        raise RuntimeError("not used")


def count_tokens(client: httpx.Client, model: str, system: str, prompt: str, fmt: Any) -> int:
    reply = client.post(
        "/api/chat",
        json={
            "model": model,
            "stream": False,
            "format": fmt,
            "options": {"temperature": 0, "num_predict": 1, "num_ctx": MEASURE_CTX},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
    )
    reply.raise_for_status()
    return int(reply.json()["prompt_eval_count"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default="llama3.2:3b")
    arguments = parser.parse_args()
    schema = load_schema("cord_receipt")
    system = SYSTEM_PROMPT if arguments.prompt == "1.0" else prompts.SYSTEM_PROMPT_2
    evidence = arguments.prompt in prompts.EVIDENCE_PROMPTS
    fmt = _output_model(schema, evidence).model_json_schema()
    ocr = RapidOcrParser()
    memory = MemoryLog()
    memory.start()

    lengths: dict[str, list[tuple[int, str, str]]] = {"a": [], "b": []}
    for split in ("train", "validation", "test"):
        for document in iter_documents(split, DEFAULT_RAW_DIR, with_images=False):
            # OCR is already cached for every split; no image is loaded.
            entry = cached_parse(document.document_id, b"", ocr, OCR_CACHE)
            parsed = ParsedDocument.model_validate(entry["parsed"])
            for mode in ("a", "b"):
                extractor = LlmExtractor(_NoProvider(), arguments.model, mode=mode,  # type: ignore[arg-type]
                                         prompt=arguments.prompt)  # fmt: skip
                text = extractor._build_prompt(parsed, schema)
                lengths[mode].append((len(system) + len(text), document.document_id, text))

    client = httpx.Client(base_url="http://127.0.0.1:11434", timeout=300)
    measured: dict[str, list[dict[str, Any]]] = {}
    for mode, rows in lengths.items():
        rows.sort(reverse=True)
        measured[mode] = []
        for characters, document_id, text in rows[:TOP]:
            if memory.abort_reason:
                raise SystemExit(f"ABORTED: {memory.abort_reason}")
            first = count_tokens(client, arguments.model, system, text, fmt)
            second = count_tokens(client, arguments.model, system, text, fmt)
            measured[mode].append(
                {"document_id": document_id, "characters": characters,
                 "tokens_first": first, "tokens_second": second}
            )  # fmt: skip
    longest = max(max(r["tokens_first"], r["tokens_second"]) for v in measured.values() for r in v)
    num_predict = int(DEFAULT_PARAMS["num_predict"])
    num_ctx = math.ceil((longest + num_predict) / STEP) * STEP
    result = {
        "prompt": arguments.prompt,
        "model": arguments.model,
        "documents_ranked": {mode: len(rows) for mode, rows in lengths.items()},
        "top_measured_per_pass": TOP,
        "measured": measured,
        "counts_stable_across_repeats": all(
            r["tokens_first"] == r["tokens_second"] for v in measured.values() for r in v
        ),
        "longest_prompt_tokens": longest,
        "num_predict": num_predict,
        "num_ctx": num_ctx,
        "rule": "smallest multiple of 256 >= longest prompt tokens + num_predict",
        "memory": memory.report(),
        "environment": environment(),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"prompt_tokens_p{arguments.prompt}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"longest {longest} tokens -> num_ctx {num_ctx}; wrote {path}")


if __name__ == "__main__":
    main()
