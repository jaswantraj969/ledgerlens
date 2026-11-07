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

k=12 was set in advance and is not tuned. Assignments are in `evals/splits/cord_v2/layout_groups.json`. SROIE vendor groups are the primary A12 check, and these groups are a secondary check.

## SROIE vendor groups

SROIE is research-only with unverified terms; see `evals/datasets/LICENSES.md`. Vendor groups are the primary A12 check, because SROIE has a company label.

- Labels: 626 key files from a community mirror, verified against git blob hashes. The official set has 1000 receipts. This mirror lacks the labelled test portion, so the split covers 626 documents.
- Grouping: company text is casefolded, punctuation and legal suffixes are removed, and near-identical names merge at a RapidFuzz ratio of at least 92.
- Split: whole vendors are assigned to train, calibration and test at 60/20/20, largest first, seed 20261106.
- Result: 221 vendor groups, of which 150 hold one document. Train 376 documents and 79 vendors, calibration 125 and 71, test 125 and 71.

`evals/splits/sroie/vendor_groups.json` holds document IDs and anonymous group numbers only. No company name is committed. Fuzzy merging can join two different vendors or miss a variant, so groups approximate vendors.

No SROIE metric has been computed. Images are not downloaded.

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

## Metrics (version 1.1)

Metrics 1.1 replaces 1.0 for all new results, and every results file records its version. Normalisation stays at 1.0. `evals/results/cord_s1_v1.json` is kept for history under 1.0 definitions.

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

## Changes after first results

No rule, schema, normalisation or metric change has been made since `evals/results/cord_s1_v1.json`.

## Results

[S1 on CORD test](../evals/results/cord_s1_v1.md). The test split was read once, at commit `1b53a77`.

`n` counts usable labels. Tax has n=41 on test: 43 documents hold the key, but two contain only `-`, which this protocol defines as absent.

With one tuning round on 100 validation documents, the validation numbers are optimistic, and the test table is the reported result.

The test run's log has no HEARTBEAT line, because of a wrapper bug fixed afterwards (see Operational lessons in `docs/progress/PROGRESS.md`). Its `EXIT=0` line was written after the process ended and is valid. The run was not repeated, because the test split is read once.
