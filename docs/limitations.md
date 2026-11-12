# Limitations

Research prototype evaluated on public datasets. Not validated for production use. No compliance certification.

This file grows as limitations are found.

## Deterministic values have no independent evidence

The deterministic extractor copies values from the tokens, so matching them against those tokens proves nothing. Such fields are recorded as `evidence_status: self_sourced` with `evidence_independent: false`, never `exact`, and the feature builder excludes them. Only a value from a different source, such as an LLM pass, gets a real match result. A `self_sourced` field shows where a value was read from, not that it is correct.

## LLM extraction quality on validation

With `llama3.2:3b` and prompts `a-1.0` and `b-1.0`, line items are poor: row-level F1 0.058 for S2, against 0.377 for rules. The model often omits quantity, lists summary lines such as `TOTAL` as items, and confuses columns. It also fills fields that are not printed, with false fill rates of about 0.7 to 0.8 on subtotal and tax. The evidence check cannot catch that, because the number it copies does appear in the document, in a different role. JSON validity is enforced by Ollama's schema constraint, so a high validity rate says nothing about whether values are right.

## Prompt 2.2 helps rows but stays below the rules on CORD

On validation, prompt 2.2 raised row F1 from 0.058 (S2) to 0.202 (S2'), and S4h reached 0.292, against 0.377 for S1. Total F1 fell from 0.814 (S2) to 0.719 (S2'). S4h is below S1 on every CORD field, though the total intervals overlap. Tax false fills stay high (0.57 to 0.76) because a printed number copied into the wrong field passes the evidence check. On synthetic invoices S2' transfers to the held-out layout where rules fail (total F1 1.000 against 0.000), but not for subtotal (0.000) and only partly for invoice number.

## Memory is the binding constraint

With `llama3.2:3b` loaded, free RAM on this machine drops to about 0.3 to 0.4 GiB during runs. Five runs aborted under the 0.4 GiB rule (prompt round, token measurement, two S4' attempts, synthetic S2'), and each was retried from the replay cache. A larger model would make this worse.

## SROIE: removed — official access unavailable; mirror terms unverified

The SROIE labels and vendor groups were deleted, and no SROIE metric exists. CORD has no vendor label, so no real vendor-grouped split was possible on any dataset. The A12 check uses derived CORD layout groups, which approximate layouts, not vendors.

## The application's risk score is unfitted; S5 exists only in the evaluation code

In the application (API, worker, review UI, export), `risk_score` is the hand-weighted heuristic in `backend/src/ledgerlens/confidence/risk.py`. It is not a probability, and routing uses it with a fixed threshold of 0.2. `calibrated_prob` is never set by the application and is always null. The S5 calibrators (logistic regression fitted on CORD train, thresholds set on validation) exist only in the evaluation code (`evals/s5.py`) and are not used by the application.

## Amount parsing

One separator followed by exactly three digits is read as thousands grouping (`45.000` is 45000). This suits Indonesian receipts and misreads three-decimal currencies.

## Rule-based extraction does not transfer to unseen wording

On the held-out synthetic layout, S1 scored F1 0.000 on vendor, invoice number, date, subtotal, tax and total, against about 1.000 on development layouts (`evals/results/synthetic_s1_v1_1.md`). Line items and currency held up because they do not depend on label wording. Development-layout scores mostly show fit to known wording.

## Currency scan false fills

The currency scan fills a value on layouts that print no currency: F1 0.000 on the `receipt` layout. The likely cause, unconfirmed, is item words that match ISO codes, such as "Try" or "Sar". It is left unfixed, because rules may not change after reading held-out results without a new protocol.

## Synthetic evaluation scope

The synthetic evaluation covers five single-page layouts. Rotated, low-DPI and multi-page variants exist in the generator but are outside this run.

## Parsing: native PDF text, with CPU OCR for images and scanned pages

The worker uses `AutoParser` (`backend/src/ledgerlens/parsing/ocr.py`). It reads embedded text from PDF pages that have it, and runs RapidOCR (ONNX Runtime, CPU) on images and on PDF pages without text. OCR quality was measured on CORD receipt photos and on rendered synthetic invoices only. The degradation study shows it falls sharply under strong blur (mean F1 0.681 to 0.446 for S1 at blur radius 3.0). Handwriting, rotated pages and multi-column documents were not evaluated.

## LLM mode inside Docker: not tested

The Compose stack was verified with the worker in its default rules mode: all five services were healthy, and the upload, review and export flow passed against it (`docs/progress/logs/run-docker-compose-up.log`, `run-e2e-docker.log`). The `llm` and `llm_or_rules` modes, which reach Ollama on the host from inside the container, were not tested in Docker. Networking is not the obstacle: the worker container reached Ollama on the host (version 0.40.15 through `host.docker.internal`). A smoke test (`scripts/docker_llm_smoke.py`, 3 CORD train documents, hard timeout) stopped at its free-RAM gate on 2026-11-12: 0.43 GiB free against the 2 GiB required, with Docker Desktop's VM holding about 4.7 GB (`docs/progress/logs/docker-llm-smoke.json`). On this 16 GB machine, Docker, the model and an editor do not fit together.

## S5 header precision targets were not met on test

On CORD test, the thresholds chosen on validation gave header precision below target. At the 0.98 target, S5-S1 reached 0.966 [0.906, 1.000] and S5-S4h 0.959 [0.891, 1.000]. At the 0.99 target, S5-S1 reached 0.966 and S5-S4h 0.976. Row units met their targets only for S5-S1, which accepted 3 of 253 rows; S5-S4h accepted no rows. Thresholds set on 100 validation documents do not hold their precision on new documents, and the intervals are wide (`evals/results/final/cord_s5_test_v1_1_1.md`).

## CORD v2 has near-duplicate documents across its official splits

Seven of the 100 test documents have identical OCR token text to a train or validation document: test 25, 28, 31, 33, 38, 44 and 75 (`docs/progress/logs/cord-cross-split-duplicates.txt`). The image bytes always differ. The gold labels are identical in 5 of the 7 pairs. Across all splits there are 17 such cross-split groups. The split checks compared document IDs only, so this was found after the final test read: 8 S2′ test replies were replayed from replies recorded for the train or validation twins. The test numbers are reported as read. They include these documents, so CORD test is not fully unseen data for the S5 calibrators (fitted on train) or the S1 rules (tuned on validation).

<!-- dedup-sensitivity:start -->
Duplicate-exclusion check (post hoc, `docs/evaluation/addendum-01-duplicate-sensitivity.md`): No S1-against-S4h ordering changes on any field (on the 93, S1 against S4h: total 0.775 against 0.825; subtotal 0.819 against 0.729; tax 0.727 against 0.475; row-level 0.330 against 0.216). There are also 10 train-validation and 22 within-split groups of near-copies, so validation choices rest partly on near-copies of train, and the bootstrap intervals are slightly optimistic. No clustered bootstrap was run.
<!-- dedup-sensitivity:end -->
