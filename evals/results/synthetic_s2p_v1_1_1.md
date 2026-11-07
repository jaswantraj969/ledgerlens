# S2' on synthetic invoices (metrics 1.1.1)

Generated from `synthetic_s2p_v1_1_1.json`. Do not edit by hand. Synthetic results are reported apart and are not real-dataset claims.

Commit `29dfc5e71eb72328584af7a4f591c2d366d0d9e5`, dirty: False.

## Route: native_pdf, 40 documents per layout

### Dev versus held-out, F1 pooled over documents

| Field | Dev F1 | Held-out F1 | Gap (dev minus held-out) |
|---|---|---|---|
| vendor_name | 1.000 | 0.775 | 0.225 |
| invoice_number | 1.000 | 0.675 | 0.325 |
| invoice_date | 1.000 | 1.000 | 0.000 |
| currency | 1.000 | 1.000 | 0.000 |
| subtotal | 0.857 | 0.000 | 0.857 |
| tax_amount | 0.925 | 0.656 | 0.269 |
| total_amount | 0.963 | 1.000 | -0.037 |
| line_items_row_level | 0.699 | 0.781 | -0.082 |

### F1 per layout

| Field | classic | modern | receipt | statement | ledger (held out) |
|---|---|---|---|---|---|
| vendor_name | 1.000 | 1.000 | 1.000 | 1.000 | 0.775 |
| invoice_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.675 |
| invoice_date | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| currency | 1.000 | 1.000 | n/a | 1.000 | 1.000 |
| subtotal | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| tax_amount | 0.919 | 0.944 | 0.919 | 0.919 | 0.656 |
| total_amount | 1.000 | 1.000 | 0.850 | 1.000 | 1.000 |
| line_items (row level) | 0.769 | 0.593 | 0.722 | 0.711 | 0.781 |

## Route: ocr, 20 documents per layout

### Dev versus held-out, F1 pooled over documents

| Field | Dev F1 | Held-out F1 | Gap (dev minus held-out) |
|---|---|---|---|
| vendor_name | 0.988 | 1.000 | -0.012 |
| invoice_number | 1.000 | 0.450 | 0.550 |
| invoice_date | 1.000 | 1.000 | 0.000 |
| currency | 1.000 | 1.000 | 0.000 |
| subtotal | 0.857 | 0.000 | 0.857 |
| tax_amount | 0.925 | 1.000 | -0.075 |
| total_amount | 0.963 | 1.000 | -0.037 |
| line_items_row_level | 0.713 | 0.753 | -0.041 |

### F1 per layout

| Field | classic | modern | receipt | statement | ledger (held out) |
|---|---|---|---|---|---|
| vendor_name | 1.000 | 0.950 | 1.000 | 1.000 | 1.000 |
| invoice_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.450 |
| invoice_date | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| currency | 1.000 | 1.000 | n/a | 1.000 | 1.000 |
| subtotal | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| tax_amount | 0.919 | 0.944 | 0.919 | 0.919 | 1.000 |
| total_amount | 1.000 | 1.000 | 0.850 | 1.000 | 1.000 |
| line_items (row level) | 0.788 | 0.642 | 0.657 | 0.782 | 0.753 |
