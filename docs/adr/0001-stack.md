# ADR-0001: Application stack

Status: Accepted  
Date: 2026-11-05

## Decision
Python 3.12 (through uv), FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL 16, Redis, structlog, Prometheus client. OpenTelemetry is left out.

## Why
The specification names this stack and nothing on this machine rules it out. 3.12 is used over the system 3.13 because ML wheels arrive there first.

## Consequences
Docker supplies Postgres and Redis in development. SQLite is limited to unit tests. `make` is absent on this machine, so Windows instructions need an equivalent.
