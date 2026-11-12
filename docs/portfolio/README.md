# Portfolio drafts

Drafts only. The owner reviews and publishes them; nothing here has been published.

Research prototype evaluated on public datasets. Not validated for production use.

- [summary.md](summary.md): 150-word project summary
- [upwork-entry.md](upwork-entry.md): Upwork portfolio entry (title, description, skills, role)
- [case-study.md](case-study.md): short case study

Every number in these files is copied from a file in `evals/results/final/`, named under each text. The one exception is the synthetic-layout finding, which is described without numbers and cites `evals/results/synthetic_*.md`. They contain no latency figures, no client claims and no production claims.

## Screenshots (not in git)

`docs/portfolio/screenshots/` is gitignored, because the images show CORD receipts and dataset documents are never committed. They are produced by `frontend/e2e/screenshots.spec.ts` against the running Compose stack, with the worker in rules mode and CORD v2 train documents 0, 1 and 2 as input. Log: `docs/progress/logs/portfolio-screenshots.log`.

| File | Shows |
|---|---|
| `screenshots/1-documents.png` | Documents page after uploading three CORD receipts |
| `screenshots/2-review.png` | Review page: receipt image with evidence boxes, fields with risk scores |
| `screenshots/3-queue.png` | Review queue, highest risk first |
| `screenshots/4-report.png` | Evaluation page: final CORD test table and validation table |

Attribution to show with any screenshot: CORD v2 receipts, Park et al., "CORD: A Consolidated Receipt Dataset for Post-OCR Parsing" (2019), NAVER Clova, CC BY 4.0.
