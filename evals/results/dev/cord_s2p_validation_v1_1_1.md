# S2' on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s2p_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `78c55da8f7945a73b767b9a97dcee05529172d0e397aab4f15c01e53ad8565a2`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `bda4ac504d3fb38271d6fbb67a77116316fa894d`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.734 [0.642, 0.819] | 0.704 [0.610, 0.794] | 0.719 [0.628, 0.802] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.841 [0.721, 0.941] | 0.552 [0.427, 0.672] | 0.667 [0.547, 0.770] | 0.091 [0.000, 0.200] |
| tax_amount | 47 | 53 | 0.493 [0.377, 0.608] | 0.766 [0.641, 0.884] | 0.600 [0.483, 0.704] | 0.566 [0.429, 0.702] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 65 | 422 | 221 | 0.154 [0.104, 0.208] | 0.294 [0.209, 0.381] | 0.202 [0.140, 0.267] | 0.060 [0.020, 0.110] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.361 [0.292, 0.436] | 0.661 [0.581, 0.732] | 0.467 [0.393, 0.543] |
| quantity | 0.543 [0.431, 0.651] | 0.600 [0.494, 0.706] | 0.570 [0.465, 0.667] |
| unit_price | 0.048 [0.000, 0.154] | 0.020 [0.000, 0.068] | 0.028 [0.000, 0.088] |
| amount | 0.501 [0.426, 0.578] | 0.823 [0.752, 0.885] | 0.623 [0.556, 0.686] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 0. Truncated replies: 0.

## Verification

- Values output: 1241.
- Not found in the document: 83.
- Withheld: 0.
- Rule failures (arithmetic): 188.
- Label proximity: 150 values next to a label for their field, 61 not.

## Latency and memory

Timings are mixed: 99 calls measured in this run, 1 recorded earlier (an aborted run or an earlier system) and replayed.

Power state of timings: ac (200 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing (audit replay)).

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 3.42 s, p95 6.61 s (n=99).
- Warm total per document: p50 6.32 s, p95 10.27 s (n=99).
- Cold documents: 1. Model load (s): [4.76]. Cold LLM time excluding load (s): [5.67].
- Memory: peak process RSS 0.113 GiB, peak model runner RSS 0.864 GiB, lowest available system RAM 2.994 of 15.638 GiB.

Gold values excluded as unparsable: none.
