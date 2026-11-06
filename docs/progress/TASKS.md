# Tasks

Labels: NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED BUT UNVERIFIED, VERIFIED.

| Phase | Task | Status | Evidence |
|---|---|---|---|
| 1 | Environment inspection | VERIFIED | docs/progress/logs/environment.txt |
| 2 | Tasks, criteria, ADRs, architecture | IN PROGRESS | ADR-0002 awaits the Docling result |
| 3 | Backend scaffold, lockfile, Compose services | VERIFIED | docs/progress/logs/phase3-checks.txt |
| 3 | Frontend scaffold and first test | VERIFIED | docs/progress/logs/phase3-frontend.txt |
| 3 | pre-commit hooks | VERIFIED | docs/progress/logs/phase3-precommit.txt |
| 3 | CI workflow | IMPLEMENTED BUT UNVERIFIED | cannot run: no remote by design (R8); same checks run locally |
| 4 | Backend | NOT STARTED | |
| 5 | Normalisation module v1.0.0 | VERIFIED | docs/progress/logs/phase3-checks.txt (47 tests) |
| 5 | Native PDF parser (pdfium) | VERIFIED | docs/progress/logs/phase5-parser-checks.txt |
| 5 | Offline slice: schemas, deterministic extractor, evidence, arithmetic, heuristic risk, routing, JSON/CSV export | VERIFIED | docs/progress/logs/phase5-slice-checks.txt, docs/progress/logs/phase5-mutation-check.txt |
| 5 | OCR parser, LLM extractor, replay cache, calibrators | NOT STARTED | |
| 6 | Frontend | NOT STARTED | |
| 7 | CORD v2 downloaded, hashes verified, labels mapped | VERIFIED | evals/datasets/checksums/cord-v2.sha256, evals/datasets/LICENSES.md |
| 7 | Synthetic generator, single template | IMPLEMENTED BUT UNVERIFIED | used by e2e tests; edge cases (rotation, low DPI, noise) missing |
| 7 | Rest of evaluation framework and runs | NOT STARTED | |
| 8 | Testing and hardening | NOT STARTED | |
| 9 | Deployment | NOT STARTED | |
| 10 | Documentation | NOT STARTED | |
| 11 | Portfolio and publication preparation | NOT STARTED | |
| 12 | Final verification and report | NOT STARTED | |

## Blockers
- Docling install not yet completed: two attempts failed or hung on the network, so ADR-0002 is still Proposed.
- Ollama binary missing (install directory gone, models remain). S2-S5 need a working local model.
- DocILE needs a human access request. Not yet requested.
