# LedgerLens: project summary (150 words)

Research prototype evaluated on public datasets. Not validated for production use.

LedgerLens extracts totals, taxes and line items from receipts and invoices, links each value to its place on the page, checks it against the document, and sends uncertain values to a person for review. It runs locally with Docker: a FastAPI service, a background worker, PostgreSQL, Redis and a React review app, with an optional local LLM (llama3.2:3b through Ollama).

I built it evaluation-first. Protocols were committed before the CORD v2 test split was read once. On those 100 test receipts, the tuned rules reached total F1 0.793 and the rules-plus-LLM hybrid 0.827, with overlapping intervals; the rules stayed ahead on tax and line items. A calibrated router let 19% of header fields skip review, at 0.966 measured precision; essentially every line item still goes to a person. One command regenerates every result table and figure from the saved result files. All numbers, limitations and the protocol are in the repository.

## Sources
- Total F1 0.793 (S1) and 0.827 (S4h), and the tax and row comparison: `evals/results/final/cord_test_comparison_v1_1_1.md`
- 19% of header fields (0.193) at 0.966 precision; 3 of 253 rows accepted: `evals/results/final/cord_s5_test_v1_1_1.md` (S5-S1, all variant, target 0.98)
- 100 test documents: `evals/results/final/cord_test_comparison_v1_1_1.json` (`n_documents`)
