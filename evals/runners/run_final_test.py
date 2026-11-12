"""Run docs/evaluation/final-test-protocol.md end to end, unattended, from a clean commit.

    python -m evals.runners.run_final_test [--check-only]

Order:
1. Pre-flight: a clean commit, reboot age, AC power, Docker stopped, free RAM, Ollama and the
   model digest, and keep-awake on. Any failure stops the run before test is touched (exit 10).
2. Warm the model.
3. Every protocol step, in order. A memory abort (exit 3, with an abort record that is not a
   power abort) is retried with the same command and settings, resuming from the caches. Any other
   failure stops the run (exit 11). The one pre-registered exception: if the S1 records rerun does
   not reproduce the recorded predictions, S5-S1 is "not evaluated" and its steps are skipped.
4. Keep-awake is released, a summary is printed, and the metadata is saved.

A step whose output file already exists is skipped, so after an interruption the same command
resumes where it stopped. This script runs the existing runners only; it changes no code, config,
prompt, threshold or result file of its own accord, and it writes no README text.

--check-only runs the pre-flight (including starting and releasing keep-awake), checks that each
runner accepts the flags the protocol uses, and lists the steps. It does not warm the model and
never reads test.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
FINAL = RESULTS / "final"
LOGS = ROOT / "docs" / "progress" / "logs"
ABORTED = RESULTS / "aborted"
PROTOCOL = "docs/evaluation/final-test-protocol.md"
PROTOCOL_COMMIT = "2550b14"
MODEL = "llama3.2:3b"
MODEL_DIGEST = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
NUM_CTX = 2304
OLLAMA = "http://127.0.0.1:11434"
MIN_FREE_RAM_GIB = 2.0
MAX_BOOT_AGE_MINUTES = 60
MAX_ATTEMPTS = 20
RETRY_PAUSE_SECONDS = 30
KEEP_AWAKE_MINUTES = 600
ABORT_EXIT = 3
PREFLIGHT_FAILED, STEP_FAILED = 10, 11
DOCKER_PROCESSES = ("docker desktop.exe", "com.docker.backend.exe", "com.docker.build.exe")
PERTURBATIONS = ("blur-1.5", "blur-3.0", "jpeg-30", "jpeg-10")
TEST = ["evals.runners.run_cord", "--split", "test", "--final"]
PRIMED = ["--prompt", "2.2", "--num-ctx", str(NUM_CTX)]


@dataclass
class Step:
    name: str
    module_args: list[str]
    output: str  # repository-relative; the step is done when this exists
    attempts: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"


def protocol_steps() -> list[Step]:
    """The protocol's steps 1 to 8, in order, with the exact flags it fixes."""
    steps = [
        Step("S1 records rerun", [*TEST, "--system", "S1", "--records-rerun", "--save-records"],
             "evals/results/repro/cord_s1_test_records_rerun_v1_1_1.json"),
        Step("S2'", [*TEST, "--system", "S2", "--label", "S2'", *PRIMED],
             "evals/results/cord_s2p_v1_1_1.json"),
        Step("S3'", [*TEST, "--system", "S3", "--label", "S3'", *PRIMED],
             "evals/results/cord_s3p_v1_1_1.json"),
        Step("S4'", [*TEST, "--system", "S4", "--label", "S4'", *PRIMED],
             "evals/results/cord_s4p_v1_1_1.json"),
        Step("S4h", [*TEST, "--system", "S4h", "--label", "S4h", *PRIMED, "--save-records"],
             "evals/results/cord_s4h_v1_1_1.json"),
    ]  # fmt: skip
    for base, scope in (("s1", "train_all_p1.0"), ("s4h", "train_all_p2.2")):
        label = "S5-S1" if base == "s1" else "S5-S4h"
        for variant, suffix in (("all", ""), ("grouped", "_grouped")):
            command = ["evals.runners.run_s5", "--base", base, "--train-scope", scope]
            command += ["--variant", variant, "--final"]
            output = f"evals/results/cord_s5_{base}{suffix}_v1_1_1.json"
            steps.append(Step(f"{label} {variant}", command, output))
    ablations = ["evals.runners.run_s5_ablations", "--final"]
    steps.append(Step("S5 ablations", ablations, "evals/results/cord_s5_ablations_v1_1_1.json"))
    degraded = "evals/results/degradation"
    for perturbation in PERTURBATIONS:
        s1 = [*TEST, "--system", "S1", "--perturb", perturbation]
        output = f"{degraded}/cord_s1_{perturbation}_v1_1_1.json"
        steps.append(Step(f"S1 {perturbation}", s1, output))
        s4h = [*TEST, "--system", "S4h", "--label", "S4h", *PRIMED, "--perturb", perturbation]
        output = f"{degraded}/cord_s4h_{perturbation}_v1_1_1.json"
        steps.append(Step(f"S4h {perturbation}", s4h, output))
    return steps


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(command: list[str], timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603


def _ac_online() -> bool | None:
    from evals.power import ac_online_now

    return ac_online_now()


def _ollama(path: str, payload: dict[str, Any] | None = None, timeout: float = 30) -> Any:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(  # noqa: S310 (fixed local address)
        f"{OLLAMA}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode())


def gather_facts() -> dict[str, Any]:
    """Everything the pre-flight judges, measured now."""
    facts: dict[str, Any] = {"measured_utc": now()}
    status = _run(["git", "status", "--porcelain"]).stdout
    facts["git_commit"] = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    facts["git_dirty_files"] = [line for line in status.splitlines() if line.strip()]
    facts["protocol_commit_is_ancestor"] = (
        _run(["git", "merge-base", "--is-ancestor", PROTOCOL_COMMIT, "HEAD"]).returncode == 0
    )
    facts["boot_age_minutes"] = round((time.time() - psutil.boot_time()) / 60, 1)
    facts["ac_online"] = _ac_online()
    docker = _run(["docker", "info"]) if _has("docker") else None
    facts["docker_daemon_running"] = docker is not None and docker.returncode == 0
    names = {(p.info["name"] or "").lower() for p in psutil.process_iter(["name"])}
    facts["docker_processes"] = sorted(n for n in names if n in DOCKER_PROCESSES)
    facts["free_ram_gib"] = round(psutil.virtual_memory().available / 2**30, 3)
    facts["vscode_running"] = "code.exe" in names
    facts["ollama_max_loaded_models"] = os.environ.get("OLLAMA_MAX_LOADED_MODELS") or _user_env(
        "OLLAMA_MAX_LOADED_MODELS"
    )
    try:
        facts["ollama_version"] = _ollama("/api/version")["version"]
        tags = _ollama("/api/tags")["models"]
        facts["model_digest"] = next((m["digest"] for m in tags if m["name"] == MODEL), None)
    except OSError as error:
        facts["ollama_version"], facts["model_digest"] = None, None
        facts["ollama_error"] = type(error).__name__
    return facts


def _has(program: str) -> bool:
    from shutil import which

    return which(program) is not None


def _user_env(name: str) -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return None


def judge(facts: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """(check, passed, detail) for each pre-flight item. Pure, so it is unit-tested."""
    return [
        ("clean commit", not facts["git_dirty_files"],
         f"{len(facts['git_dirty_files'])} changed or untracked files"),
        ("protocol commit is in history", facts["protocol_commit_is_ancestor"], PROTOCOL_COMMIT),
        ("fresh reboot", facts["boot_age_minutes"] <= MAX_BOOT_AGE_MINUTES,
         f"booted {facts['boot_age_minutes']} min ago (limit {MAX_BOOT_AGE_MINUTES})"),
        ("AC power", facts["ac_online"] is True, f"ac_online={facts['ac_online']}"),
        ("Docker stopped", not facts["docker_daemon_running"] and not facts["docker_processes"],
         f"daemon={facts['docker_daemon_running']} processes={facts['docker_processes']}"),
        ("free RAM", facts["free_ram_gib"] >= MIN_FREE_RAM_GIB,
         f"{facts['free_ram_gib']} GiB available (minimum {MIN_FREE_RAM_GIB})"),
        ("Ollama and model", facts["model_digest"] == MODEL_DIGEST,
         f"version={facts['ollama_version']} digest={str(facts['model_digest'])[:12]}"),
        ("OLLAMA_MAX_LOADED_MODELS=1", facts["ollama_max_loaded_models"] == "1",
         f"value={facts['ollama_max_loaded_models']}"),
    ]  # fmt: skip


class KeepAwake:
    """Holds a Windows keep-awake request while the run lives (scripts/keep_awake.ps1)."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> bool:
        script = ROOT / "scripts" / "keep_awake.ps1"
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                   "-Minutes", str(KEEP_AWAKE_MINUTES)]  # fmt: skip
        self.process = subprocess.Popen(command)  # noqa: S603
        time.sleep(3)
        return self.process.poll() is None

    def release(self) -> str:
        if self.process is None:
            return "keep-awake was not started"
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=30)
            return f"keep-awake released: stopped process {self.process.pid}"
        return f"keep-awake process {self.process.pid} had already ended"


def check_runner_flags(steps: list[Step], log: Any) -> list[str]:
    """Each runner must list every flag the protocol passes it (from its own --help)."""
    problems = []
    for module in sorted({step.module_args[0] for step in steps}):
        completed = _run([sys.executable, "-m", module, "--help"], timeout=300)
        flags = {a for s in steps if s.module_args[0] == module for a in s.module_args[1:]
                 if a.startswith("--")}  # fmt: skip
        missing = sorted(flag for flag in flags if flag not in completed.stdout)
        log(f"flags {module}: exit {completed.returncode}, missing {missing or 'none'}")
        if completed.returncode != 0 or missing:
            problems.append(module)
    return problems


def warm_model() -> float:
    started = time.perf_counter()
    _ollama("/api/generate", {"model": MODEL, "prompt": "", "keep_alive": "60m",
                              "options": {"num_ctx": NUM_CTX}}, timeout=600)  # fmt: skip
    return round(time.perf_counter() - started, 2)


def _new_aborts(before: set[str]) -> list[str]:
    return sorted({p.name for p in ABORTED.glob("*.json")} - before)


def run_step(step: Step, log_file: Any, log: Any) -> str:
    """'done', 'skipped' (output existed), 'failed' or 'power' (AC lost)."""
    if (ROOT / step.output).exists():
        step.status = "skipped: output already exists"
        log(f"{step.name}: output exists, skipped")
        return "skipped"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        before = {p.name for p in ABORTED.glob("*.json")} if ABORTED.exists() else set()
        started = now()
        log(f"{step.name}: attempt {attempt} started")
        log_file.flush()
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-u", "-m", *step.module_args],
            cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT, check=False,
        )  # fmt: skip
        aborts = _new_aborts(before) if ABORTED.exists() else []
        record = {"attempt": attempt, "started_utc": started, "ended_utc": now(),
                  "exit_code": completed.returncode, "abort_records": aborts}  # fmt: skip
        step.attempts.append(record)
        log(f"{step.name}: attempt {attempt} exit {completed.returncode} aborts {aborts}")
        if completed.returncode == 0:
            step.status = "done"
            return "done"
        if completed.returncode == ABORT_EXIT and any("on_battery" in a for a in aborts):
            step.status = "stopped: AC power lost"
            return "power"
        if completed.returncode != ABORT_EXIT or not aborts:
            step.status = f"failed: exit {completed.returncode}"
            return "failed"
        _run(["ollama", "stop", MODEL])
        time.sleep(RETRY_PAUSE_SECONDS)
    step.status = f"failed: {MAX_ATTEMPTS} memory aborts"
    return "failed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-only", action="store_true", help="pre-flight only; no test read")
    arguments = parser.parse_args(argv)
    facts = gather_facts()  # before this run writes anything, so the clean-tree check is honest
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    kind = "check" if arguments.check_only else "run"
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / f"final-{kind}-{stamp}.log"
    metadata: dict[str, Any] = {"protocol": PROTOCOL, "mode": kind, "started_utc": now(),
                                "log": log_path.relative_to(ROOT).as_posix()}  # fmt: skip
    exit_code = 0
    keep_awake = KeepAwake()
    steps = protocol_steps()
    with log_path.open("a", encoding="utf-8") as log_file:

        def log(message: str) -> None:
            line = f"{now()} {message}"
            print(line, flush=True)
            log_file.write(line + "\n")
            log_file.flush()

        try:
            log(f"START {kind}, {len(steps)} protocol steps")
            checks = judge(facts)
            awake = keep_awake.start()
            checks.append(("keep-awake on", awake, "scripts/keep_awake.ps1 running"))
            for name, passed, detail in checks:
                log(f"PREFLIGHT {'PASS' if passed else 'FAIL'} {name}: {detail}")
            metadata["preflight"] = {"facts": facts, "checks": [
                {"check": n, "passed": p, "detail": d} for n, p, d in checks]}  # fmt: skip
            failed = [name for name, passed, _ in checks if not passed]
            if arguments.check_only:
                problems = check_runner_flags(steps, log)
                for step in steps:
                    state = "exists" if (ROOT / step.output).exists() else "to run"
                    log(
                        f"STEP {step.name}: {' '.join(step.module_args)} -> {step.output} ({state})"
                    )
                metadata["runner_flag_problems"] = problems
                exit_code = PREFLIGHT_FAILED if failed or problems else 0
                verdict = "FAILED: " + ", ".join(failed) if failed else "passed"
                log(f"CHECK-ONLY: pre-flight {verdict}; test was not read")
                return exit_code
            if failed:
                log(f"PRE-FLIGHT FAILED: {', '.join(failed)}. Test was not read.")
                exit_code = PREFLIGHT_FAILED
                return exit_code
            metadata["model_warm_seconds"] = warm_model()
            log(f"model warmed in {metadata['model_warm_seconds']} s")
            s1_records_failed = False
            for step in steps:
                if s1_records_failed and step.name.startswith("S5-S1"):
                    step.status = "not evaluated: S1 records rerun did not reproduce predictions"
                    log(f"{step.name}: {step.status}")
                    continue
                outcome = run_step(step, log_file, log)
                if outcome == "failed" and step.name == "S1 records rerun":
                    s1_records_failed = True
                    continue
                if outcome in ("failed", "power"):
                    log(f"STOPPED at {step.name}: {step.status}")
                    exit_code = STEP_FAILED
                    break
            return exit_code
        except KeyboardInterrupt:
            log("INTERRUPTED; rerun the same command to resume")
            exit_code = 12
            return exit_code
        finally:
            log(keep_awake.release())
            metadata["keep_awake"] = "released"
            metadata["steps"] = [asdict(step) for step in steps]
            metadata["memory_aborts"] = sum(
                len(a["abort_records"]) for s in steps for a in s.attempts
                if not any("on_battery" in r for r in a["abort_records"])
            )  # fmt: skip
            metadata["ended_utc"] = now()
            metadata["exit_code"] = exit_code
            target = (FINAL if kind == "run" else LOGS) / f"final-{kind}-metadata-{stamp}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            log("SUMMARY")
            for step in steps:
                log(f"  {step.name}: {step.status}, attempts {len(step.attempts)}")
            log(f"  memory aborts: {metadata['memory_aborts']}; metadata {target.name}")
            log(f"EXIT={exit_code}")


if __name__ == "__main__":
    sys.exit(main())
