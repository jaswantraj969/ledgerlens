# Evaluation protocol

This protocol is committed before any CORD metric is computed. Git history records the order. Any change after results exist is listed under "Changes after first results".

## Normalisation

`evals/normalization.py` defines correctness and is frozen at version 1.0. Its SHA-256 fingerprint is stored in `evals/normalization.lock` and recorded in every results file. A test fails if the rules change.

Money formats were checked on the CORD **train** split only, which exposed parser bugs on `Rp. 57.000` and `39,200,00`. These were fixed before the freeze.

## CORD v2 splits

Official files are used unchanged: train 800, validation 100, test 100. Document IDs have the form `cord-v2:<split>:<image_id>`. `evals/splits/cord_v2/ids.json` stores each list with the SHA-256 of its sorted IDs.

- **train:** fitting, including the layout groups below.
- **validation:** rule tuning, recorded in the tuning log below.
- **test:** read once per reported configuration. The runner refuses to overwrite an existing test result.

## CORD layout groups

CORD has no vendor identifier, so groups are derived and approximate a layout, not a vendor.

1. Descriptor per document: the share of annotated word boxes whose centre falls in each cell of a grid 4 columns wide and 6 rows high, normalised by image size, plus image aspect ratio. Word positions only; no word text and no field labels.
2. Grouping: k-means with k=12, `n_init=10`, `random_state=20261106`, fitted on **train only**.
3. Validation and test documents join the nearest train centroid.

k=12 was set in advance and is not tuned. Assignments are in `evals/splits/cord_v2/layout_groups.json`. These groups are the only A12 check available, because SROIE is blocked.

## SROIE

**SROIE: removed — official access unavailable; mirror terms unverified.** The local labels and the committed vendor-group file were deleted on 2026-11-07 in a normal commit; history was not rewritten. The adapter in `evals/datasets/sroie.py` remains, tested on fictional fixtures only, for the case where official access appears. No SROIE metric was ever computed. See `evals/datasets/LICENSES.md`.

## Mapped fields

| Field | CORD label |
|---|---|
| total_amount | `total.total_price` |
| subtotal | `sub_total.subtotal_price` |
| tax_amount | `sub_total.tax_price` |
| line_items.amount | `menu.price` |
| line_items.description | `menu.nm` |
| line_items.quantity | `menu.cnt` |
| line_items.unit_price | `menu.unitprice` |

A label holding only `-` counts as absent. vendor_name, invoice_number, invoice_date and currency are not evaluated on CORD.

## Metrics (version 1.1.1)

Metrics 1.1.1 is current. It is metrics 1.1 with one change in presentation: for single-valued fields, `exact_match` is numerically equal to `recall` (shown below), so it is dropped from tables. It stays in results files, beside `exact_match_redundant`, which says so. No count, rate or interval changes. Results under 1.1 were rescored to 1.1.1 from their saved predictions, with no pipeline rerun, by `evals/runners/rescore.py`, which checks the predictions hash and that every number matches the 1.1 file. The 1.1 files are kept.

Metrics 1.1 replaced 1.0 for all new results, and every results file records its version. Normalisation stays at 1.0. `evals/results/cord_s1_v1.json` is kept for history under 1.0 definitions.

Below, `pred` and `gold` are normalised values for one document, and `D` is the set of documents. A gold value that does not normalise counts as absent, and is reported in `gold_values_excluded_unparsable`.

### Single-valued fields

Per document:

| Case | Condition | Counts as |
|---|---|---|
| Correct | gold present, `pred == gold` | TP |
| Wrong | gold present, pred present, `pred != gold` | FP and FN |
| Missed | gold present, pred absent | FN |
| False fill | gold absent, pred present | FP |
| Correctly empty | gold absent, pred absent | nothing |

- `n_present = |{d in D : gold present}|`, and `n_absent = |D| - n_present`
- `precision = TP / (TP + FP)`, null if the denominator is 0
- `recall = TP / (TP + FN)`, null if the denominator is 0
- `F1 = 2TP / (2TP + FP + FN)`, null if the denominator is 0
- `exact_match = TP / n_present`, null if `n_present = 0`
- `false_fill_rate = false fills / n_absent`, null if `n_absent = 0`

Every gold-present document is TP or FN, so `TP + FN = n_present`, which makes `exact_match` numerically equal to `recall` here. Both are kept because they are read differently. Under 1.0, exact match also counted correctly-empty documents, which is why values under the two versions are not comparable.

### Line items: row level (primary)

Each row has cells `description`, `quantity`, `unit_price` and `amount`. For gold row `g` and predicted row `p`:

- `L(g)` is the set of cells `g` labels. Gold rows with empty `L(g)` are not scored. Predicted cells outside `L(g)` are ignored, because CORD leaves `unit_price` unlabelled on most rows.
- `share(p, g) = |{c in L(g) : p[c] == g[c]}| / |L(g)|`
- `full(p, g)` holds when `share(p, g) = 1`
- `weight(p, g) = share(p, g) + 1000 * full(p, g)`

Rows are matched one to one per document by the Hungarian algorithm, maximising total weight. The factor of 1000 means full matches are maximised first. Then, pooled over documents:

- `C` = assigned pairs with `full(p, g)`
- `row_precision = C / predicted rows`, null if there are none
- `row_recall = C / gold rows`, null if there are none
- `row_F1 = 2C / (predicted rows + gold rows)`, null if both are 0
- `documents_all_rows_correct` = share of documents with gold rows where `C = predicted rows = gold rows`

### Line items: set-based (secondary)

Labelled "set-based, ignores row alignment". Per document and per cell type, predicted and gold values are compared as multisets, under the 1.0 formulas: TP is the size of the multiset intersection, and FP and FN are the remainders, pooled over documents. Its `exact_match` is the share of all documents with equal multisets. Correct values on the wrong row score full marks, so this must not be read as row accuracy.

### Failed extractions

For S2 to S5, a document where the model failed and the rule-based fallback ran is a failed extraction. Its predictions are empty, so its gold values count as FN and it earns no credit. Fallback counts are reported separately. `evals/scoring.py` enforces this, with a test.

### Intervals

95% percentile bootstrap, 2000 resamples of **documents**, seed 20261106. A rate undefined on a resample is skipped for that resample.

### Latency

Cold start and warm running are reported separately.

- **Model load:** Ollama's `load_duration`, a number of its own.
- **Cold document:** the first document of a run that loaded the model, as measured.
- **Warm per-document latency:** LLM time with load time subtracted, over the remaining documents, as p50 and p95.
- Replayed runs report recorded times and say so.

Runs use one worker and no parallel model calls. Each run logs peak process memory and lowest free system RAM.

## Systems

Fixed before S2, S3 and S4 were first run.

- **S1:** RapidOCR, then the deterministic extractor. It needs no LLM.
- **S2:** LLM pass A (field-guided), with values as returned.
- **S3:** S2 plus verification. A value is withheld, and so counts as no prediction, if it does not parse or if the independent evidence check does not find it in the document. Arithmetic results are reported but withhold nothing, because a failed sum does not show which field is wrong.
- **S4:** pass A, pass B (document-guided) and the deterministic extractor, merged by normalised agreement. The most-agreed value wins, and a tie goes to the earliest of pass A, pass B, rules. Rows come from the first LLM pass that produced rows. The S3 check then applies. A failed pass is an empty source, and the document is a failed extraction only if both passes fail. Partial failures are counted as pass fallbacks.
- **S5:** S4 plus a calibrator and thresholds. Not built yet.

## Pre-registered on 2026-11-07, before any result below exists

Written and committed before S2', S3', S4', S4h or S5 has produced a number. Nothing in this section changes after a result is seen; a change would be a new, separately named system.

### Prompt round (S2', S3', S4')

- Development set: 100 CORD **train** documents, `evals/splits/cord_v2/prompt_dev_train100.json` (seed 20261107, sha256 `ff174afe618302ac1af5dffeb750ccde6268af8187bd408d4009d2b1ff06e847`). Validation is not used to develop prompts.
- One round, with at most three candidates, each a revision of both pass A and pass B with the same changes. Candidates are scored as S2 (pass A, as returned) on the development set under metrics 1.1.1. The final prompt is the candidate with the highest mean of the four F1 values (total, subtotal, tax, row-level), ties to the shorter prompt. Prompt `a-1.0`/`b-1.0` is scored the same way as the reference.
- The final prompt is then evaluated once on validation as S2', S3' and S4', defined as S2, S3 and S4 with that prompt. No further prompt change follows the validation read.
- `num_ctx` is the smallest multiple of 256 that holds the longest CORD prompt (all splits; input only, no labels) plus `num_predict`. It is measured with the final prompt before the validation read.

### Label proximity check

A monetary header field (total, subtotal, tax) is **label-supported** if a token sequence matching its value lies on the same line as a label keyword for that field, or on the line directly above or below it. Lines and keywords come from the parsed document only. Keywords are configured per field in the schema, and include Indonesian terms (`PB1`, `PPN`, `Pajak`, `Service`, `Subtotal`, `Total`). It is a verification result and a confidence feature. It changes no extracted value, and S3' withholds by the S3 rule only.

### S4h (hybrid)

For each single-valued field:

1. If the deterministic extractor produced a value and it equals (after normalisation) the value of pass A or pass B, take the deterministic value.
2. Otherwise take an LLM value from pass A or B, among those that parse and are found by the independent evidence check. Rank them by support: +1 if label-supported, +1 if pass A and pass B agree on it. Highest support wins; a tie goes to pass A.
3. Otherwise null.

For line items, as one unit: take the deterministic rows if there is at least one, and at least one of them equals (all four cells, normalised) a row from pass A or pass B. Otherwise take the rows of the LLM pass with more rows whose description is found by the independent evidence check, tie to pass A. Otherwise no rows.

Deterministic-versus-LLM agreement is a feature with both sources independent (`agree_rules_llm`): the rule value comes from regular expressions over OCR tokens and the LLM value from the model, so agreement is not circular. A failed LLM pass is an empty source, as in S4. S4h uses the final prompt and is evaluated once on validation.

### S5 (calibrated routing)

- **Base system:** S4h. Chosen now, before any S4h or S4' result, because it is the system whose records carry every independent source.
- **Units:** each single-valued header field slot with a predicted value, and each predicted line-item row. A slot without a value always goes to review and counts against automation.
- **Label:** a header unit is correct if its normalised value equals gold. A row unit is correct if the metrics 1.1.1 row assignment matches it to a gold row with all scored cells equal.
- **Features:** `build_features` only, including label support, A/B agreement and rule/LLM agreement. Dependent evidence matches stay excluded.
- **Calibrator:** logistic regression (scikit-learn, L2, C=1.0, a one-hot field name), one for header units and one for row units. Fitted on S4h predictions for **CORD train** (800 documents). Nothing else is tuned.
- **Thresholds:** for target precision 0.98 and 0.99, the lowest calibrated-probability threshold on a 0.001 grid at which precision of accepted units on **validation** is at least the target. If no threshold reaches it, nothing is auto-accepted at that target.
- **Test:** read once at the end, with S1 to S5 together, from a clean commit.
- **Reported, on test:** automation rate (auto-accepted units over all units, header slots counted whether or not filled) at each target, with achieved precision and 95% document-bootstrap intervals, reported even when the target is not met. Also ECE (10 equal-width bins), Brier score and ROC-AUC of the calibrated probabilities on test. The word "calibrated probability" is used only for these outputs.
- **Layout-group-held-out variant:** `evals/splits/cord_v2/layout_group_holdout.json`, written before any S5 result. Groups 6, 7, 9 and 10 are evaluation groups and the other eight are calibration groups. The calibrator is fitted on train documents in calibration groups (540), thresholds are chosen on validation documents in calibration groups (74), and results are reported on test documents in evaluation groups (37), next to the test documents in calibration groups (63). Only the calibrator and thresholds are group-held-out. The rules and prompts were developed on documents from every group, and 37 documents give wide intervals. This is the only A12 generalisation result available.

## Synthetic evaluation

Fixed before the held-out layout was first run through extraction.

- Layouts: `classic`, `modern`, `receipt` and `statement` are development layouts. `ledger` is held out. Its wording appears in no schema, and a test enforces that.
- Documents: seeds from 700000, 40 per layout on the native PDF route and 20 per layout on the OCR route. The same seeds are used for each layout. All are single-page with 1 to 8 items, and rotated and low-DPI variants are not included in this run.
- Schema: `default`, unchanged. No rule may be changed after reading held-out results.
- Reported: per-layout metrics 1.1, plus F1 pooled across development layouts against F1 on the held-out layout, with the gap.

Synthetic results are reported separately and are never presented as real-dataset results.

## Tuning log

Entries are added as tuning happens, on train or validation only.

### Round 1, 2026-11-06, validation only

Baseline before tuning (schema 1.0.0, validation, n=100): total F1 0.776, subtotal F1 0.800, tax F1 0.765, line items F1 0.000. Source: `docs/progress/logs/run-cord-s1-validation.log` and the first committed `evals/results/dev/` run.

Changes, all from reading validation errors:

- Values glued to a label (`Change:9,000`) are split from the token and keep its box.
- Trailing punctuation is stripped from amounts in the extractor. The frozen normaliser is unchanged.
- A value may sit alone on the line below its label.
- `cord_receipt` schema 1.1.0 adds label variants (`grandtotal`, `net amt`, `tax amt`, `pb 1`, `pajak`), and ignores count lines such as `total item`.
- Headerless receipt rows: rows run from the top of the receipt to the first summary line, and read `[qty] description [@price] [qty] amount`.

Pure OCR misreads such as `590050` for `59,500` were left alone. Patching them would fit noise.

### Round 2, 2026-11-07, validation only

The LLM extractor now treats the literal strings `null`, `none`, `n/a` and `na` as no value. Reading S2 rows showed the model sometimes returns these. Field scores did not change, because such strings never normalised to a value, but verification counts did. No prompt changed, so replies come from the replay cache.

### Round 3, 2026-11-07, prompt round on train only

Run as pre-registered above. S2 on the 100-document train subset, metrics 1.1.1 ([table](../evals/results/dev/prompt_round/prompt_round.md)): mean of four F1 for 1.0 (reference) 0.449, 2.0 0.461, 2.1 0.477, 2.2 0.495. Prompt 2.2 was chosen by the rule. `num_ctx` per prompt: 2048, 2048 and 2304, from the longest CORD prompt (864, 908 and 1129 tokens) plus `num_predict` 1024; counts were stable across repeated calls. The first reference run aborted at 95 of 100 documents below 0.4 GiB free RAM and wrote nothing; the rerun replayed the recorded replies. Validation was then read once, for S2', S3', S4' and S4h. No prompt changes after that read.

S4' needed three attempts: two aborted below 0.4 GiB free RAM (records in `evals/results/aborted/`) and wrote no result, so no S4' number was seen before the completed run. Recorded replies replayed on each retry; timings are labelled mixed where that happened.

## Changes after first results

No S1 rule, schema, normalisation or metric definition has changed since `evals/results/cord_s1_v1.json`. Metrics 1.1 added new definitions and left the 1.0 path intact, which the reproduction in `docs/progress/logs/s1-reproduction.txt` confirms.

The `memory` block of `evals/results/cord_s1_v1_1.json` reads 0.0 for process and runner because that run ended before the first sample, and the file is not regenerated. The sampler was fixed afterwards. Its other contents are unaffected.

## Results

Reported test result: [S1 on CORD test, metrics 1.1.1](../evals/results/cord_s1_v1_1_1.md), rescored from saved predictions; [metrics 1.1](../evals/results/cord_s1_v1_1.md). History: [metrics 1.0](../evals/results/cord_s1_v1.md).

The test split has been read for S1 only: once at commit `1b53a77`, and again for the reproduction check and metrics 1.1, as the 2026-11-07 review directed, with no rule change. S2 to S5, S2'-S4' and S4h have not read it.

- Reproduction log: `docs/progress/logs/s1-reproduction.txt`. 140 values, 0 different, with fresh OCR, and again at clean HEAD.
- Layout groups: [S1 by layout group](../evals/results/cord_s1_v1_1_layout_groups.md).
- Synthetic: [S1 per layout, dev versus held-out](../evals/results/synthetic_s1_v1_1.md).
- Validation, for development only: [all systems, metrics 1.1.1](../evals/results/dev/cord_validation_comparison_v1_1_1.md), covering S1-S4 (prompt 1.0), S2', S3', S4' (prompt 2.2) and S4h.
- Synthetic S2' (prompt 2.2), dev versus held-out: [table](../evals/results/synthetic_s2p_v1_1_1.md), next to [S1](../evals/results/synthetic_s1_v1_1.md).

The S1 latency differed between runs (p50 2.57 s, then 2.00 s). Timings are not reproducible in the way scores are.

`n` counts usable labels. Tax has n=41 on test: 43 documents hold the key, but two contain only `-`, which this protocol defines as absent.

With one tuning round on 100 validation documents, the validation numbers are optimistic, and the test table is the reported result.

The test run's log has no HEARTBEAT line, because of a wrapper bug fixed afterwards (see Operational lessons in `docs/progress/PROGRESS.md`). Its `EXIT=0` line was written after the process ended and is valid. The run was not repeated, because the test split is read once.
