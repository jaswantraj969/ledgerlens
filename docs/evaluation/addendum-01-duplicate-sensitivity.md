# Addendum 01: duplicate-exclusion sensitivity check (post hoc)

Written and committed on 2026-11-12, before any number in this check has been computed. It adds to `docs/evaluation/final-test-protocol.md` (commit `2550b14`) and changes nothing in it.

## Why
After the final test read, a check found that 7 of the 100 CORD test documents have OCR token text identical to a train or validation document (`docs/progress/logs/cord-cross-split-duplicates.txt`, commit `bea277b`). This analysis is **post hoc**: it was added after the final read because of that finding. It was not part of the pre-registered protocol.

## Status of the primary results
The primary results in `evals/results/final/` are unchanged. This check is reported beside them, never instead of them. No result file written by the final read is modified.

## Exclusion set
Exactly these 7 test documents, the test members of the "identical token text" groups in `cord-cross-split-duplicates.txt`:

`cord-v2:test:25`, `cord-v2:test:28`, `cord-v2:test:31`, `cord-v2:test:33`, `cord-v2:test:38`, `cord-v2:test:44`, `cord-v2:test:75`.

No other document is excluded, and the set does not change after any number is seen.

## What is computed
From the saved test predictions and per-field records only (`data/cord-v2/predictions/*_test.json`, `data/cord-v2/records/*_test.json`), with the test gold labels:

1. **S1, S2′, S3′, S4′ and S4h** on the 93 remaining documents:
   - total, subtotal and tax F1, and row-level F1, under metrics 1.1.1;
   - 95% document-bootstrap intervals (2,000 resamples, seed 20261106), with n = 93.
2. **S5-S1 and S5-S4h** (variant all) on the 93 remaining documents, at targets 0.98 and 0.99:
   - header and row automation rate, and achieved precision, each with document-bootstrap intervals;
   - an exact Clopper-Pearson 95% interval for precision where fewer than 30 values were accepted.

   The calibrators are fitted on train exactly as in `evals/runners/run_s5.py`. The thresholds are the ones recorded in `evals/results/cord_s5_{s1,s4h}_v1_1_1.json`, and the recomputed accepted counts on all 100 documents must equal those files' counts before any subset is scored.
3. **For information:** per-system field F1 and row F1 on the 7 excluded documents alone. No intervals are computed; with 7 documents they would not be informative.

## What is not allowed
- No LLM call.
- No calibrator refit beyond reproducing the recorded one.
- No threshold, rule, prompt or setting change.
- No change to any existing result file.
- No clustered or re-weighted bootstrap.

## Outputs
- `evals/results/final/cord_test_dedup_sensitivity_v1_1_1.json` and `.md`, written by `evals/runners/dedup_sensitivity.py`.
- Log: `docs/progress/logs/run-dedup-sensitivity.log`.
- One README paragraph and one limitations line, with numbers taken from that file. They state whether any S1-against-S4h ordering on any field changes.

## Known related facts, stated in advance
Under the same "identical token text" definition, `cord-cross-split-duplicates.txt` also lists 10 train–validation groups and 22 groups within a single split. So validation choices (S1 rule tuning, prompt checks, S5 thresholds) were made partly on near-copies of train documents, and the document-bootstrap intervals, which treat documents as independent, are slightly optimistic. This addendum does not correct for either.
