# Progress

## Operational lessons

| Failure | Cause | Permanent fix |
|---|---|---|
| Backend install hung about 12 hours | Retry loop had no stall detection; `uv` waited on dead connections, and `TaskStop` ended the shell but not its `uv` child | All long commands run through `scripts/run_logged.sh`: hard timeout, stall detector, heartbeat, child killed |
| Hours lost re-downloading packages | A private `UV_CACHE_DIR`, added to avoid a lock conflict, bypassed the default cache | Keep the default uv cache. Avoid the lock by not running two uv jobs at once |
| Large wheels never finished | `uv` cannot resume, so each timeout discarded partial downloads | `scripts/fetch_wheels.py`: resumable curl plus PyPI SHA-256 check, then `--find-links` |
| False exit-0 notices (failed sync, failed pre-commit, unverified CORD downloads) | The notice reports the wrapper's last command, not the step that mattered | Every log ends in `EXIT=<code>`. Read that line and the log tail before marking anything done. Verify downloads by hash |
| Wrapper lost heartbeats and misjudged progress | Native Windows children ignore append mode on a shared file and overwrite wrapper lines. The first self-tests used shell children, so they hid it | Child output goes through a pipe; `scripts/test_run_logged.sh` tests with a real native child |
| pre-commit reported "files modified" | Its log was written inside the repo during the run | Write logs for pre-commit outside the tree, then copy them in |

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
- Frontend scaffold verified (build, 1 test, oxlint). Log: docs/progress/logs/phase3-frontend.txt.
- pre-commit: all six hooks pass after fixing ruff config. Log: docs/progress/logs/phase3-precommit.txt.
- Offline slice works in-process with no database: synthetic PDF, parse, extract, verify, risk, route, export.
- Checks: 72 tests pass; ruff, format, mypy clean. Log: docs/progress/logs/phase5-slice-checks.txt.
- Mutation check: 6 of 6 deliberate breaks caught. Log: docs/progress/logs/phase5-mutation-check.txt.
- Started docs/limitations.md. Deterministic evidence matching is circular; see that file.
- Next: Phase 4 backend (models, migrations, auth, org scoping, upload, jobs).
