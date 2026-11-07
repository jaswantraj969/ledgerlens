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

**Status: results BLOCKED. Research-only, terms unverified.** Official access is unavailable to this project, as confirmed by the project owner on 2026-11-07. No SROIE result will be produced, and unofficial image mirrors must not be used. No licence for the dataset was found on 2026-11-06.

- **Official source:** https://rrc.cvc.uab.es/?ch=13, 1000 receipts. The download section requires a free portal account. The public Downloads page states no licence, and the terms inside the registered area have not been read. Registration needs the project owner.
- **Community mirror used for labels:** `zzzDavid/ICDAR-2019-SROIE`, which states 600 trainval and 400 test receipts. Its MIT licence covers the repository's code. It states no licence for the dataset and cannot grant one for the receipts.
- **Hugging Face copies:** several exist, some tagged MIT. A tag from a re-uploader is not evidence of a right to use the data.
- **Paper:** arXiv 2103.10213 is CC BY 4.0, which covers the paper only.

Rules until the owner confirms terms: no SROIE file, company name or receipt text is committed; it never appears in the public demo; only document IDs and anonymous group numbers are committed. The fetch script takes key files only, not images.

## Not yet obtained

- **DocILE:** access needs a human request. Never redistributed.
- **FUNSD:** forms, not invoices. Not used for the main schema.

## Synthetic

Generated locally with a seed. Results are reported separately and never mixed with real-dataset claims.
