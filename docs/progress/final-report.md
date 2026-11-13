# LedgerLens v1.0.0: final report (Phase 12)

Research prototype evaluated on public datasets. Not validated for production use.

Date: 2026-11-13. Licence: MIT. Pushed to a private GitHub repository after the release checks; nothing is public or published.

## 1. What was built

- **API** (FastAPI, PostgreSQL, Redis): upload with validation by content, deduplication per organisation, JWT and API-key authentication with roles, rate limits, review endpoints, a read-only audit trail per document, JSON and CSV export (one document, or up to 50 reviewed documents at once), signed webhooks, health and readiness probes.
- **Worker** (RQ): parses each document (native PDF text, or CPU OCR with RapidOCR) and extracts with rules by default, or with a local LLM (`llama3.2:3b` through Ollama). It verifies every value against the page, scores its risk, and routes it to review or acceptance. Steps are idempotent, with retries and a dead-letter queue.
- **Review UI** (React, served by Caddy): page image with evidence boxes, approve, reject or correct, the document's audit trail, a review queue, export of selected documents, and an evaluation page that shows the final test results.
- **Deployment:** Docker Compose with five services, all running as non-root users; quickstart through `scripts/init_env.py` and `scripts/tasks.sh up`.
- **Evaluation code** (`evals/`): CORD v2 and synthetic runners, metrics 1.1.1, S5 calibration and routing, ablations, degradation, power and integrity checks.

## 2. Evaluation protocol

- **Pre-registration:** the final CORD v2 test protocol was committed before any test access (`docs/evaluation/final-test-protocol.md`, commit `2550b14`).
- **Single read:** the 100 test documents were read once, by one unattended run, from a clean commit, on AC power only.
- **Run log:** `docs/progress/logs/final-run-20261112T073516Z.log` records EXIT=0, 18 of 18 steps, and 8 memory aborts, each resumed with the same command.
- **Integrity:** all 8 checks pass, again at release (`docs/progress/logs/final-integrity.txt`, `docs/progress/logs/release-reproduce.log`). They cover:
  - the S1 rerun reproducing its predictions hash;
  - 18 hash-checked done-markers;
  - AC power only;
  - the fixed settings;
  - the S5 thresholds equal to the ones chosen on validation.
- **Reproduction:** `make reproduce` regenerates all 30 files under `evals/results/final/` byte-identically (`docs/progress/logs/release-reproduce.log`).

## 3. Final results (CORD v2 test, n = 100 documents)

Every number below is copied from the file named under it. Intervals are 95% document-bootstrap intervals.

| System | Total F1 | Subtotal F1 | Tax F1 | Row-level F1 |
|---|---|---|---|---|
| S1 (rules) | 0.793 [0.712, 0.866] | 0.804 [0.713, 0.876] | 0.763 [0.622, 0.881] | 0.365 [0.263, 0.471] |
| S2′ (LLM, one pass) | 0.765 [0.684, 0.843] | 0.478 [0.341, 0.602] | 0.554 [0.430, 0.667] | 0.193 [0.121, 0.272] |
| S3′ (S2′ plus evidence check) | 0.773 [0.696, 0.849] | 0.484 [0.346, 0.606] | 0.564 [0.442, 0.679] | 0.192 [0.118, 0.272] |
| S4′ (two LLM passes plus rules) | 0.821 [0.747, 0.892] | 0.728 [0.633, 0.813] | 0.508 [0.393, 0.609] | 0.199 [0.126, 0.283] |
| S4h (hybrid, pre-registered) | 0.827 [0.753, 0.898] | 0.724 [0.627, 0.807] | 0.508 [0.393, 0.609] | 0.253 [0.168, 0.343] |

Source: `evals/results/final/cord_test_comparison_v1_1_1.md`.

### S5 routing (variant all)

| System | Target | Header automation | Header precision | Row automation | Row precision |
|---|---|---|---|---|---|
| S5-S1 | 0.98 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000] | 0.012 [0.000, 0.033] (3 / 253) | 3 / 3 correct, exact 95% CI [0.292, 1.000] |
| S5-S1 | 0.99 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000] | 0.012 [0.000, 0.033] (3 / 253) | 3 / 3 correct, exact 95% CI [0.292, 1.000] |
| S5-S4h | 0.98 | 0.163 [0.120, 0.210] (49 / 300) | 0.959 [0.891, 1.000] | 0.000 (0 / 422) | none accepted |
| S5-S4h | 0.99 | 0.140 [0.097, 0.183] (42 / 300) | 0.976 [0.917, 1.000] | 0.000 (0 / 422) | none accepted |

Source: `evals/results/final/cord_s5_test_v1_1_1.md`.

- **Header precision:** every point estimate is below its target, and every interval contains the target.
- **Line items** are effectively routed to human review.
- **Unseen layout groups (37 documents):** S5-S1 accepts 14 of 111 header slots and S5-S4h 9 of 111, all correct. The exact 95% intervals are [0.768, 1.000] and [0.664, 1.000], so "target met" at these sizes is not evidence that the target holds.
- **Review workload per document** (`evals/results/final/cord_s5_review_workload_v1_1_1.json`):
  - S5-S1: 4.920 [4.370, 5.480] slots routed, a 0.890 share;
  - S5-S4h at 0.98: 6.730 [6.080, 7.570], a 0.932 share.

### Ablations (S5, header, target 0.98)

| Base | Change | Test automation | Note |
|---|---|---|---|
| S5-S1 | isotonic calibrator | 0.297 [0.237, 0.360] | Precision 0.944 [0.887, 0.989] |
| S5-S4h | without the format and validation checks | 0.000 | No validation threshold met the target |
| S5-S4h | isotonic calibrator | 0.180 [0.137, 0.230] | Precision 0.981 [0.936, 1.000] |

Source: `evals/results/final/cord_s5_ablations_test_v1_1_1.md`.

### Degradation (mean of four F1)

| Condition | S1 | S4h |
|---|---|---|
| Clean | 0.681 | 0.578 |
| Blur radius 3.0 | 0.446 | 0.399 |
| JPEG quality 10 | 0.545 | 0.483 |

S4h is above S1 on total F1 in all five conditions. Source: `evals/results/final/cord_degradation_test_v1_1_1.md`.

### Synthetic invoices (held-out layout)

The rules score 0.000 on six header fields; S2′ recovers four of them. Sources:
- `evals/results/synthetic_s1_v1_1_1.md`
- `evals/results/synthetic_s2p_v1_1_1.md`

S3 to S5 were not run on synthetic data (ADR-0013).

## 4. Addendum 01: duplicate exclusion (post hoc)

**Registration:**
- 7 test documents have near-copies in train or validation (`docs/progress/logs/cord-cross-split-duplicates.txt`).
- A check excluding them was registered in `docs/evaluation/addendum-01-duplicate-sensitivity.md` (commit `a1ec84e`, 15:31:47 UTC) before it was computed (`1faa328`, 15:32:59 UTC).

**Results:**

| On the 93 documents | S1 | S4h |
|---|---|---|
| Total F1 | 0.775 | 0.825 |
| Subtotal F1 | 0.819 | 0.729 |
| Tax F1 | 0.727 | 0.475 |
| Row-level F1 | 0.330 | 0.216 |

No S1-against-S4h ordering changes on any field. Source: `evals/results/final/cord_test_dedup_sensitivity_v1_1_1.md`. The primary results are unchanged.

## 5. Limitations (summary; full list in `docs/limitations.md`)

- **The LLM does not beat the tuned rules on CORD.** Line items are effectively not automated.
- **Header precision at the 0.98 and 0.99 targets was not confirmed on test.** About 50 accepted values per configuration cannot confirm or rule out the target.
- **CORD has near-duplicates across its official splits:**
  - 7 test documents;
  - 10 train-validation groups;
  - 22 groups within a single split.

  So the bootstrap intervals are slightly optimistic.
- **The application's `risk_score` is a hand-weighted heuristic.** The S5 calibrators exist only in the evaluation code.
- **Evaluation scope:** OCR was measured on CORD receipt photos and rendered synthetic invoices only. The synthetic evaluation covers S1 and S2′ only.
- **Memory:** this machine's RAM limited every LLM run. The final read had 8 memory aborts, all resumed with the same command.

## 6. Security review (summary; full table in `docs/security-review.md`)

| Status | Items |
|---|---|
| Pass | Authentication on every non-public route; upload size, type-by-content and page limits; path traversal; HMAC signing; rate limits; secrets scan; npm audit |
| Fixed | Image pixel limit; webhook replay window; allow-list for public webhook addresses; non-root web container; `/api/metrics` off the proxy; unused `litellm` extra with a known CVE |
| Risk accepted | Open registration (isolated organisations); DNS rebinding window; login limited per email, not per IP |

## 7. Test counts at release

| Suite | Result | Log |
|---|---|---|
| Backend pytest (with PostgreSQL and Redis) | 503 passed; core coverage 96% | `docs/progress/logs/release-ci-local.log` |
| Frontend Vitest | 43 passed | `release-ci-local.log` |
| Lint, type check (mypy over backend and evals, 107 files), oxlint, frontend build, pre-commit hooks, eval-smoke, gitleaks over the full history | all pass | `release-ci-local.log` |
| Playwright upload, review (correction checked in the audit trail) and export against Docker Compose | 1 passed | `docs/progress/logs/release-fresh-clone.log` |
| Fresh clone following the README (attempt 2) | every step passes; tracked tree unchanged after the run | `release-fresh-clone.log` |
| GitHub Actions on the private repository, at v1.0.0 | backend, frontend and secrets jobs succeeded; 503 and 43 tests | `docs/progress/logs/release-ci-github.txt` |
| Linux simulation of the CI workflow (at 6b0e402, before the audit trail and batch export) | backend 493 passed, frontend 37 passed, gitleaks clean | `docs/progress/logs/release-ci-linux-simulation.log` |

## 8. Not verified

- **LLM mode inside Docker.** The worker container reaches Ollama on the host, but the smoke test stopped at its 2 GiB free-RAM gate (`docs/progress/logs/docker-llm-smoke.json`). `scripts/run_docker_llm_smoke.ps1` is ready for a run with other applications closed.
- **Test-split replay (A13, verified in scope).** `make reproduce` regenerates all 30 final files byte-identically from the saved result files. Replaying the test runs themselves needs the CORD caches, which are gitignored by design, so a fresh clone cannot replay them.
