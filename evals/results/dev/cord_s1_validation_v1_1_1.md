# S1 on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s1_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `d4b2385e1529fa38f4ec4c63ebc669a4a4bebed7247ef3b0eb35187bcd507b18`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `cd5a82dd110fc7de48f048a4004ff3b0b22f4b74`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.867 [0.793, 0.934] | 0.796 [0.714, 0.876] | 0.830 [0.755, 0.899] | 0.000 [0.000, 0.000] |
| subtotal | 67 | 33 | 0.960 [0.896, 1.000] | 0.716 [0.606, 0.819] | 0.821 [0.734, 0.893] | 0.000 [0.000, 0.000] |
| tax_amount | 47 | 53 | 0.878 [0.771, 0.972] | 0.766 [0.644, 0.886] | 0.818 [0.711, 0.916] | 0.000 [0.000, 0.000] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 85 | 230 | 221 | 0.370 [0.286, 0.456] | 0.385 [0.301, 0.471] | 0.377 [0.296, 0.456] | 0.210 [0.140, 0.290] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.548 [0.460, 0.639] | 0.570 [0.473, 0.659] | 0.559 [0.474, 0.639] |
| quantity | 0.954 [0.895, 1.000] | 0.490 [0.387, 0.586] | 0.648 [0.549, 0.724] |
| unit_price | 1.000 [1.000, 1.000] | 0.060 [0.000, 0.143] | 0.113 [0.000, 0.250] |
| amount | 0.700 [0.608, 0.788] | 0.732 [0.639, 0.811] | 0.716 [0.638, 0.781] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 0. Truncated replies: 0.

## Verification

- Values output: 752.
- Not found in the document: 0.
- Withheld: 0.
- Rule failures (arithmetic): 111.
- Label proximity: 0 values next to a label for their field, 0 not.

## Latency and memory

Timings are measured in this run.

Power state of timings: ac (100 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing).

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Total per document: p50 2.55 s, p95 4.71 s (n=100). No model is used.
- Memory: peak process RSS 0.108 GiB, peak model runner RSS 0.042 GiB, lowest available system RAM 4.015 of 15.638 GiB.

Gold values excluded as unparsable: none.
