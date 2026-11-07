# S1 on synthetic invoices (metrics 1.1)

Generated from `synthetic_s1_v1_1.json`. Do not edit by hand. Synthetic results are reported apart and are not real-dataset claims.

Commit `7832fc29b2824a57909d1f22be3776c43e0e479e`, dirty: False.

## Route: native_pdf, 40 documents per layout

### Dev versus held-out, F1 pooled over documents

| Field | Dev F1 | Held-out F1 | Gap (dev minus held-out) |
|---|---|---|---|
| vendor_name | 1.000 | 0.000 | 1.000 |
| invoice_number | 1.000 | 0.000 | 1.000 |
| invoice_date | 1.000 | 0.000 | 1.000 |
| currency | 0.988 | 1.000 | -0.012 |
| subtotal | 1.000 | 0.000 | 1.000 |
| tax_amount | 1.000 | 0.000 | 1.000 |
| total_amount | 1.000 | 0.000 | 1.000 |
| line_items_row_level | 1.000 | 1.000 | 0.000 |

### F1 per layout

| Field | classic | modern | receipt | statement | ledger (held out) |
|---|---|---|---|---|---|
| vendor_name | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| invoice_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| invoice_date | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| currency | 1.000 | 1.000 | 0.000 | 0.975 | 1.000 |
| subtotal | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| tax_amount | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| total_amount | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| line_items (row level) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Route: ocr, 20 documents per layout

### Dev versus held-out, F1 pooled over documents

| Field | Dev F1 | Held-out F1 | Gap (dev minus held-out) |
|---|---|---|---|
| vendor_name | 0.988 | 0.000 | 0.988 |
| invoice_number | 1.000 | 0.000 | 1.000 |
| invoice_date | 1.000 | 0.000 | 1.000 |
| currency | 0.975 | 1.000 | -0.025 |
| subtotal | 1.000 | 0.000 | 1.000 |
| tax_amount | 1.000 | 0.000 | 1.000 |
| total_amount | 1.000 | 0.000 | 1.000 |
| line_items_row_level | 0.997 | 0.987 | 0.010 |

### F1 per layout

| Field | classic | modern | receipt | statement | ledger (held out) |
|---|---|---|---|---|---|
| vendor_name | 1.000 | 0.950 | 1.000 | 1.000 | 0.000 |
| invoice_number | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| invoice_date | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| currency | 1.000 | 1.000 | 0.000 | 0.950 | 1.000 |
| subtotal | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| tax_amount | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| total_amount | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| line_items (row level) | 1.000 | 1.000 | 0.986 | 1.000 | 0.987 |
