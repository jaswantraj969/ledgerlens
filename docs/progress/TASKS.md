# Tasks

Labels: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED BUT UNVERIFIED, VERIFIED.

| Phase | Task | Status | Evidence |
|---|---|---|---|
| 1 | Environment inspection | VERIFIED | docs/progress/logs/environment.txt |
| 2 | Tasks, criteria, ADRs, architecture | VERIFIED | docs/adr/ (10 files), docs/acceptance-criteria.md, docs/architecture.md |
| 3 | Backend scaffold, lockfile, Compose services | VERIFIED | docs/progress/logs/phase3-checks.txt |
| 3 | Frontend scaffold and first test | VERIFIED | docs/progress/logs/phase3-frontend.txt |
| 3 | pre-commit hooks | VERIFIED | docs/progress/logs/phase3-precommit.txt |
| 3 | CI workflow | IMPLEMENTED BUT UNVERIFIED (local mirror; GitHub run pending human approval) | docs/progress/logs/ci-local.txt |
| R | Run wrapper: timeout, stall detector, heartbeat, EXIT line | VERIFIED | docs/progress/logs/run-logged-tests.txt |
| 5 | Normalisation 1.0, frozen with hash lock | VERIFIED | evals/normalization.lock, backend/tests/unit/test_eval_normalization.py |
| 5 | Parsers: pdfium, RapidOCR, AutoParser | VERIFIED | backend/tests/unit/test_ocr_parser.py, docs/progress/logs/ci-local.txt |
| 5 | Schema-driven deterministic extractor | VERIFIED | backend/tests/unit/test_deterministic_rules.py, docs/progress/logs/ci-local.txt |
| 5 | Evidence provenance, feature builder, heuristic risk, routing | VERIFIED | backend/tests/unit/test_features.py, docs/progress/logs/ci-local.txt |
| 5 | JSON and CSV export functions | VERIFIED | backend/tests/e2e/test_vertical_slice.py |
| 5 | Replay cache, Ollama provider, LLM pass A with retry and fallback | VERIFIED | backend/tests/unit/test_llm.py, docs/progress/logs/run-llm-smoke.log, docs/progress/logs/run-llm-smoke-replay.log |
| 5 | LLM pass B, cross-pass agreement | NOT STARTED | Needed by S4 |
| 5 | Hosted providers through LiteLLM | NOT STARTED | Optional |
| 5 | Calibrators | NOT STARTED | Needs S2-S5 data |
| 7 | CORD v2 data, splits, layout groups | VERIFIED | evals/datasets/checksums/cord-v2.sha256, evals/splits/cord_v2/ |
| 7 | S1 on CORD test | VERIFIED | evals/results/cord_s1_v1.json, evals/results/cord_s1_v1.md, docs/progress/logs/run-cord-s1-test.log |
| 7 | Synthetic generator, five layouts, one held out | VERIFIED | backend/tests/unit/test_synthetic_layouts.py |
| 7 | Synthetic held-out evaluation | NOT STARTED | Generator ready, no runner yet |
| 7 | SROIE adapter and vendor split | VERIFIED | backend/tests/unit/test_sroie_adapter.py, evals/splits/sroie/vendor_groups.json |
| 7 | SROIE results | BLOCKED | Needs images and confirmed terms |
| 7 | S2-S5 | IN PROGRESS | Smoke run only. Order: review steps 1-4, then validation, then test once at the end. No test split LLM call has been made |
| 7 | Ablations, degradation | NOT STARTED | Follow S5 |
| 9 | Ollama recorded, default model chosen | VERIFIED | docs/progress/ENVIRONMENT.md, docs/adr/0011-default-extraction-model.md, evals/results/dev/llm_smoke_llama3.2-3b.json |
| 4 | Backend | NOT STARTED | Next |
| 6 | Frontend pages | NOT STARTED | |
| 8 | Testing and hardening | NOT STARTED | |
| 9 | Deployment | NOT STARTED | |
| 10 | Documentation | NOT STARTED | |
| 11 | Portfolio and publication preparation | NOT STARTED | |
| 12 | Final verification and report | NOT STARTED | |

## Acceptance criteria

| Id | Status | Note |
|---|---|---|
| A1 | NOT STARTED | Parsers handle PDF, scan and image; no upload API yet |
| A2 | VERIFIED | test_ocr_parser.py, test_pdfium_parser.py |
| A3 | IN PROGRESS | Default and alternative schemas work offline; Ollama works with cord_receipt only so far |
| A4 | IN PROGRESS | True in the pipeline for deterministic fields; not persisted yet |
| A5 | NOT STARTED | |
| A6 | IN PROGRESS | Export functions only |
| A7 | NOT STARTED | |
| A8 | NOT STARTED | |
| A9 | IMPLEMENTED BUT UNVERIFIED (local mirror; GitHub run pending human approval) | docs/progress/logs/ci-local.txt |
| A10 | NOT STARTED | |
| A11 | IN PROGRESS | S1 on CORD only; S2-S5 IN PROGRESS |
| A12 | IN PROGRESS | Groups saved; no grouped metric yet |
| A13 | NOT STARTED | Follows S5 |
| A14 | IN PROGRESS | Split hashes and overlap tests exist for CORD and SROIE; documented in docs/evaluation.md |
| A15 | NOT STARTED | |
| A16 | IN PROGRESS | No claims published yet |
| A17 | IN PROGRESS | Full-history scan clean, no trailers, nothing pushed; licence options not drafted |

## Blockers

| Blocker | Human action |
|---|---|
| S2-S5 cannot pass review steps 1-4: the text defining metrics 1.1, the S1 reproduction check and hygiene is not in this repository or the session | Paste that review |
| SROIE images and terms | Register at https://rrc.cvc.uab.es/?ch=13, read the terms in the download area, and say whether research use is allowed |
| DocILE, optional | Submit Rossum's access request form, or decide to skip it |
| CI on GitHub unverified | Approve creating a remote; nothing is pushed until then |
