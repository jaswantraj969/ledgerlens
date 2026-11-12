"""Label every existing timed result with the power state its timings were recorded under.

For CORD results the run's configuration is replayed with no live calls: each document's OCR cache
entry, and every LLM reply the system asks for, gives one timing with a recording time (the cache
file's modification time). Synthetic and one-off runs, whose cache times were rewritten by a
commit hook or which used no cache, are labelled from their run log's START/END window.

Only metadata is added (a `power` block). No number in any results file changes.

    python -m evals.runners.audit_power
"""

import contextlib
import json
import re
from pathlib import Path
from typing import Any

from evals.datasets.cord import DEFAULT_RAW_DIR, iter_documents
from evals.power import PowerLog
from evals.runners.run_cord import CACHE_DIR, SCHEMA, ocr_path
from evals.systems import build_system
from ledgerlens.extraction.llm import DEFAULT_PARAMS
from ledgerlens.llm.base import LLMError
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
LOGS = ROOT / "docs" / "progress" / "logs"
SPLITS = ROOT / "evals" / "splits" / "cord_v2"
REPORT = LOGS / "power-audit.json"
# Results whose timings are not in the CORD caches, labelled by their run window instead.
WINDOW_RUNS = {
    "synthetic_s2p_v1_1_1.json": "run-synthetic-s2p.log",
    "dev/memory_measurement.json": "run-memory-measurement.log",
    "dev/llm_smoke_llama3.2-3b.json": "run-llm-smoke.log",
}


def _scope(result: dict[str, Any]) -> tuple[str, set[str] | None]:
    split = str(result["split"])
    match = re.match(r"(\w+) \((\w+)\)", split)
    if not match:
        return split, None
    subset = json.loads((SPLITS / f"{match[2]}.json").read_text(encoding="utf-8"))
    return match[1], set(subset["ids"])


def cord_paths(result: dict[str, Any]) -> list[Path]:
    """Cache files holding this result's timings: OCR per document, plus every LLM reply."""
    split, wanted = _scope(result)
    perturbation = (result.get("perturbation") or {}).get("name")
    llm = result.get("llm")
    system = None
    provider = None
    if llm:
        params = dict(DEFAULT_PARAMS) | dict(llm.get("params") or {})
        prompt = str(llm.get("prompt_versions", {}).get("a", "a-1.0")).split("-", 1)[1]
        provider = CachingProvider(ReplayCache(CACHE_DIR))
        definition = result.get("system_definition") or result["system"]
        system = build_system(definition, provider, llm["model"], params, prompt)
    schema = load_schema(SCHEMA)
    paths = []
    for document in iter_documents(split, DEFAULT_RAW_DIR, with_images=False):  # type: ignore[arg-type]
        if wanted is not None and document.document_id not in wanted:
            continue
        ocr = ocr_path(document.document_id, perturbation)
        paths.append(ocr)
        if system is not None and ocr.exists():
            parsed = ParsedDocument.model_validate(json.loads(ocr.read_text("utf-8"))["parsed"])
            # A replay miss means that reply was never recorded, so it has no timing.
            with contextlib.suppress(LLMError):
                system(parsed, schema)
    if provider is not None:
        paths += [provider.cache.path_for(key) for key in provider.keys_used]
    return [path for path in paths if path.exists()]


def window(log_name: str) -> list[float]:
    text = (LOGS / log_name).read_text(encoding="utf-8", errors="replace")
    stamps = re.findall(r"^(?:START|END) (\S+)", text, flags=re.M)
    from evals.power import _ts

    return [_ts(stamp) for stamp in stamps]


def timed_results() -> list[Path]:
    paths = []
    for path in sorted(RESULTS.rglob("*.json")):
        relative = path.relative_to(RESULTS).as_posix()
        if relative.startswith(("aborted/", "repro/")) and not relative.startswith("repro/cord"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and ("latency_seconds" in data or relative in WINDOW_RUNS):
            paths.append(path)
    return paths


def main() -> None:
    log = PowerLog.load(refresh=True, snapshot=True)  # the explicit audit updates the snapshot
    report = {}
    for path in timed_results():
        relative = path.relative_to(RESULTS).as_posix()
        data = json.loads(path.read_text(encoding="utf-8"))
        if relative in WINDOW_RUNS:
            stamps = window(WINDOW_RUNS[relative])
            power = log.summarize(stamps) | {"method": f"run window from {WINDOW_RUNS[relative]}"}
        elif "split" in data and str(data.get("dataset", "cord-v2")).startswith("cord"):
            stamps = [p.stat().st_mtime for p in cord_paths(data)]
            power = log.summarize(stamps) | {
                "method": "cache file modification time per recorded timing (audit replay)"
            }
        else:
            continue
        data["power"] = power
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        report[relative] = power
        counts = (power["timings_ac"], power["timings_battery"], power["timings_unknown"])
        print(f"{power['label']:17} {relative}  ac/battery/unknown={counts}", flush=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", REPORT)


if __name__ == "__main__":
    main()
