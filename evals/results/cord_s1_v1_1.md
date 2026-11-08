# S1 on cord-v2 test (metrics 1.1)

Generated from `cord_s1_v1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `b8535d600517fdcf857f79ba0d27d839ae943afab3f4081761a78f29de562049`.
- Predictions sha256: `8b3fccde4d463e2d75c1f0ce007d2b34f256dfe60c5518a943b039cca9ab7e47`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `2ebea874cf18ad6a45289e4828e6238785faff67`, dirty: False.

## Single-valued fields

`exact_match` equals `recall` by definition under metrics 1.1; see docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | Exact match | False fill rate |
|---|---|---|---|---|---|---|---|
| total_amount | 95 | 5 | 0.873 [0.797, 0.940] | 0.726 [0.633, 0.813] | 0.793 [0.712, 0.866] | 0.726 [0.633, 0.813] | 0.200 [0.000, 0.667] |
| subtotal | 65 | 35 | 0.957 [0.887, 1.000] | 0.692 [0.574, 0.797] | 0.804 [0.713, 0.876] | 0.692 [0.574, 0.797] | 0.057 [0.000, 0.148] |
| tax_amount | 41 | 59 | 0.829 [0.686, 0.946] | 0.707 [0.562, 0.841] | 0.763 [0.622, 0.881] | 0.707 [0.562, 0.841] | 0.000 [0.000, 0.000] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 92 | 253 | 251 | 0.364 [0.261, 0.471] | 0.367 [0.261, 0.477] | 0.365 [0.263, 0.471] | 0.220 [0.140, 0.300] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.565 [0.479, 0.655] | 0.570 [0.484, 0.652] | 0.567 [0.484, 0.646] |
| quantity | 0.953 [0.903, 0.990] | 0.459 [0.343, 0.562] | 0.620 [0.503, 0.710] |
| unit_price | 1.000 [1.000, 1.000] | 0.045 [0.000, 0.123] | 0.086 [0.000, 0.220] |
| amount | 0.751 [0.674, 0.825] | 0.772 [0.697, 0.839] | 0.762 [0.698, 0.818] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 0. Truncated replies: 0.

## Verification

- Values output: 776.
- Not found in the document: 0.
- Withheld: 0.
- Rule failures (arithmetic): 98.

## Latency and memory

Timings are measured in this run.

Power state of timings: ac (100 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing (audit replay)).

- OCR: p50 2.56 s, p95 5.39 s (n=100).
- Total per document: p50 2.57 s, p95 5.39 s (n=100). No model is used.
- Memory: peak process RSS 0.0 GiB, peak model runner RSS 0.0 GiB, lowest available system RAM 2.564 of 15.638 GiB.

Gold values excluded as unparsable: none.
