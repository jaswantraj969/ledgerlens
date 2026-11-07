"""Measure free RAM three ways: no model, model loaded and idle, and during one S4' document.

Samples every 0.5 s, recording psutil's `available` (what the abort guard uses) next to Windows
`FreePhysicalMemory` (what ad-hoc PowerShell checks read), plus the model runner's RSS. The
document is a CORD train document outside the prompt subset, called live with prompt 2.2, so
validation is not touched. Output: evals/results/dev/memory_measurement.json.
"""

import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import psutil

from evals.memory_guard import GIB, RUNNER_NAMES
from evals.runners.run_cord_s1 import OCR_CACHE, environment
from evals.systems import build_system
from ledgerlens.extraction.llm import DEFAULT_PARAMS
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[2]
MODEL = "llama3.2:3b"
OUTPUT = ROOT / "evals" / "results" / "dev" / "memory_measurement.json"


def windows_free_gib() -> float | None:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",  # noqa: S607
             "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
            capture_output=True, text=True, check=True, timeout=20,
        )  # fmt: skip
        return round(int(out.stdout.strip()) / 1024**2, 3)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def runner_rss() -> float:
    total = 0
    for process in psutil.process_iter(["name", "memory_info"]):
        name = (process.info.get("name") or "").lower()
        if process.info.get("memory_info") and any(r in name for r in RUNNER_NAMES):
            total = max(total, process.info["memory_info"].rss)
    return round(total / GIB, 3)


class Sampler(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.samples: list[tuple[float, float]] = []

    def run(self) -> None:
        while not self.stop.wait(0.5):
            self.samples.append((psutil.virtual_memory().available / GIB, runner_rss()))

    def summary(self) -> dict[str, Any]:
        self.stop.set()
        available = [s[0] for s in self.samples] or [psutil.virtual_memory().available / GIB]
        rss = [s[1] for s in self.samples] or [runner_rss()]
        return {
            "samples": len(self.samples),
            "psutil_available_min_gib": round(min(available), 3),
            "psutil_available_mean_gib": round(sum(available) / len(available), 3),
            "runner_rss_max_gib": round(max(rss), 3),
            "windows_free_physical_gib_after": windows_free_gib(),
        }


def phase(name: str, action: Any) -> dict[str, Any]:
    sampler = Sampler()
    sampler.start()
    started = time.perf_counter()
    action()
    result = sampler.summary() | {"phase": name, "seconds": round(time.perf_counter() - started, 1)}
    print(result, flush=True)
    return result


def main() -> None:
    splits = json.loads((ROOT / "evals/splits/cord_v2/ids.json").read_text(encoding="utf-8"))
    subset = set(json.loads((ROOT / "evals/splits/cord_v2/prompt_dev_train100.json")
                            .read_text(encoding="utf-8"))["ids"])  # fmt: skip
    document_id = next(d for d in sorted(splits["train"]["ids"]) if d not in subset)
    cache_file = OCR_CACHE / f"{hashlib.sha256(document_id.encode()).hexdigest()}.json"
    parsed = ParsedDocument.model_validate(json.loads(cache_file.read_text("utf-8"))["parsed"])
    schema = load_schema("cord_receipt")
    params = dict(DEFAULT_PARAMS) | {"num_ctx": 2304}
    scratch = ROOT / "data" / "memory-measurement-cache"
    provider = CachingProvider(ReplayCache(scratch), OllamaProvider())  # fresh: calls are live
    system = build_system("S4", provider, MODEL, params, "2.2")
    client = httpx.Client(base_url="http://127.0.0.1:11434", timeout=300)

    subprocess.run(["ollama", "stop", MODEL], capture_output=True, check=False)  # noqa: S603, S607
    time.sleep(5)
    phases = [phase("no model loaded, idle 10 s", lambda: time.sleep(10))]
    client.post("/api/generate", json={"model": MODEL, "keep_alive": "10m",
                                       "options": {"num_ctx": 2304}})  # fmt: skip
    phases.append(phase("model loaded, idle 20 s", lambda: time.sleep(20)))
    phases.append(phase("one live S4' document (passes A and B)",
                        lambda: system(parsed, schema)))  # fmt: skip
    phases.append(phase("model loaded, idle 10 s after", lambda: time.sleep(10)))
    result = {
        "document_id": document_id,
        "model": MODEL,
        "params": params,
        "live_calls": provider.live_calls,
        "total_ram_gib": round(psutil.virtual_memory().total / GIB, 3),
        "phases": phases,
        "environment": environment(),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUTPUT)


if __name__ == "__main__":
    main()
