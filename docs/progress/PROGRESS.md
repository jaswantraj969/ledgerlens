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

## 2026-11-12, final test read
- Prompt-rule timing confirmed: rule in eb5c68f (09:48:38 UTC on 11-07), before the first prompt-round run (11:50 UTC).
- Final test protocol committed before any test access: 2550b14. Entry script with pre-flight, atomic outputs and done-markers: 4273082, e3a506a.
- First pre-flight failed on free RAM (1.5 to 1.97 GiB with VS Code open); test was not read (1d3ba07).
- Final run, 2026-11-12 07:35 to 08:56 UTC, from 475c048 with VS Code closed: pre-flight passed (6.05 GiB free, booted 3.7 min before), EXIT=0, 18/18 steps, 8 memory aborts, each resumed from cache with the same command. All timed results are AC-only.
- Integrity: S1 rerun reproduced predictions 8b3fccde exactly; 18 done-markers match, none recovered; S5 test thresholds equal the validation-chosen ones (docs/progress/logs/final-integrity.txt).
- make reproduce: validation metrics reproduce exactly; final tables and figure generated.
- Results: S4h does not beat S1 on CORD test except total F1 (0.827 against 0.793, intervals overlap). S5 header precision on test fell short of the 0.98 and 0.99 targets; line items are effectively routed to human review.
- Next: Phase 8 hardening, Phases 10 to 12, GitHub CI (needs a remote created by the human).

## 2026-11-12, supervisor review of the final read, and Phase 8 start
- Synthetic S1 rerun under metrics 1.1.1, rules only: all 375 precision, recall and F1 values equal the 1.1 run.
- CORD has near-duplicates across its official splits: 7 test documents share OCR token text with a train or validation document. Found while labelling replayed timings; recorded in limitations and the README. No result was changed.
- Replayed test timings labelled with their original recording time and power: all on AC.
- S5: exact Clopper-Pearson intervals where fewer than 30 values were accepted; review workload per document with bootstrap intervals.
- README corrected (synthetic under 1.1.1, S1 rerun hash, header precision wording, small samples, workload, degradation exceptions, risk score). ADR-0013 narrows A11 on synthetic data to S1 and S2'. Limitations updated (OCR parsing; risk score unfitted, S5 evaluation-only).
- Phase 8 baseline: backend 458 passed, Vitest 36 passed, Playwright 1 passed on Compose, ruff and backend mypy clean, oxlint 1 warning.

## 2026-11-12, addendum 01 and Phase 8 hardening
- Addendum 01 (post hoc duplicate-exclusion check) committed in a1ec84e, then computed in 1faa328. On the 93 documents, no S1-against-S4h ordering changes on any field.
- oxlint warning fixed; Alembic path_separator set; mypy now checks evals/ in the configured run (type-only fixes; make reproduce guard: all metrics and prediction hashes identical).
- Security review (docs/security-review.md): fixed the webhook replay window, the public-address allow-list, the image pixel limit, the non-root web container, metrics hidden from the proxy, and the unused litellm extra (CVE); risks accepted: open registration, DNS rebinding window, per-email login limit.
- Docker LLM smoke: the worker reaches host Ollama, but the run stopped at the 2 GiB free-RAM gate (0.43 GiB; Docker's VM held 4.7 GB).
- Final suites at a clean HEAD: backend 486 passed, Vitest 36 passed, Playwright 1 passed on Compose, lint and type checks clean.

## 2026-11-12, release preparation (no push, no remote)
- Pre-push audit: one identity on all commits; no attribution strings in any commit message; gitleaks clean over the full history; no file over 5 MB; no dataset file ever committed. LICENSE missing: the owner's decision.
- CORD download script added (pinned revision, checksums); README gains the CC BY 4.0 attribution.
- README top section, quickstart (init_env.py, tasks.sh up), command status table; docs index; architecture diagram of the running services.
- Evaluation page fixed: it now shows the final test table (its note said only S1 had read test).
- Portfolio drafts in docs/portfolio/; screenshots taken with Playwright against Compose, kept out of git.
- Fresh clone: attempt 1 failed on the Windows 260-character path limit (deep clone folder); README now asks for a short path; attempt 2 passed every step unaided at 293cc23 (backend 488, Vitest 37, e2e 1, lint, typecheck, eval-smoke, runtime security checks).

## 2026-11-12/13, v1.0.0 release (local; no remote)
- MIT licence (2026 Jaswant Raj); package metadata and version 1.0.0; README status "v1.0.0, research prototype".
- Tracked files hold no attribution strings: script comment reworded, scratch paths and search terms redacted in old logs (no result changed).
- Power events go to a gitignored path; `tasks.sh test` prints the pytest summary; mypy counts no data folders (107 files in working copy and clone).
- Portfolio precision wording states the 0.98 target and the interval; README screenshots from synthetic invoices.
- CI workflow: actions pinned to commit SHAs, read-only permissions, no secrets; Linux simulation passes (it first exposed a crash where git is unavailable, fixed). Local CI mirror passes: 493 backend tests, 96% coverage, 37 frontend tests.
- Release fresh clone: attempt 1 failed at e2e (a page-image locator also matched the evidence overlay; fixed with an exact name); attempt 2 passes every step with a clean tracked tree.
- Release audit, integrity 8/8, make reproduce byte-identical. CHANGELOG and final report. Tag v1.0.0.
- Not done: push and GitHub CI (no remote URL given), LLM mode inside Docker, A5 audit view, A6 batch export.
