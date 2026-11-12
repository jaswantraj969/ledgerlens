# Upwork portfolio entry (draft; the owner publishes)

**Title:** LedgerLens: receipt and invoice extraction with measured accuracy

**Role:** Sole developer (design, backend, frontend, evaluation, deployment files)

**Description:**

Research prototype evaluated on public datasets. Not validated for production use.

LedgerLens reads receipts and invoices (PDF, JPEG, PNG) and extracts the total, subtotal, tax and line items. Every value keeps a link to where it appears on the page, is checked against the document text and arithmetic rules, and goes to a review queue unless the system is confident. Reviewers approve, correct or reject values, then export JSON or CSV. Signed webhooks report job events.

The focus was honest measurement. The test protocol was committed before the test data was read, and the test split was read once. On the public CORD v2 receipt dataset (100 test receipts):
- The tuned rules scored total F1 0.793; rules plus a local LLM scored 0.827, with overlapping confidence intervals.
- The rules stayed ahead on tax (0.763 against 0.508) and on line items (0.365 against 0.253).
- A calibrated router let 19% of header fields skip review, at 0.966 measured precision. Line items still go to a person.

Stack: Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, RQ, RapidOCR, Ollama (llama3.2:3b, local), scikit-learn, React, TypeScript, Vite, Tailwind, Playwright, Docker Compose, Caddy.

**Skills:** Python, FastAPI, Document AI, OCR, Data Extraction, LLM Integration, Ollama, Machine Learning Evaluation, PostgreSQL, Redis, React, TypeScript, Docker, Playwright, Test Automation

**Screenshots (owner to attach; CORD v2 sample receipts, CC BY 4.0, Park et al. 2019, NAVER Clova):** `screenshots/1-documents.png`, `2-review.png`, `3-queue.png`, `4-report.png`

## Sources for every number
- 100 test receipts; total F1 0.793 (S1) and 0.827 (S4h); tax 0.763 against 0.508; rows 0.365 against 0.253: `evals/results/final/cord_test_comparison_v1_1_1.md`
- 19% of header fields (0.193) at 0.966 precision: `evals/results/final/cord_s5_test_v1_1_1.md` (S5-S1, all variant, target 0.98)
