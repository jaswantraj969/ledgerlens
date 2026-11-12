# S4' on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s4p_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `d843e68ea12fa5f82ce61cc3e1636ff08399fbcfa7a2eb5e8a24a64ef5f8cdd9`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `b77d0b81fcaf7ccdc3176e05699920e688885adb`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.830 [0.747, 0.904] | 0.796 [0.714, 0.878] | 0.812 [0.734, 0.888] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.640 [0.541, 0.739] | 0.851 [0.761, 0.930] | 0.731 [0.639, 0.812] | 0.788 [0.636, 0.925] |
| tax_amount | 47 | 53 | 0.458 [0.346, 0.568] | 0.809 [0.687, 0.911] | 0.585 [0.472, 0.691] | 0.717 [0.596, 0.836] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 65 | 412 | 221 | 0.158 [0.106, 0.214] | 0.294 [0.209, 0.381] | 0.205 [0.142, 0.271] | 0.060 [0.020, 0.110] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.377 [0.306, 0.457] | 0.661 [0.581, 0.732] | 0.480 [0.406, 0.557] |
| quantity | 0.592 [0.474, 0.706] | 0.581 [0.476, 0.687] | 0.587 [0.480, 0.688] |
| unit_price | 0.048 [0.000, 0.154] | 0.020 [0.000, 0.068] | 0.028 [0.000, 0.088] |
| amount | 0.525 [0.447, 0.602] | 0.823 [0.752, 0.885] | 0.641 [0.574, 0.704] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 1. Truncated replies: 1.

## Verification

- Values output: 1225.
- Not found in the document: 0.
- Withheld: 109.
- Rule failures (arithmetic): 489.
- Label proximity: 176 values next to a label for their field, 117 not.

## Latency and memory

Timings are mixed: 14 calls measured in this run, 187 recorded earlier (an aborted run or an earlier system) and replayed.

Power state of timings: ac (301 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing (audit replay)).

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 7.68 s, p95 14.05 s (n=97).
- Warm total per document: p50 10.43 s, p95 17.93 s (n=97).
- Cold documents: 3. Model load (s): [4.82, 6.93, 6.74]. Cold LLM time excluding load (s): [11.89, 8.75, 9.19].
- Memory: peak process RSS 0.113 GiB, peak model runner RSS 2.078 GiB, lowest available system RAM 3.289 of 15.638 GiB.

Gold values excluded as unparsable: none.
