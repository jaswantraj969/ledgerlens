# S1 on cord-v2 test

Generated from `cord_s1_v1.json`. Do not edit by hand.

- Documents: 100. `n` is documents with a label for the field.
- Schema: cord_receipt 1.1.0.
- Normalisation: 1.0, sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1`.
- Split sha256: `b8535d600517fdcf857f79ba0d27d839ae943afab3f4081761a78f29de562049`.
- Intervals: 95% bootstrap, 2000 resamples of documents, seed 20261106.
- Failures: 0 crashes, 0 documents without tokens.
- Latency per document (OCR plus extraction, per document): p50 2.57 s, p95 5.39 s.
- Commit: `1b53a77461f85c0351fffd01092e7f5852f71968`, dirty: False.

| Field | n | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] | Exact match [95% CI] |
|---|---|---|---|---|---|
| total_amount | 95 | 0.873 [0.797, 0.940] | 0.726 [0.633, 0.813] | 0.793 [0.712, 0.866] | 0.730 [0.640, 0.820] |
| subtotal | 65 | 0.957 [0.887, 1.000] | 0.692 [0.574, 0.797] | 0.804 [0.713, 0.876] | 0.780 [0.690, 0.860] |
| tax_amount | 41 | 0.829 [0.686, 0.946] | 0.707 [0.562, 0.841] | 0.763 [0.622, 0.881] | 0.880 [0.810, 0.940] |
| line_items.amount | 99 | 0.751 [0.674, 0.825] | 0.772 [0.697, 0.839] | 0.762 [0.698, 0.818] | 0.490 [0.390, 0.590] |
| line_items.description | 100 | 0.565 [0.479, 0.655] | 0.570 [0.484, 0.652] | 0.567 [0.484, 0.646] | 0.330 [0.240, 0.430] |
| line_items.quantity | 87 | 0.953 [0.903, 0.990] | 0.459 [0.343, 0.562] | 0.620 [0.503, 0.710] | 0.360 [0.270, 0.460] |
| line_items.unit_price | 34 | 1.000 [1.000, 1.000] | 0.045 [0.000, 0.123] | 0.086 [0.000, 0.220] | 0.680 [0.590, 0.770] |

Gold values excluded as unparsable: none.
