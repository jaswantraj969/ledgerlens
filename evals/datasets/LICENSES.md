# Datasets and licences

No dataset files are committed. Each dataset keeps its own licence.

## CORD v2 (`naver-clova-ix/cord-v2`)

- Licence: CC BY 4.0, as reported by the Hugging Face dataset API on 2026-11-05.
- Files: six parquet files, 2.3 GB. SHA-256 values are in [checksums/cord-v2.sha256](checksums/cord-v2.sha256), and all six were verified after download.
- Size: 800 train, 100 validation, 100 test (counted from the downloaded files).

| LedgerLens field | CORD label | Labelled documents (train / val / test) |
|---|---|---|
| total_amount | total.total_price | 779 / 98 / 95 |
| subtotal | sub_total.subtotal_price | 530 / 67 / 65 |
| tax_amount | sub_total.tax_price | 355 / 47 / 43 (41 usable on test) |
| line_items.description | menu.nm | 795 / 100 / 100 |
| line_items.quantity | menu.cnt | 729 / 94 / 87 |
| line_items.unit_price | menu.unitprice | 291 / 31 / 34 |
| line_items.amount | menu.price | 799 / 99 / 99 |

Counts are documents holding the key. On test, 2 of the 43 `tax_price` labels (image_id 60 and 65) contain only `-`, which the protocol treats as absent, so evaluated n is 41. Reported results use usable values.

**Not evaluable on CORD:** vendor_name, invoice_number, invoice_date, currency. CORD does not label them.

**No vendor identifier.** Metadata holds only `image_id`, `image_size`, `split` and `version`. A grouped split must use derived layout groups, and reports must call them derived.

## SROIE (ICDAR 2019)

**SROIE: removed — official access unavailable; mirror terms unverified.**

- **Official source:** https://rrc.cvc.uab.es/?ch=13. Its download section requires a portal account, and the terms inside it were never read. Official access is unavailable to this project, as confirmed by the project owner on 2026-11-07.
- **Community mirror:** `zzzDavid/ICDAR-2019-SROIE`. Its MIT licence covers the repository's code and cannot grant rights to the receipts. Its dataset terms are unverified.
- **What was removed on 2026-11-07:** the 626 label files fetched from that mirror (local only, never committed), the fetch script, the split script, and `evals/splits/sroie/vendor_groups.json`, which held only document IDs and anonymous group numbers. Removal was a normal commit; earlier commits still contain the vendor-group file, which never held a company name or receipt text.
- **What remains:** the adapter `evals/datasets/sroie.py` and its tests on fictional fixtures. No images were ever downloaded and no SROIE result was produced.

## Not yet obtained

- **DocILE:** access needs a human request. Never redistributed.
- **FUNSD:** forms, not invoices. Not used for the main schema.

## Synthetic

Generated locally with a seed. Results are reported separately and never mixed with real-dataset claims.
