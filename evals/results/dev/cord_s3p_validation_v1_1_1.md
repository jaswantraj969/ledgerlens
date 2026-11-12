# S3' on cord-v2 validation (metrics 1.1.1)

Generated from `cord_s3p_validation_v1_1_1.json`. Do not edit by hand.

- Documents: 100. Workers: 1.
- Metrics 1.1.1, normalisation 1.0 (sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`).
- Schema: cord_receipt 1.1.0. Split sha256: `e809a1edf8320960479a1f79e7e2c086aaca4793dbf9c91fc354eaca2c656852`.
- Predictions sha256: `49c3f8652abde2a0a2b72f297bb229c9b938c4c39db3afbed574895c0e7eb0ae`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Commit: `bda4ac504d3fb38271d6fbb67a77116316fa894d`, dirty: False.

## Single-valued fields

Exact match is not shown: for single-valued fields it equals recall. It stays in the JSON, flagged redundant. See docs/evaluation.md.

| Field | n present | n absent | Precision | Recall | F1 | False fill rate |
|---|---|---|---|---|---|---|
| total_amount | 98 | 2 | 0.793 [0.701, 0.875] | 0.704 [0.610, 0.794] | 0.746 [0.656, 0.825] | 1.000 [1.000, 1.000] |
| subtotal | 67 | 33 | 0.974 [0.914, 1.000] | 0.552 [0.427, 0.672] | 0.705 [0.589, 0.800] | 0.000 [0.000, 0.000] |
| tax_amount | 47 | 53 | 0.554 [0.429, 0.677] | 0.766 [0.641, 0.884] | 0.643 [0.524, 0.748] | 0.434 [0.306, 0.571] |

## Line items, row level (primary)

| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 | Documents with all rows correct |
|---|---|---|---|---|---|---|
| 65 | 410 | 221 | 0.159 [0.107, 0.215] | 0.294 [0.209, 0.381] | 0.206 [0.142, 0.271] | 0.060 [0.020, 0.110] |

## Line items, set-based (secondary)

Secondary score, set-based, ignores row alignment.

| Cell | Precision | Recall | F1 |
|---|---|---|---|
| description | 0.377 [0.306, 0.457] | 0.661 [0.581, 0.732] | 0.480 [0.406, 0.557] |
| quantity | 0.592 [0.474, 0.706] | 0.581 [0.476, 0.687] | 0.587 [0.480, 0.688] |
| unit_price | 0.048 [0.000, 0.154] | 0.020 [0.000, 0.068] | 0.028 [0.000, 0.088] |
| amount | 0.528 [0.449, 0.606] | 0.823 [0.752, 0.885] | 0.643 [0.576, 0.705] |

## Failures

- Crashes: 0.
- Failed extractions (scored as empty): 0.
- Documents with a fallback: 0. Pass fallbacks: 0.
- Retries: 0. Truncated replies: 0.

## Verification

- Values output: 1147.
- Not found in the document: 0.
- Withheld: 94.
- Rule failures (arithmetic): 188.
- Label proximity: 150 values next to a label for their field, 61 not.

## Latency and memory

Timings are recorded when the call was first made.

Power state of timings: ac (200 on AC, 0 on battery, 0 unknown; cache file modification time per recorded timing (audit replay)).

- OCR: p50 2.55 s, p95 4.71 s (n=100).
- Warm LLM, load excluded: p50 3.42 s, p95 6.61 s (n=99).
- Warm total per document: p50 6.25 s, p95 10.17 s (n=99).
- Cold documents: 1. Model load (s): [4.76]. Cold LLM time excluding load (s): [5.67].
- Memory: peak process RSS 0.112 GiB, peak model runner RSS 0.864 GiB, lowest available system RAM 3.31 of 15.638 GiB.

Gold values excluded as unparsable: none.
