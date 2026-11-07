"""Start a worker: recover abandoned jobs, then process the queue.

One worker, one job at a time, in this process (no fork), so the OCR model and the LLM client
stay loaded and memory stays bounded. RQ's scheduler runs the backoff retries.

    python -m ledgerlens.workers.run [--burst]
"""

import argparse

from rq import SimpleWorker

from ledgerlens.core.config import Settings
from ledgerlens.core.logs import configure_logging
from ledgerlens.workers import tasks
from ledgerlens.workers.queue import queue_for


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--burst", action="store_true", help="exit when the queue is empty")
    arguments = parser.parse_args(argv)
    configure_logging()
    settings = Settings()  # type: ignore[call-arg]
    context = tasks.WorkerContext.build(settings)
    tasks.use_context(context)
    tasks.recover_abandoned(context, max_attempts=len(settings.job_retry_intervals) + 1)
    worker = SimpleWorker([queue_for(context.redis, settings)], connection=context.redis)
    worker.work(burst=arguments.burst, with_scheduler=not arguments.burst)


if __name__ == "__main__":
    main()
