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
| 4 | Worker service in Compose | NOT STARTED | Needs the Dockerfile (Phase 9) |
| 4 | Webhooks | NOT STARTED | Tables exist only |
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
| 7 | S5 code (units, calibrator, thresholds, grouped variant) | IMPLEMENTED BUT UNVERIFIED | backend/tests/unit/test_s5.py; not run on real predictions yet |
| 7 | S5 run | NOT STARTED | Needs S4h on all 800 train documents; waits for the model decision |
| 7 | Final S1-S5 test read, once, from a clean commit | NOT STARTED | Last step |
| 7 | Ablations, degradation | NOT STARTED | Follow S5 |
| 7 | SROIE | BLOCKED | Removed: official access unavailable; mirror terms unverified. Labels and vendor groups deleted; adapter kept with fictional fixtures |
| 6 | Frontend pages | NOT STARTED | |
| 8 | Testing and hardening | NOT STARTED | |
| 9 | Deployment | NOT STARTED | |
| 10 | Documentation | IN PROGRESS | Minimal README only |
| 11 | Portfolio and publication preparation | NOT STARTED | |
| 12 | Final verification and report | NOT STARTED | |

## Acceptance criteria

| Id | Status | Note |
|---|---|---|
| A1 | IN PROGRESS | Upload, batch, rejection and dedup work, and the worker processes jobs; no frontend yet |
| A2 | VERIFIED | test_ocr_parser.py, test_pdfium_parser.py |
| A3 | IN PROGRESS | Default and alternative schemas work offline; Ollama used with cord_receipt only |
| A4 | IN PROGRESS | Fields, evidence and validations are persisted by the worker; no review API yet |
| A5 | NOT STARTED | |
| A6 | IN PROGRESS | Export functions and OpenAPI exist; no export endpoints or webhooks |
| A7 | VERIFIED | backend/tests/api, docs/progress/logs/mutation-check.txt |
| A8 | IN PROGRESS | Worker crash, retry, dead-letter and model-unavailable tests pass; webhooks not built |
| A9 | IMPLEMENTED BUT UNVERIFIED (local mirror; GitHub run pending human approval) | docs/progress/logs/ci-local.txt |
| A10 | NOT STARTED | |
| A11 | IN PROGRESS | S1 on CORD test; S2-S4 on validation only; S5 not started |
| A12 | IN PROGRESS | CORD layout groups for S1. No real vendor-grouped split was possible |
| A13 | NOT STARTED | Follows S5 |
| A14 | IN PROGRESS | Split hashes and overlap tests exist, documented in docs/evaluation.md |
| A15 | NOT STARTED | |
| A16 | IN PROGRESS | No claims published yet |
| A17 | IN PROGRESS | Scan clean, no trailers, nothing pushed; licence options not drafted |

## Blockers

| Blocker | Human action |
|---|---|
| SROIE results | None required. Blocked by decision; reopen only if official access appears |
| CI on GitHub unverified | Approve creating a remote; nothing is pushed until then |
| LLM still below rules on CORD after prompt 2.2 (S4h row F1 0.292 vs 0.377) | Decide on the model proposal; nothing is pulled without approval |
