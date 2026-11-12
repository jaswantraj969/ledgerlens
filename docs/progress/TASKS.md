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
| 8 | Testing and hardening | VERIFIED | Security review (docs/security-review.md), Phase 8 suites (docs/progress/logs/phase8-final-*.log), release suites (docs/progress/logs/release-ci-local.log) |
| 9 | Dockerfiles and full compose stack | VERIFIED | docs/progress/logs/run-docker-compose-up.log: all five services healthy. Web published on 8081 for this run because an unrelated httpd holds 8080 here (LEDGERLENS_WEB_PORT) |
| 9 | Playwright flow against the Compose stack | VERIFIED | docs/progress/logs/run-e2e-docker.log (1 passed) |
| 10 | Documentation | VERIFIED | README top section, quickstart with command status, data attribution; docs/README.md index; architecture diagram of the running services. Quickstart passed unaided in a fresh clone (docs/progress/logs/phase12-fresh-clone.log) |
| 11 | Portfolio and publication preparation | IMPLEMENTED BUT UNVERIFIED | Drafts in docs/portfolio/ (summary, Upwork entry, case study), numbers checked by script against evals/results/final/; screenshots local only (CORD images, R10). Publishing is the owner's step |
| 12 | Final verification and report | VERIFIED | docs/progress/final-report.md; docs/progress/logs/release-fresh-clone.log, release-ci-local.log, release-prepush-audit.txt, release-reproduce.log |
| R | Release A1: MIT LICENSE, licence metadata, README licence | VERIFIED | LICENSE, backend/pyproject.toml, frontend/package.json, docs/progress/logs/release-prepush-audit.txt |
| R | Release A2: neutral script wording; 0 attribution matches in tracked files | VERIFIED | docs/progress/logs/release-prepush-audit.txt |
| R | Release A3: power events written to a gitignored path | VERIFIED | evals/power.py, tests/unit/test_power.py; tracked tree unchanged in docs/progress/logs/release-fresh-clone.log |
| R | Release A4: tasks.sh test prints the pytest summary | VERIFIED | docs/progress/logs/release-fresh-clone.log (BACKEND PYTEST SUMMARY line) |
| R | Release A5: mypy source count independent of local caches | VERIFIED | backend/pyproject.toml exclude; 107 files in working copy and clone |
| R | Release A6: portfolio precision wording, number check | VERIFIED | docs/progress/logs/portfolio-number-check.log |
| R | Release A7: README status v1.0.0 | VERIFIED | README.md |
| R | Release A8: README images from synthetic invoices; CORD captions | VERIFIED | docs/images/, docs/progress/logs/readme-images.log, docs/portfolio/screenshot-captions.md |
| R | Release B9: CI workflow review | VERIFIED | .github/workflows/ci.yml; docs/progress/logs/release-ci-linux-simulation.log |
| R | Release B10: local CI mirror at a clean HEAD | VERIFIED | docs/progress/logs/release-ci-local.log |
| R | Release C11-C13: fresh clone, audit, integrity and reproduce | VERIFIED | docs/progress/logs/release-fresh-clone.log, release-prepush-audit.txt, release-reproduce.log |
| R | Release D14-D16: CHANGELOG, final report, task status, v1.0.0 tag | VERIFIED | CHANGELOG.md, docs/progress/final-report.md; the first tag (never pushed) was deleted and v1.0.0 recreated after the A5 and A6 work (below) |
| R | Release E17-E19: push to a private remote and GitHub CI | BLOCKED | No remote URL given (placeholder in the release instructions); nothing pushed |
| R2 | Step 1: A5 audit-trail view | VERIFIED | GET /documents/{id}/audit (read-only, organisation-scoped); review-page panel; backend/tests/api/test_audit_and_batch_export.py; frontend components.test.tsx; Playwright flow in docs/progress/logs/release-fresh-clone.log |
| R2 | Step 2: A6 batch export | VERIFIED | POST /documents/export (cap 50, reviewed and owned only); documents-page action; same tests as step 1 |
| R2 | Step 3: A13 recorded as verified in scope | VERIFIED | docs/progress/logs/release-reproduce.log |
| R2 | Step 4: all checks at one commit, logs in the next commit, tag v1.0.0 on the log commit | VERIFIED | docs/progress/logs/release-ci-local.log, release-fresh-clone.log, release-prepush-audit.txt, release-reproduce.log (each names the commit it ran at) |
| R2 | Step 6: push to a private remote and GitHub CI | BLOCKED | No remote URL given (placeholder); nothing pushed |

## Acceptance criteria

| Id | Status | Note |
|---|---|---|
| A1 | VERIFIED | PDF, scanned PDF (test_ocr_parser.py::test_auto_parser_runs_ocr_on_scanned_pdf...), JPEG/PNG, single and batch upload; oversize, unsupported, disguised and too-many-pages rejected; duplicates idempotent (backend/tests/api/test_documents.py); 503 passed in docs/progress/logs/release-ci-local.log |
| A2 | VERIFIED | backend/tests/unit/test_ocr_parser.py, test_pdfium_parser.py (bboxes, confidence, null when unavailable) |
| A3 | VERIFIED | Default and alternative schema offline (tests/e2e/test_vertical_slice.py::test_alternative_schema_comes_from_config_alone); Ollama path used for every LLM result in evals/results/final/ (cord_receipt schema) |
| A4 | VERIFIED | Evidence status, validations, signals, risk score and decision persist (tests/api/test_review.py); calibrated_prob stays null in the application because no calibrator is fitted there (docs/limitations.md) |
| A5 | VERIFIED | Evidence highlighting, approve/reject/correct and the risk-ordered queue (frontend tests, Playwright flow). Audit trail stored (test_documents.py, test_review.py), served read-only by GET /documents/{id}/audit with organisation scoping (backend/tests/api/test_audit_and_batch_export.py: order and old/new values, rejection, cross-organisation isolation, viewer access, 401) and shown newest first on the review page (frontend/src/components/components.test.tsx: panel contents, reload after a review action, page usable if the trail fails); the Playwright flow checks that the correction appears in the audit trail (docs/progress/logs/release-fresh-clone.log) |
| A6 | VERIFIED | JSON and CSV export per document and in batch: POST /documents/export, same format as single export, at most 50 reviewed documents of the caller's organisation (backend/tests/api/test_audit_and_batch_export.py: success in both formats, mixed ownership refused, unreviewed refused, cap, 401); select-and-export on the documents page (components.test.tsx: request body, only reviewed selectable, refusal shown). OpenAPI at /docs and /openapi.json; HMAC-signed webhooks with retries (test_review.py, test_webhooks.py) |
| A7 | VERIFIED | Roles, API keys, cross-organisation isolation, rate limits (test_auth.py, test_documents.py, test_route_auth.py); no secrets or document content in logs (test_health.py::test_logs_hold_no_secrets_or_document_content); docs/security-review.md |
| A8 | VERIFIED | Worker crash, retry, dead-letter, invalid LLM output fallback (tests/api/test_worker.py, tests/unit/test_llm.py); readiness reflects each dependency (test_health.py) |
| A9 | IMPLEMENTED BUT UNVERIFIED | ruff, mypy strict (backend and evals), backend and frontend tests pass locally (docs/progress/logs/release-ci-local.log, 96% core coverage) and in a Linux simulation of the workflow (docs/progress/logs/release-ci-linux-simulation.log); no GitHub run, because no remote exists |
| A10 | VERIFIED | Fresh clone following the README: compose up to healthy, all suites, e2e, clean tracked tree (docs/progress/logs/release-fresh-clone.log; same machine, separate Compose project) |
| A11 | VERIFIED (scope per ADR-0013) | CORD test: per-field P/R/F1 with CIs, ECE, Brier, ROC-AUC, automation and achieved precision at 0.98/0.99, review workload, cost 0 (local), p50/p95 latency on AC, n per field (evals/results/final/); synthetic: S1 and S2' only, by ADR-0013 |
| A12 | VERIFIED (layout groups) | S5 grouped variant on unseen layout groups next to document-level results (evals/results/final/cord_s5_test_v1_1_1.md); S1 layout groups (evals/results/cord_s1_v1_1_layout_groups.md); no vendor split is possible on CORD (evals/datasets/LICENSES.md) |
| A13 | VERIFIED (scoped) | Ablations and degradation done (evals/results/final/); make reproduce regenerates all 30 final files byte-identically from the saved result files (docs/progress/logs/release-reproduce.log). Replaying the test runs needs the CORD caches, which are gitignored by design (R10), so a fresh clone cannot replay them |
| A14 | VERIFIED | Split hashes stored, ID overlap test (test_cord_runner_guards.py::test_split_ids_do_not_overlap...), layout-group roles; content near-duplicates found post hoc are documented (cord-cross-split-duplicates.txt, addendum 01) |
| A15 | VERIFIED | README (quickstart, results, limitations link, research-prototype statement), docs/README.md index, docs/limitations.md, docs/security-review.md, docs/progress/final-report.md |
| A16 | VERIFIED | README and final-report numbers checked against result files; portfolio numbers checked by scripts/check_portfolio_numbers.py (docs/progress/logs/portfolio-number-check.log); README screenshots are synthetic (docs/progress/logs/readme-images.log) |
| A17 | VERIFIED | One identity on every commit, 0 attribution matches in commits and tracked files, gitleaks clean over the full history, no data or weights ever committed, MIT LICENSE, nothing pushed (docs/progress/logs/release-prepush-audit.txt); CHANGELOG.md |

## Blockers

| Blocker | Human action |
|---|---|
| SROIE results | None required. Blocked by decision; reopen only if official access appears |
| CI on GitHub unverified (Release E) | Give a private remote URL; then push main and v1.0.0 and watch the run |
| LLM mode inside Docker unverified | Run scripts/run_docker_llm_smoke.ps1 with other applications closed |
| Upwork portfolio | Owner reviews docs/portfolio/ and publishes; nothing is published by the project |
| LLM below rules on CORD (test: S4h row F1 0.253 against 0.365 for S1) and qwen3:4b does not fit in RAM | None required now. A larger model needs a machine with more RAM |
