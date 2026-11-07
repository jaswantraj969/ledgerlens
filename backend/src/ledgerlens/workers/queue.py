"""Putting jobs on the queue. Shared by the API and by worker recovery."""

import redis
from rq import Queue, Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job as RqJob

from ledgerlens.core.config import Settings

WORKER_TASK = "ledgerlens.workers.tasks.process_document"
_PENDING = {"queued", "started", "scheduled", "deferred"}


def queue_for(connection: redis.Redis, settings: Settings) -> Queue:
    return Queue(settings.queue_name, connection=connection)


def is_pending(connection: redis.Redis, job_id: str) -> bool:
    """True while RQ will still run the job: waiting, running, or scheduled for a retry."""
    try:
        status = RqJob.fetch(job_id, connection=connection).get_status(refresh=True)
    except NoSuchJobError:
        return False
    # JobStatus is a str enum whose hash is its name, so compare by value.
    return getattr(status, "value", status) in _PENDING


def enqueue(
    connection: redis.Redis, settings: Settings, job_id: str, *, force: bool = False
) -> bool:
    """Queue a job unless RQ already holds it. `force` is for recovering abandoned jobs.

    Returns whether a job was queued. Raises redis.RedisError when Redis is unavailable.
    """
    if not force and is_pending(connection, job_id):
        return False
    intervals = settings.job_retry_intervals
    queue_for(connection, settings).enqueue(
        WORKER_TASK,
        job_id,
        job_id=job_id,
        job_timeout=settings.job_timeout_seconds,
        retry=Retry(max=len(intervals), interval=intervals) if intervals else None,
        failure_ttl=30 * 24 * 3600,
    )
    return True
