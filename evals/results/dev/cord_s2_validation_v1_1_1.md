# S2 on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s2_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `7626291638eea48de28bf545ba67090e318b2a04ab41c3a37f7bd706587d95e8`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `86cb81e4cf31b4c9f3e7679e06f7330c601fe9c5`, dirty: False.
- Rescored from saved predictions of `evals/results/dev/cord_s2_validation_v1_1.json`, with no rerun. Rescored at commit `65c1c75515c8a19cbc9592be359f3119817f9492`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.823 [0.742, 0.898] | 0.806 [0.724, 0.883] | 0.814 [0.736, 0.890] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.571 [0.473, 0.674] | 0.776 [0.671, 0.873] | 0.658 [0.562, 0.753] | 0.788 [0.643, 0.920] |
| tax_amount | 47 | 53 | 0.351 [0.246, 0.461] | 0.574 [0.431, 0.721] | 0.435 [0.319, 0.548] | 0.717 [0.596, 0.833] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 17 | 361 | 221 | 0.047 [0.018, 0.089] | 0.077 [0.029, 0.141] | 0.058 [0.022, 0.110] | 0.010 [0.000, 0.030] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.332 [0.240, 0.441] | 0.335 [0.241, 0.444] | 0.333 [0.248, 0.435] |
| quantity | 0.593 [0.482, 0.722] | 0.395 [0.283, 0.500] | 0.474 [0.366, 0.568] |
| unit_price | 0.188 [0.093, 0.333] | 0.480 [0.289, 0.646] | 0.270 [0.147, 0.415] |
| amount | 0.475 [0.400, 0.552] | 0.645 [0.537, 0.751] | 0.547 [0.477, 0.618] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 0. Truncated replies: 0.

## Verification

- Values output: 1072.
- Not found in the document: 31.
- Withheld: 0.
- Rule failures: 412.

## Latency and memory

Timings are recorded when the call was first made.

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 2.37 s, p95 7.31 s (n=98).
- Warm total per document: p50 5.26 s, p95 9.91 s (n=98).
- Cold documents: 2. Model load (s): [69.55, 7.33]. Cold LLM time excluding load (s): [58.07, 4.31].
- Memory, live run: peak process RSS 0.98 GiB, peak model runner RSS 1.888 GiB, lowest available system RAM 0.265 of 15.638 GiB.

Gold values excluded as unparsable: none.
