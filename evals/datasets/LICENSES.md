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
| tax_amount | sub_total.tax_price | 355 / 47 / 43 |
| line_items.description | menu.nm | 795 / 100 / 100 |
| line_items.quantity | menu.cnt | 729 / 94 / 87 |
| line_items.unit_price | menu.unitprice | 291 / 31 / 34 |
| line_items.amount | menu.price | 799 / 99 / 99 |

**Not evaluable on CORD:** vendor_name, invoice_number, invoice_date, currency. CORD does not label them.

**No vendor identifier.** Metadata holds only `image_id`, `image_size`, `split` and `version`. A grouped split must use derived layout groups, and reports must call them derived.

## Not yet obtained

- **SROIE:** source and licence not verified. Treat as research-only. Several community copies exist on Hugging Face; a repository tag alone is not evidence of a right to use the data.
- **DocILE:** access needs a human request. Never redistributed.
- **FUNSD:** forms, not invoices. Not used for the main schema.

## Synthetic

Generated locally with a seed. Results are reported separately and never mixed with real-dataset claims.
