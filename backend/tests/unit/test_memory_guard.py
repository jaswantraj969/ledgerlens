import json
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace

import pytest
from evals import memory_guard
from evals.memory_guard import GIB, MemoryLog, abort_run

VirtualMemory = namedtuple("VirtualMemory", "available total")


def fake_ram(monkeypatch: pytest.MonkeyPatch, available_gib: float) -> None:
    monkeypatch.setattr(
        memory_guard.psutil,
        "virtual_memory",
        lambda: VirtualMemory(int(available_gib * GIB), 16 * GIB),
    )


def fake_processes(monkeypatch: pytest.MonkeyPatch, entries: list[tuple[str, int]]) -> None:
    processes = [
        SimpleNamespace(info={"name": name, "memory_info": SimpleNamespace(rss=rss)})
        for name, rss in entries
    ]
    monkeypatch.setattr(memory_guard.psutil, "process_iter", lambda attrs: processes)


def test_a_report_taken_before_any_interval_has_real_numbers() -> None:
    """The cause of the 0.0 figures: the old sampler only sampled after the first interval."""
    log = MemoryLog(interval=3600)
    log.start()
    report = log.report()
    assert report["peak_process_rss_gib"] > 0
    assert report["lowest_available_system_ram_gib"] > 0


def test_a_never_started_log_still_reports_real_numbers() -> None:
    assert MemoryLog(interval=3600).report()["peak_process_rss_gib"] > 0


def test_model_runner_is_found_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_processes(monkeypatch, [("ollama.exe", 1 * GIB), ("llama-server.exe", 3 * GIB),
                                 ("code.exe", 9 * GIB)])  # fmt: skip
    assert MemoryLog(interval=3600).report()["peak_model_runner_rss_gib"] == 3.0


def test_enough_free_ram_sets_no_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ram(monkeypatch, 0.5)
    log = MemoryLog(interval=3600)
    log.sample()
    assert log.abort_reason is None


def test_low_free_ram_sets_an_abort_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ram(monkeypatch, 0.39)
    log = MemoryLog(interval=3600)
    assert log.abort_reason is not None
    assert "0.390 GiB fell below 0.400 GiB" in log.abort_reason


def test_abort_records_the_reason_and_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_ram(monkeypatch, 0.2)
    log = MemoryLog(interval=3600)
    with pytest.raises(SystemExit) as stopped:
        abort_run(log, tmp_path, "cord_s2_validation", {"documents_processed": 7})
    assert stopped.value.code == memory_guard.ABORT_EXIT_CODE
    (record_path,) = tmp_path.glob("cord_s2_validation_aborted_*.json")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["aborted"] is True
    assert record["documents_processed"] == 7
    assert "fell below" in record["reason"]
    assert record["memory"]["lowest_available_system_ram_gib"] == 0.2


def test_the_cord_runner_stops_before_the_next_document(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from evals.runners import run_cord

    monkeypatch.setattr(run_cord, "ABORTED", tmp_path)
    fake_ram(monkeypatch, 0.1)
    with pytest.raises(SystemExit):
        run_cord.stop_if_low_memory(MemoryLog(interval=3600), "S2", "validation", 41)
    (record_path,) = tmp_path.glob("cord_s2_validation_aborted_*.json")
    assert json.loads(record_path.read_text(encoding="utf-8"))["documents_processed"] == 41
