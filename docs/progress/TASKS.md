# Tasks

Labels: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED BUT UNVERIFIED, VERIFIED.

| Phase | Task | Status | Evidence |
|---|---|---|---|
| 1 | Environment inspection | VERIFIED | docs/progress/logs/environment.txt |
| 2 | Tasks, criteria, ADRs, architecture | VERIFIED | docs/adr/ (11 files), docs/acceptance-criteria.md, docs/architecture.md |
| 3 | Backend and frontend scaffold, lockfile, Compose services | VERIFIED | docs/progress/logs/phase3-checks.txt, docs/progress/logs/phase3-frontend.txt |
| 3 | pre-commit hooks installed and run on commit | VERIFIED | docs/progress/logs/ci-local.txt |
| 3 | CI workflow | IMPLEMENTED BUT UNVERIFIED (local mirror; GitHub run pending human approval) | docs/progress/logs/ci-local.txt |
| R | Run wrapper | VERIFIED | docs/progress/logs/run-logged-tests.txt |
| R | Task runner, Windows equivalents of make | VERIFIED | docs/progress/logs/tasks-check.txt |
| R | GNU make route | IMPLEMENTED BUT UNVERIFIED | make is not installed here; each target only calls scripts/tasks.sh |
| R | Mutation check, 22 of 22 caught | VERIFIED | docs/progress/logs/mutation-check.txt |
| 4 | Schema and Alembic migration, 17 tables | VERIFIED | backend/alembic/versions/0001_initial_schema.py, backend/tests/api |
| 4 | Auth, roles, API keys, org scoping, rate limits, audit, problem responses | VERIFIED | backend/tests/api/test_auth.py, backend/tests/api/test_documents.py |
| 4 | Upload, validation, dedup, storage, batch, list, get, delete, job status | VERIFIED | backend/tests/api/test_documents.py |
| 4 | Health, readiness, metrics, log redaction | VERIFIED | backend/tests/api/test_health.py |
| 4 | RQ worker and persisted pipeline: idempotent steps, retries with backoff, dead-letter, crash recovery | VERIFIED | backend/tests/api/test_worker.py (9 tests), docs/progress/logs/run-worker-tests.log |
| 4 | Worker service in Compose | VERIFIED | docs/progress/logs/run-docker-compose-up.log (worker healthy; API readiness reports worker true) |
| 4 | Webhooks: HMAC-signed, retries with backoff, URL safety | VERIFIED | backend/tests/api/test_webhooks.py (10 tests) |
| 4 | Review, queue, page image, export and evaluation report endpoints | VERIFIED | backend/tests/api/test_review.py (13 tests) |
| 5 | Normalisation 1.0, frozen | VERIFIED | evals/normalization.lock |
| 5 | Parsers, deterministic extractor, evidence, features, heuristic risk, export | VERIFIED | backend/tests/unit |
| 5 | Replay cache, Ollama provider, LLM passes A and B, cross-pass merge | VERIFIED | backend/tests/unit/test_llm.py, backend/tests/unit/test_merge.py, backend/tests/unit/test_systems.py |
| 5 | Hosted providers | NOT STARTED | Not to be built now, per review. The provider interface allows a later LiteLLM provider |
| 5 | Calibrators | NOT STARTED | Later, on train and validation only |
| 7 | CORD v2 data, splits, layout groups | VERIFIED | evals/splits/cord_v2/ |
| 7 | Metrics 1.1 with row-level matching | VERIFIED | backend/tests/unit/test_metrics_v1_1.py, docs/evaluation.md |
| 7 | Metrics 1.1.1 (exact match dropped from tables), results rescored from saved predictions | VERIFIED | docs/progress/logs/metrics-1-1-1-rescore.txt |
| 7 | Memory sampler test and 0.4 GiB abort | VERIFIED | backend/tests/unit/test_memory_guard.py |
| 7 | Pre-registration: prompt round, label proximity, S4h, S5, layout-group holdout | VERIFIED | docs/evaluation.md, evals/splits/cord_v2/layout_group_holdout.json, prompt_dev_train100.json (commit eb5c68f) |
| 5 | Label proximity check and feature | VERIFIED | backend/tests/unit/test_label_proximity.py |
| 5 | S4h hybrid | VERIFIED | backend/tests/unit/test_hybrid.py, backend/tests/unit/test_systems.py |
| 7 | S1 reproduction under 1.0 | VERIFIED | docs/progress/logs/s1-reproduction.txt |
| 7 | S1 on CORD test under 1.1 | VERIFIED | evals/results/cord_s1_v1_1.md |
| 7 | S1 synthetic, dev versus held-out | VERIFIED | evals/results/synthetic_s1_v1_1.md |
| 7 | A12 check on CORD layout groups | VERIFIED | evals/results/cord_s1_v1_1_layout_groups.md |
| 7 | S2 on validation | IN PROGRESS | evals/results/dev/cord_s2_validation_v1_1.md. Test read is pending |
| 7 | S3 on validation | IN PROGRESS | evals/results/dev/cord_s3_validation_v1_1.md. Test read is pending |
| 7 | S4 on validation | IN PROGRESS | evals/results/dev/cord_s4_validation_v1_1.md. Test read is pending |
| 7 | Prompt round 2 on train subset; 2.2 chosen | VERIFIED | evals/results/dev/prompt_round/prompt_round.md |
| 7 | S2', S3', S4', S4h on validation, read once | VERIFIED | evals/results/dev/cord_validation_comparison_v1_1_1.md. Test read is pending |
| 7 | S2' on synthetic, dev versus held-out ledger | VERIFIED | evals/results/synthetic_s2p_v1_1_1.md |
| 7 | Memory measurement and explanation | VERIFIED | evals/results/dev/memory_measurement.json, docs/progress/ENVIRONMENT.md |
| 7 | Thinking-off for qwen3 in the Ollama provider | VERIFIED | backend/tests/unit/test_thinking_off.py |
| 7 | Model comparison llama3.2:3b against qwen3:4b | BLOCKED | qwen3:4b aborted twice on memory before any result; not adopted under the pre-registered rule (ADR-0012). No S4h-qwen row |
| 7 | llama S4h baseline on the train subset | VERIFIED | evals/results/dev/prompt_round/cord_s4h_prompt_dev_train100_p2.2_v1_1_1.json (mean F1 0.578, warm p95 19.73 s, 3 aborts) |
| 7 | S5 code (units, calibrator, thresholds, grouped variant) | VERIFIED | backend/tests/unit/test_s5.py; run on real predictions for S5-S1 |
| 7 | S5-S1 on validation (calibrator fitted on train) | VERIFIED | evals/results/dev/cord_s5_validation_comparison_v1_1_1.md. Test not read |
| 7 | S4h llama3.2:3b on all 800 train documents | VERIFIED | evals/results/dev/prompt_round/cord_s4h_train_all_p2.2_v1_1_1.json; 10 attempts (9 memory aborts, resumed from the replay cache); latency battery-affected |
| 7 | S5-S4h on validation (calibrator fitted on train) | VERIFIED | evals/results/dev/cord_s5_validation_comparison_v1_1_1.md; docs/progress/logs/run-s5-s4h-*.log. Test not read |
| 7 | Power state per timed run; audit of existing latency figures | VERIFIED | evals/power.py, evals/runners/audit_power.py, docs/progress/logs/power-audit.json; only S4h train_all is battery-affected. Test split refuses to run off AC |
| 7 | Final S1-S5 test read, once, from a clean commit | VERIFIED | Protocol 2550b14; run log docs/progress/logs/final-run-20261112T073516Z.log (EXIT=0, 18/18 steps, 8 memory aborts resumed); integrity checks docs/progress/logs/final-integrity.txt (all pass); tables evals/results/final/ |
| 7 | Ablations, degradation | VERIFIED | evals/results/final/cord_s5_ablations_test_v1_1_1.md, cord_degradation_test_v1_1_1.{md,png} |
| 7 | SROIE | BLOCKED | Removed: official access unavailable; mirror terms unverified. Labels and vendor groups deleted; adapter kept with fictional fixtures |
| 6 | Frontend: upload and batch, job status, review with boxes, approve/reject/correct, queue, export, evaluation page | VERIFIED | frontend/src (36 Vitest tests), npm run build |
| 6 | Playwright upload, review, export flow | VERIFIED (local dev stack, not Docker) | docs/progress/logs/run-e2e-local.log |
| 8 | Testing and hardening | NOT STARTED | |
| 9 | Dockerfiles and full compose stack | VERIFIED | docs/progress/logs/run-docker-compose-up.log: all five services healthy. Web published on 8081 for this run because an unrelated httpd holds 8080 here (LEDGERLENS_WEB_PORT) |
| 9 | Playwright flow against the Compose stack | VERIFIED | docs/progress/logs/run-e2e-docker.log (1 passed) |
| 10 | Documentation | IN PROGRESS | README results section from the final test files; limitations updated. Some older limitations entries are stale (OCR now exists; S5 calibrators exist in evals but not in the product risk score) |
| 11 | Portfolio and publication preparation | NOT STARTED | |
| 12 | Final verification and report | NOT STARTED | |

## Acceptance criteria

| Id | Status | Note |
|---|---|---|
| A1 | IN PROGRESS | Upload, batch, rejection, dedup, processing, frontend and the Docker stack work (e2e passes on Compose); hardening (Phase 8) not started |
| A2 | VERIFIED | test_ocr_parser.py, test_pdfium_parser.py |
| A3 | IN PROGRESS | Default and alternative schemas work offline; Ollama used with cord_receipt only |
| A4 | VERIFIED | Fields, evidence, validations and review decisions persist; backend/tests/api/test_review.py |
| A5 | NOT STARTED | |
| A6 | VERIFIED | JSON and CSV export endpoints, signed webhooks; test_review.py, test_webhooks.py |
| A7 | VERIFIED | backend/tests/api, docs/progress/logs/mutation-check.txt |
| A8 | VERIFIED | Worker crash, retry, dead-letter, model-unavailable and webhook retry tests pass |
| A9 | IMPLEMENTED BUT UNVERIFIED (local mirror; GitHub run pending human approval) | docs/progress/logs/ci-local.txt |
| A10 | NOT STARTED | |
| A11 | IN PROGRESS | CORD test done for S1-S4h and S5 (evals/results/final/). Synthetic covers S1 and S2' only, not S3-S5; review workload not reported as its own metric |
| A12 | IN PROGRESS | CORD layout groups for S1. No real vendor-grouped split was possible |
| A13 | IN PROGRESS | Ablations and degradation done; final tables and figure regenerate via make reproduce from saved result files (docs/progress/logs/run-reproduce-final.log). make reproduce does not replay the test runs themselves from the caches |
| A14 | IN PROGRESS | Split hashes and overlap tests exist, documented in docs/evaluation.md |
| A15 | NOT STARTED | |
| A16 | IN PROGRESS | No claims published yet |
| A17 | IN PROGRESS | Scan clean, no trailers, nothing pushed; licence options not drafted |

## Blockers

| Blocker | Human action |
|---|---|
| SROIE results | None required. Blocked by decision; reopen only if official access appears |
| CI on GitHub unverified | Approve creating a remote; nothing is pushed until then |
| LLM below rules on CORD (S4h row F1 0.292 against 0.377) and qwen3:4b does not fit in RAM | None required now. A larger model needs a machine with more RAM |
