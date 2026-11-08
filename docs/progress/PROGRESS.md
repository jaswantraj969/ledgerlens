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

## 2026-11-07, review steps 1-4 and items 5-7
- Metrics 1.1 with row-level matching. `exact_match` equals `recall` by definition.
- S1 reproduced: 140 values, 0 different, with fresh OCR and again at clean HEAD. Log: docs/progress/logs/s1-reproduction.txt.
- S1 under 1.1: total F1 0.793, row-level F1 0.365, against 0.762 set-based on amounts.
- Synthetic: dev about 1.000, held-out 0.000 on six of seven header fields. Line items held.
- Hooks installed. Task runner added. SROIE blocked. A12 check on CORD layout groups.
- S2, S3 and S4 on validation, with 0 failed extractions and 0 fallbacks. Row-level F1: S1 0.377, S2 0.058, S3 0.055, S4 0.055.
- Phase 4 API, migrations and tests. The worker is not built, so jobs stay queued.
- Mutation check: 22 of 22 caught. Log: docs/progress/logs/mutation-check.txt.
- A commit went in with one test failing (a2d4c67), fixed in 3f5d7de. The hook checks lint and types, not tests, so commit commands must gate on pytest.
- Next: RQ worker and persisted pipeline, then S5 on train and validation.

## 2026-11-07, review 3
- SROIE labels and vendor groups removed in a normal commit; adapter kept with fictional fixtures.
- Metrics 1.1.1: exact match dropped from single-field tables, kept in JSON as redundant. Five results rescored from saved predictions: 155 values each, 0 different.
- Memory sampler tested; runs abort below 0.4 GiB free RAM and write nothing. Five aborts happened and were retried from the replay cache.
- OLLAMA_MAX_LOADED_MODELS=1 set and confirmed in the server log.
- RQ worker and persisted pipeline: 9 tests pass, including a worker killed at two points, an unavailable model, and duplicate uploads.
- Pre-registered prompt round, label proximity, S4h and S5 before any new result (commit eb5c68f).
- Prompt round on train subset: 2.2 chosen (mean F1 0.495 against 0.449 for 1.0). Validation read once for S2', S3', S4', S4h.
- S2' on synthetic: transfers to the held-out layout for most header fields; subtotal does not.
- Local CI: all steps exit 0; 378 backend tests, 96% coverage, gitleaks 69 commits, no leaks.
- Next: model decision, then S4h on all train documents and S5.

## 2026-11-08, review 4 and notes A to C
- Memory: the two free-RAM measures agree within 0.02 GiB; llama3.2:3b at num_ctx 2304 costs about 0.8 GiB of system RAM. Recorded in ENVIRONMENT.md.
- qwen3:4b: thinking-off implemented and tested; pulled; two memory aborts during setup, before any quality result. Not adopted for lack of RAM, no quality judgement made (ADR-0012). llama3.2:3b stays.
- S1 and S4h (llama3.2:3b, prompt 2.2) on all 800 train documents. S4h took 10 attempts: 9 memory aborts, resumed from the replay cache.
- S5-S1 and S5-S4h on validation only, calibrators fitted on train. Header automation 0.237 and 0.197; row automation 0.013 and 0.003 at a 0.98 precision target. Test not read.
- Power: every timed result now carries an AC/battery label from the Windows power log. Only S4h train_all is battery-affected (103 of 2,421 timings). Battery explains the 48 s against 10 s per document; split latency is in ENVIRONMENT.md. The test split refuses to run off AC.
- Product: webhooks (HMAC, retries), review/export API, frontend (36 Vitest tests), Dockerfiles. All five Compose services healthy; Playwright upload-review-export passes on the local dev stack and on the Compose stack.
- Backend: 412 tests pass.
- Next: final S1-S5 test read, once, on AC, from a clean commit, when the supervisor approves.
