"""Memory sampling for evaluation runs, with an abort when free system RAM runs low.

The sampler records this process, the model runner and free system RAM. It samples once when
created, on every interval, and once more when the report is taken, so a run that ends before
the first interval still reports real numbers (the bug behind the 0.0 figures in
evals/results/cord_s1_v1_1.json was a report taken with no sample at all).

When free RAM falls below `abort_below_gib`, `abort_reason` is set. Runners check it after each
document and stop through `abort_run`, which records the abort and writes no results.
"""

import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

GIB = 1024**3
ABORT_BELOW_GIB = 0.4
RUNNER_NAMES = ("llama-server", "ollama")
ABORT_EXIT_CODE = 3


class MemoryLog(threading.Thread):
    def __init__(self, interval: float = 2.0, abort_below_gib: float = ABORT_BELOW_GIB) -> None:
        super().__init__(daemon=True)
        self.interval = interval
        self.abort_below = abort_below_gib * GIB
        self.stop_event = threading.Event()
        self.peak_process = 0
        self.peak_runner = 0
        self.lowest_available = psutil.virtual_memory().available
        self.abort_reason: str | None = None
        self.sample()

    def sample(self) -> None:
        self.peak_process = max(self.peak_process, psutil.Process().memory_info().rss)
        available = psutil.virtual_memory().available
        self.lowest_available = min(self.lowest_available, available)
        if available < self.abort_below and self.abort_reason is None:
            self.abort_reason = (
                f"free system RAM {available / GIB:.3f} GiB fell below "
                f"{self.abort_below / GIB:.3f} GiB"
            )
        for process in psutil.process_iter(["name", "memory_info"]):
            name = (process.info.get("name") or "").lower()
            memory = process.info.get("memory_info")
            if memory is not None and any(runner in name for runner in RUNNER_NAMES):
                self.peak_runner = max(self.peak_runner, memory.rss)

    def run(self) -> None:
        while not self.stop_event.wait(self.interval):
            self.sample()

    def report(self) -> dict[str, float | int]:
        self.stop_event.set()
        self.sample()
        return {
            "peak_process_rss_gib": round(self.peak_process / GIB, 3),
            "peak_model_runner_rss_gib": round(self.peak_runner / GIB, 3),
            "lowest_available_system_ram_gib": round(self.lowest_available / GIB, 3),
            "total_system_ram_gib": round(psutil.virtual_memory().total / GIB, 3),
            "abort_below_gib": round(self.abort_below / GIB, 3),
        }


def abort_run(memory: MemoryLog, directory: Path, name: str, details: dict[str, Any]) -> None:
    """Record why a run stopped, then exit non-zero. No results or predictions are written."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{name}_aborted_{stamp}.json"
    record = {"aborted": True, "reason": memory.abort_reason, "memory": memory.report()} | details
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"ABORTED: {memory.abort_reason}. Recorded in {path}. No results written.", flush=True)
    sys.exit(ABORT_EXIT_CODE)
