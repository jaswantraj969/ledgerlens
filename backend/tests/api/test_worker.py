"""The worker against real PostgreSQL and Redis: completion, crash recovery, retries, failures."""

import os
import subprocess
import sys
import textwrap
import time
import uuid
from collections import Counter
from pathlib import Path

import pytest
from evals.synthetic.generate import generate_invoice
from fastapi.testclient import TestClient
from rq import SimpleWorker
from rq.job import Job as RqJob
from rq.registry import FailedJobRegistry
from sqlalchemy import func, select

from ledgerlens.core.config import Settings
from ledgerlens.db.models import ExtractionRun, Field, Job, Page
from ledgerlens.workers import tasks
from ledgerlens.workers.queue import queue_for
from tests.api.conftest import Account

PDF = generate_invoice(3, layout="classic").pdf
UNREACHABLE = "http://127.0.0.1:9"


def upload(client: TestClient, account: Account, data: bytes = PDF) -> dict[str, str]:
    response = client.post(
        "/documents",
        files={"file": ("invoice.pdf", data, "application/pdf")},
        headers=account.headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()  # type: ignore[no-any-return]


def context_for(settings: Settings, **changes: object) -> tasks.WorkerContext:
    context = tasks.WorkerContext.build(settings.model_copy(update=changes))
    tasks.use_context(context)
    return context


def drain(context: tasks.WorkerContext) -> None:
    """Run jobs until none are waiting. Retries scheduled by RQ are moved onto the queue here,
    which is what the scheduler does in a long-running worker."""
    queue = queue_for(context.redis, context.settings)
    registry = queue.scheduled_job_registry
    for _ in range(10):
        SimpleWorker([queue], connection=context.redis).work(burst=True)
        scheduled = registry.get_job_ids()
        if not scheduled:
            return
        for job_id in scheduled:
            registry.remove(job_id)
            queue.enqueue_job(RqJob.fetch(job_id, connection=context.redis))
    pytest.fail("jobs were still scheduled after 10 rounds")


def job(context: tasks.WorkerContext, job_id: str) -> Job:
    with context.sessions() as session:
        found = session.get(Job, uuid.UUID(job_id))
        assert found is not None
        return found


def runs(context: tasks.WorkerContext, document_id: str) -> Counter[str]:
    with context.sessions() as session:
        steps = session.scalars(
            select(ExtractionRun.step).where(ExtractionRun.document_id == uuid.UUID(document_id))
        ).all()
    return Counter(steps)


def field_rows(context: tasks.WorkerContext, document_id: str) -> list[Field]:
    with context.sessions() as session:
        return list(
            session.scalars(
                select(Field)
                .join(ExtractionRun, Field.run_id == ExtractionRun.id)
                .where(ExtractionRun.document_id == uuid.UUID(document_id))
            ).all()
        )


def test_a_job_runs_through_the_pipeline_and_stores_results(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    body = upload(client, admin)
    context = context_for(settings)
    drain(context)

    finished = job(context, body["job_id"])
    fields = field_rows(context, body["id"])
    pending = [f for f in fields if f.decision != "auto_accepted"]
    assert finished.state == ("ready_for_review" if pending else "completed")
    assert finished.attempts == 1
    assert runs(context, body["id"]) == Counter({"parse": 1, "extract": 1})
    assert {f.name for f in fields} >= {"total_amount", "invoice_number"}
    assert all(f.source == "deterministic" for f in fields)
    with context.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Page)) == 1
    status = client.get(f"/jobs/{body['job_id']}", headers=admin.headers).json()
    assert status["state"] == finished.state
    assert status["dead_lettered"] is False
    document = client.get(f"/documents/{body['id']}", headers=admin.headers).json()
    assert document["status"] == finished.state


WORKER_SCRIPT = textwrap.dedent(
    """
    import os, pathlib, time
    from ledgerlens.workers import run, tasks

    hang_at = os.environ.get("HANG_AT")
    marker = pathlib.Path(os.environ["MARKER"])

    def checkpoint(step):
        if step == hang_at:
            marker.write_text(step)
            time.sleep(600)

    tasks.checkpoint = checkpoint
    run.main(["--burst"])
    """
)


def start_worker(settings: Settings, tmp_path: Path, hang_at: str | None) -> subprocess.Popen[str]:
    script = tmp_path / "worker.py"
    script.write_text(WORKER_SCRIPT, encoding="utf-8")
    environment = {
        key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP") if key in os.environ
    }
    environment |= {
        "LEDGERLENS_DATABASE_URL": settings.database_url,
        "LEDGERLENS_REDIS_URL": settings.redis_url,
        "LEDGERLENS_JWT_SECRET": settings.jwt_secret.get_secret_value(),
        "LEDGERLENS_STORAGE_DIR": str(settings.storage_dir),
        "LEDGERLENS_JOB_RETRY_INTERVALS": "[0, 0]",
        "MARKER": str(tmp_path / "marker"),
    }
    if hang_at:
        environment["HANG_AT"] = hang_at
    return subprocess.Popen(
        [sys.executable, str(script)], env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )  # fmt: skip


def wait_for(condition, timeout: float, message: str) -> None:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.2)
    pytest.fail(message)


def lock_is_free(context: tasks.WorkerContext, job_id: str) -> bool:
    with tasks.job_lock(context.engine, uuid.UUID(job_id)) as taken:
        return taken


@pytest.mark.parametrize("killed_at", ["extract_computed", "extracted"])
def test_a_worker_killed_mid_job_is_retried_without_duplicate_fields(
    client: TestClient, admin: Account, settings: Settings, tmp_path: Path, killed_at: str
) -> None:
    """Killed before the extraction is stored, and after it is stored but before finishing."""
    body = upload(client, admin)
    context = context_for(settings)
    marker = tmp_path / "marker"

    first = start_worker(settings, tmp_path, hang_at=killed_at)
    try:
        wait_for(marker.exists, 120, "the worker never reached the kill point")
        assert job(context, body["job_id"]).state in tasks.IN_PROGRESS
        first.kill()
        first.wait(30)
    finally:
        if first.poll() is None:
            first.kill()
    stored_before = runs(context, body["id"])
    assert stored_before["extract"] == (1 if killed_at == "extracted" else 0)
    wait_for(lambda: lock_is_free(context, body["job_id"]), 30, "the dead worker's lock stayed")

    marker.unlink()
    second = start_worker(settings, tmp_path, hang_at=None)
    output, _ = second.communicate(timeout=180)
    assert second.returncode == 0, output

    finished = job(context, body["job_id"])
    fields = field_rows(context, body["id"])
    assert finished.state in ("ready_for_review", "completed")
    assert finished.attempts == 2
    assert runs(context, body["id"]) == Counter({"parse": 1, "extract": 1})
    names = [f.name for f in fields]
    assert names and len(names) == len(set(names))
    with context.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Page)) == 1


def test_an_unavailable_model_fails_the_job_with_a_recorded_reason(
    client: TestClient, admin: Account, settings: Settings, tmp_path: Path
) -> None:
    body = upload(client, admin)
    context = context_for(
        settings,
        extraction_mode="llm",
        ollama_url=UNREACHABLE,
        llm_timeout_seconds=5.0,
        llm_cache_dir=tmp_path / "llm-cache",
    )
    queued = RqJob.fetch(body["job_id"], connection=context.redis)
    assert queued.retries_left == len(settings.job_retry_intervals)
    assert queued.retry_intervals == settings.job_retry_intervals == [10, 60, 300]
    drain(context)  # moves each scheduled retry onto the queue without waiting out the backoff

    failed = job(context, body["job_id"])
    assert failed.state == "failed"
    assert failed.error_code == "llm_unavailable"
    assert failed.error_detail and "ollama request failed" in failed.error_detail
    assert failed.dead_lettered_at is not None
    assert failed.attempts == 1 + len(settings.job_retry_intervals)
    assert runs(context, body["id"]) == Counter({"parse": 1}), "no extraction result stored"
    assert field_rows(context, body["id"]) == []
    registry = FailedJobRegistry(queue=queue_for(context.redis, context.settings))
    assert body["job_id"] in registry.get_job_ids()
    status = client.get(f"/jobs/{body['job_id']}", headers=admin.headers).json()
    assert status["dead_lettered"] is True
    assert status["error_code"] == "llm_unavailable"


def test_an_unavailable_model_degrades_to_rules_only_when_allowed_and_says_so(
    client: TestClient, admin: Account, settings: Settings, tmp_path: Path
) -> None:
    body = upload(client, admin)
    context = context_for(
        settings,
        extraction_mode="llm_or_rules",
        ollama_url=UNREACHABLE,
        llm_timeout_seconds=5.0,
        llm_cache_dir=tmp_path / "llm-cache",
    )
    drain(context)

    finished = job(context, body["job_id"])
    assert finished.state in ("ready_for_review", "completed")
    assert finished.error_detail and finished.error_detail.startswith("degraded: llm_unavailable")
    with context.sessions() as session:
        run = session.scalar(select(ExtractionRun).where(ExtractionRun.step == "extract"))
    assert run is not None
    assert run.provider == "deterministic" and run.model is None
    assert run.version.startswith("rules-fallback:")
    assert run.degraded_reason and run.degraded_reason.startswith("llm_unavailable")
    sources = {f.source for f in field_rows(context, body["id"])}
    assert sources == {"deterministic_fallback"}


def test_a_duplicate_upload_does_not_rerun_the_pipeline(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    body = upload(client, admin)
    context = context_for(settings)
    drain(context)
    before = (runs(context, body["id"]), len(field_rows(context, body["id"])))

    again = upload(client, admin)
    assert again["duplicate"] is True
    assert again["job_id"] == body["job_id"]
    assert len(queue_for(context.redis, context.settings)) == 0
    drain(context)
    assert (runs(context, body["id"]), len(field_rows(context, body["id"]))) == before
    assert job(context, body["job_id"]).attempts == 1


def test_a_duplicate_upload_while_queued_does_not_queue_twice(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    body = upload(client, admin)
    upload(client, admin)
    context = context_for(settings)
    assert queue_for(context.redis, context.settings).job_ids == [body["job_id"]]
    drain(context)
    assert job(context, body["job_id"]).attempts == 1


def test_recovery_leaves_a_job_held_by_a_live_worker(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    body = upload(client, admin)
    context = context_for(settings)
    queue_for(context.redis, context.settings).empty()
    with context.sessions.begin() as session:
        stuck = session.get(Job, uuid.UUID(body["job_id"]))
        assert stuck is not None
        stuck.state = "extracting"
        stuck.attempts = 1
    with tasks.job_lock(context.engine, uuid.UUID(body["job_id"])) as taken:
        assert taken
        assert tasks.recover_abandoned(context, max_attempts=4) == []
    assert tasks.recover_abandoned(context, max_attempts=4) == [uuid.UUID(body["job_id"])]
    assert job(context, body["job_id"]).state == "queued"
    drain(context)
    assert job(context, body["job_id"]).state in ("ready_for_review", "completed")


def test_a_missing_file_fails_at_once_without_retries(
    client: TestClient, admin: Account, settings: Settings
) -> None:
    body = upload(client, admin)
    context = context_for(settings)
    for path in Path(settings.storage_dir).rglob("*"):
        if path.is_file():
            path.unlink()
    drain(context)
    failed = job(context, body["job_id"])
    assert (failed.state, failed.error_code, failed.attempts) == ("failed", "file_missing", 1)
    assert failed.dead_lettered_at is not None
