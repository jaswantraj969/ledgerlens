# Progress

## Commit hooks

`--no-verify` was never used: no command in the working sessions passed it. Git does not record that flag, so this rests on the session record, not on history. The stronger fact is that no hook was installed until 2026-11-07, so every earlier commit ran with no hook at all, and two commits went in with ruff failing. History was not rewritten. Hooks are now installed, and CI and `scripts/ci_local.sh` run pre-commit on all files.

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

## 2026-11-06, supervisor review steps 1-8
- Step 1: `scripts/run_logged.sh` and `scripts/test_run_logged.sh`; Operational lessons added above.
- Step 2: `make ci` and `scripts/ci_local.sh`. `make` is not installed here, so the log comes from running the script directly. Log: docs/progress/logs/ci-local.txt.
- Step 3: 10 ADRs, acceptance criteria and architecture confirmed present.
- Step 4: RapidOCR and AutoParser added. ADR-0002 Accepted as a deviation.
- Step 5: `self_sourced` status, `evidence_independent` flag, feature builder excludes dependent matches.
- Step 6: five synthetic layouts, `ledger` held out, overlap and wording tests.
- Step 7: normalisation frozen, protocol committed before metrics, one tuning round on validation, one read of test. Result: evals/results/cord_s1_v1.md.
- Step 8: SROIE adapter and vendor split on 626 labels from a community mirror. Terms unverified, so research-only.
- Step 9: `ollama` is not on PATH, so S2-S5 stay BLOCKED.
- Next: Phase 4 backend.

## 2026-11-07, step 9
- Ollama 0.40.15 recorded in ENVIRONMENT.md. No model pulled.
- Added the replay cache, Ollama provider and LLM pass A with retry and marked fallback.
- Smoke run on 10 seeded CORD validation documents: 10 of 10 valid JSON, 100% GPU, warm p50 2.47 s and p95 6.35 s, cold first document 127.62 s. Log: docs/progress/logs/run-llm-smoke.log.
- Replay of those 10: 0 live calls, 10 hits, same outputs. Log: docs/progress/logs/run-llm-smoke-replay.log.
- ADR-0011 chooses llama3.2:3b. ADR-0003 amended. S2-S5 marked IN PROGRESS.
- The CORD test split was not read by any LLM code.
- Open: the review defining metrics 1.1, the S1 reproduction check and hygiene was not received, so its steps 1-4 have not started.
- Next: review steps 1-4 once the text arrives, then S2-S5 on validation, then test once at the end.
