# ADR-0004: Job queue

Status: Accepted  
Date: 2026-11-05

## Decision
Redis + RQ with one job per document that runs the pipeline steps, each idempotent and keyed by (document_id, step, version).

## Why
Simpler than Celery. RQ's default forking worker does not run on native Windows, so workers run in Linux containers; `SimpleWorker` is available for native debugging.

## Consequences
Idempotency lives in the database, not the queue: a retried job must not duplicate fields, whatever RQ delivers.
