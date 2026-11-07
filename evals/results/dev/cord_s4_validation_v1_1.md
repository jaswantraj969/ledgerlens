# S4 on cord-v2 validation (metrics 1.1)

Generated from `cord_s4_validation_v1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `76ef47e2beac9cfe9e18aa15a829506c9abd910490707e2ee1eaeb5faa1cea90`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `1c1f7655d09aa4309fe163fd8dce637b9877db09`, dirty: False.

## Single-valued fields

`exact_match` equals `recall` by definition under metrics 1.1; see docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | Exact match | False fill rate |
|---|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.830 [0.750, 0.900] | 0.847 [0.773, 0.918] | 0.838 [0.761, 0.909] | 0.847 [0.773, 0.918] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.609 [0.511, 0.707] | 0.836 [0.742, 0.919] | 0.704 [0.612, 0.790] | 0.836 [0.742, 0.919] | 0.788 [0.643, 0.920] |
| tax_amount | 47 | 53 | 0.400 [0.291, 0.513] | 0.681 [0.543, 0.816] | 0.504 [0.386, 0.618] | 0.681 [0.543, 0.816] | 0.660 [0.532, 0.790] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 16 | 357 | 221 | 0.045 [0.017, 0.085] | 0.072 [0.028, 0.130] | 0.055 [0.021, 0.102] | 0.010 [0.000, 0.030] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.336 [0.243, 0.448] | 0.335 [0.241, 0.444] | 0.336 [0.249, 0.438] |
| quantity | 0.594 [0.482, 0.722] | 0.390 [0.279, 0.495] | 0.471 [0.362, 0.567] |
| unit_price | 0.185 [0.094, 0.337] | 0.460 [0.282, 0.623] | 0.264 [0.148, 0.406] |
| amount | 0.497 [0.419, 0.579] | 0.645 [0.537, 0.751] | 0.561 [0.490, 0.633] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 1. Truncated replies: 1.

## Verification

- Values output: 1040.
- Not found in the document: 0.
- Withheld: 37.
- Rule failures: 422.

## Latency and memory

Timings are recorded when the call was first made.

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 4.73 s, p95 11.20 s (n=98).
- Warm total per document: p50 7.43 s, p95 14.79 s (n=98).
- Cold documents: 2. Model load (s): [69.6, 7.44]. Cold LLM time excluding load (s): [63.46, 8.12].
- Memory, live run: peak process RSS 0.971 GiB, peak model runner RSS 2.664 GiB, lowest available system RAM 0.253 of 15.638 GiB.

Gold values excluded as unparsable: none.
