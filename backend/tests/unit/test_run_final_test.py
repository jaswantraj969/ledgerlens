import subprocess
from pathlib import Path
from typing import Any

import pytest
from evals.runners import run_final_test as final


def good_facts() -> dict[str, Any]:
    return {
        "git_dirty_files": [],
        "protocol_commit_is_ancestor": True,
        "boot_age_minutes": 5.0,
        "ac_online": True,
        "docker_daemon_running": False,
        "docker_processes": [],
        "free_ram_gib": 3.1,
        "ollama_version": "0.40.15",
        "model_digest": final.MODEL_DIGEST,
        "ollama_max_loaded_models": "1",
    }


def test_steps_follow_the_protocol_order_and_flags() -> None:
    steps = final.protocol_steps()
    names = [step.name for step in steps]
    assert names[:5] == ["S1 records rerun", "S2'", "S3'", "S4'", "S4h"]
    assert names[5:10] == ["S5-S1 all", "S5-S1 grouped", "S5-S4h all", "S5-S4h grouped",
                           "S5 ablations"]  # fmt: skip
    assert names[10:] == [f"{s} {p}" for p in final.PERTURBATIONS for s in ("S1", "S4h")]
    for step in steps:
        if step.module_args[0] == "evals.runners.run_cord":
            assert step.module_args[1:4] == ["--split", "test", "--final"]
    assert "--records-rerun" in steps[0].module_args
    assert {"--save-records"} <= set(steps[0].module_args) & set(steps[4].module_args)
    assert len({step.output for step in steps}) == len(steps)


def test_every_primed_step_uses_prompt_2_2_and_num_ctx_2304() -> None:
    for step in final.protocol_steps():
        if step.module_args[0] == "evals.runners.run_cord" and "--label" in step.module_args:
            args = step.module_args
            assert args[args.index("--prompt") + 1] == "2.2"
            assert args[args.index("--num-ctx") + 1] == "2304"


def test_preflight_passes_only_when_every_check_passes() -> None:
    assert all(passed for _, passed, _ in final.judge(good_facts()))


@pytest.mark.parametrize(
    ("key", "value", "check"),
    [
        ("git_dirty_files", ["?? x"], "clean commit"),
        ("boot_age_minutes", 61.0, "fresh reboot"),
        ("ac_online", None, "AC power"),
        ("ac_online", False, "AC power"),
        ("docker_daemon_running", True, "Docker stopped"),
        ("docker_processes", ["com.docker.backend.exe"], "Docker stopped"),
        ("free_ram_gib", 1.999, "free RAM"),
        ("model_digest", "other", "Ollama and model"),
        ("ollama_max_loaded_models", None, "OLLAMA_MAX_LOADED_MODELS=1"),
    ],
)
def test_each_failed_check_is_reported(key: str, value: Any, check: str) -> None:
    facts = good_facts() | {key: value}
    failed = [name for name, passed, _ in final.judge(facts) if not passed]
    assert failed == [check]


class FakeRun:
    """Plays a list of (exit code, abort record names) outcomes for successive attempts."""

    def __init__(self, aborted: Path, outcomes: list[tuple[int, list[str]]]) -> None:
        self.aborted, self.outcomes, self.calls = aborted, outcomes, 0

    def __call__(self, command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        code, records = self.outcomes[self.calls]
        self.calls += 1
        for name in records:
            (self.aborted / name).write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, code, "", "")


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    aborted = tmp_path / "aborted"
    aborted.mkdir()
    monkeypatch.setattr(final, "ABORTED", aborted)
    monkeypatch.setattr(final, "ROOT", tmp_path)
    monkeypatch.setattr(final, "RETRY_PAUSE_SECONDS", 0)
    monkeypatch.setattr(final, "_run", lambda *a, **k: None)
    return aborted


def _step() -> final.Step:
    return final.Step("S4h", ["evals.runners.run_cord"], "out.json")


def test_memory_aborts_are_retried_with_the_same_command_and_recorded(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = FakeRun(sandbox, [(3, ["a1.json"]), (3, ["a2.json"]), (0, [])])
    monkeypatch.setattr(final.subprocess, "run", fake)
    step = _step()
    with (tmp_path / "log.txt").open("a") as log_file:
        assert final.run_step(step, log_file, lambda _: None) == "done"
    assert [a["abort_records"] for a in step.attempts] == [["a1.json"], ["a2.json"], []]
    assert fake.calls == 3


def test_power_loss_stops_instead_of_retrying(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = FakeRun(sandbox, [(3, ["cord_s4h_test_on_battery_x.json"])])
    monkeypatch.setattr(final.subprocess, "run", fake)
    step = _step()
    with (tmp_path / "log.txt").open("a") as log_file:
        assert final.run_step(step, log_file, lambda _: None) == "power"
    assert fake.calls == 1


def test_other_failures_stop_and_existing_outputs_are_skipped(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(final.subprocess, "run", FakeRun(sandbox, [(1, [])]))
    with (tmp_path / "log.txt").open("a") as log_file:
        assert final.run_step(_step(), log_file, lambda _: None) == "failed"
        (tmp_path / "out.json").write_text("{}", encoding="utf-8")
        assert final.run_step(_step(), log_file, lambda _: None) == "skipped"


def test_exit_3_without_an_abort_record_is_not_treated_as_a_memory_abort(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(final.subprocess, "run", FakeRun(sandbox, [(3, [])]))
    with (tmp_path / "log.txt").open("a") as log_file:
        assert final.run_step(_step(), log_file, lambda _: None) == "failed"
