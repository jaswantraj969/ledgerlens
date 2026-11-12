# S4h on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s4h_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `7980db7027534b352ff83df6c4c963ae5c74355bfec513f1695e12adbf9a1ee1`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `b77d0b81fcaf7ccdc3176e05699920e688885adb`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.832 [0.750, 0.905] | 0.806 [0.727, 0.888] | 0.819 [0.741, 0.893] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.637 [0.538, 0.733] | 0.866 [0.778, 0.940] | 0.734 [0.645, 0.814] | 0.818 [0.684, 0.941] |
| tax_amount | 47 | 53 | 0.447 [0.337, 0.557] | 0.809 [0.687, 0.911] | 0.576 [0.465, 0.681] | 0.755 [0.638, 0.868] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 84 | 354 | 221 | 0.237 [0.171, 0.306] | 0.380 [0.293, 0.466] | 0.292 [0.219, 0.367] | 0.180 [0.110, 0.260] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.433 [0.353, 0.516] | 0.692 [0.610, 0.772] | 0.533 [0.455, 0.609] |
| quantity | 0.700 [0.592, 0.802] | 0.633 [0.539, 0.721] | 0.665 [0.578, 0.743] |
| unit_price | 0.182 [0.000, 0.500] | 0.040 [0.000, 0.106] | 0.066 [0.000, 0.164] |
| amount | 0.600 [0.519, 0.681] | 0.832 [0.754, 0.894] | 0.697 [0.629, 0.758] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 1. Truncated replies: 1.

## Verification

- Values output: 1139.
- Not found in the document: 38.
- Withheld: 0.
- Rule failures (arithmetic): 407.
- Label proximity: 24 values next to a label for their field, 91 not.

## Latency and memory

Timings are recorded when the call was first made.

Power state of timings: ac (301 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing (audit replay)).

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 7.68 s, p95 14.05 s (n=97).
- Warm total per document: p50 10.43 s, p95 17.94 s (n=97).
- Cold documents: 3. Model load (s): [4.82, 6.93, 6.74]. Cold LLM time excluding load (s): [11.89, 8.75, 9.19].
- Memory: peak process RSS 0.113 GiB, peak model runner RSS 2.078 GiB, lowest available system RAM 3.285 of 15.638 GiB.

Gold values excluded as unparsable: none.
