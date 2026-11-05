# Acceptance criteria

Status labels: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED BUT UNVERIFIED, VERIFIED.
VERIFIED requires an executed command and a saved log path. Current status lives in
[progress/TASKS.md](progress/TASKS.md).

## Functional
- **A1** Upload PDF, scanned PDF and JPG/PNG receipts, single and batch; invalid/oversize/disguised files rejected with clear errors; duplicate upload is idempotent.
- **A2** Parsing stores text, page numbers, bboxes and OCR confidence where the engine provides them; nothing fabricated (test proves null when unavailable).
- **A3** Extraction returns schema-valid output for the default schema and one alternative schema loaded from config; works with the offline default (no API key) and with Ollama when available.
- **A4** Every field has evidence status, validation results, signals, risk score, decision; calibrated_prob present only when a fitted calibrator exists.
- **A5** Review UI: highlight evidence on the page, edit/approve/reject, review queue by risk, audit trail stored and visible.
- **A6** Export JSON and CSV (single and batch); REST API documented in OpenAPI; webhooks HMAC-signed with retries (or documented as not implemented).

## Reliability and security
- **A7** Auth with roles and API keys; cross-org isolation tests pass; rate limiting active; no secrets or field values in logs (test).
- **A8** Worker crash/retry produces no duplicate records (test); invalid LLM output falls back cleanly (test); health/ready endpoints reflect dependency status.

## Engineering
- **A9** ruff, mypy (strict on core packages), backend and frontend tests pass in CI; backend core coverage >= 80% (actual number reported).
- **A10** docker compose up brings the stack to healthy on a clean machine following README; fresh-clone test passes.

## Evaluation
- **A11** S1-S5 evaluated on at least CORD and the synthetic set (SROIE/DocILE if obtainable) with per-field P/R/F1, exact match, ECE, Brier, ROC-AUC, automation rate at 98% and 99% target precision with achieved test precision, review workload, cost, p50/p95 latency, 95% bootstrap CIs, and test-set sizes.
- **A12** Vendor/layout-grouped generalisation results reported next to document-level results.
- **A13** Ablations and degradation study completed; every table/figure regenerates via make reproduce from replay caches.
- **A14** Leakage controls documented and tested (split hashes stored; test that train/cal/test document IDs and grouped vendors do not overlap).

## Documentation and honesty
- **A15** README and docs complete; limitations and known failures stated; "research prototype, not production-validated" statement present.
- **A16** No metric, screenshot or claim in README/portfolio files without a matching results file or saved artefact.
- **A17** Git history clean: no secrets, no data, no AI co-author trailers; licence options drafted; release checklist ready; nothing pushed.

## Task-level additions
- **T1** Money is `Decimal` end to end; a test rejects `float` in money fields.
- **T2** Normalisation rules carry a version number and are frozen before the first experiment.
- **T3** Every results file records git commit, package versions, model ids, seeds, hardware and cache mode.
