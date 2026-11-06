# Progress

## 2026-11-05
- Phase 1 done. Started Docker Desktop; chose Docker-first services with native Python and Node.
- Phase 2 documents written. ADR-0002 is Proposed until Docling is tested.
- Running in the background: Docling probe install; CORD test and validation download into data/cord-v2/raw (gitignored).
- Next: settle ADR-0002, then Phase 3 scaffold.

## 2026-11-06
- Backend environment installed after fixing a stalled-download problem (see ENVIRONMENT.md).
- Checks: 47 tests pass; ruff, ruff format and mypy clean. Log: docs/progress/logs/phase3-checks.txt.
- uv.lock committed (203 packages, including optional extras).
- CORD v2 complete: six files match published SHA-256. Labels inspected; field map in evals/datasets/LICENSES.md.
- Postgres 16.15 and Redis healthy through Compose.
- Open: frontend dev dependencies installing; Docling install; Ollama binary; pre-commit hooks not run.
- Next: finish the frontend test, then the vertical slice (synthetic invoice, parse, extract, verify, export).
