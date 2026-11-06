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

## Metrics

Header fields, per document:

- Prediction and gold both present and equal: TP.
- Both present and different: FP and FN.
- Prediction with no gold: FP.
- Gold with no prediction: FN.
- Both absent: no count, but it agrees for exact match.

`exact_match` is the share of all documents where prediction and gold agree, including both absent. `n` is the count of documents with a gold value for the field.

Line items: per document, predicted and gold values are compared as multisets. TP is the size of the intersection, FP and FN are the remainders, and totals are pooled across documents. `exact_match` is the share of documents whose multisets are equal. Row alignment is not checked.

Confidence intervals: 95% percentile bootstrap, 2000 resamples of **documents**, seed 20261106.

Latency: wall time per document on the recorded hardware, covering OCR and extraction, reported as p50 and p95. Failures count crashes and documents with no OCR tokens.

## S1 system

S1 is RapidOCR followed by the deterministic extractor. It needs no LLM.

## Tuning log

Entries are added as tuning happens, on train or validation only.

## Changes after first results

None.
