# Changelog

## v1.0.0 (2026-11-13)

First release. Research prototype evaluated on public datasets. Not validated for production use. Licence: MIT.

### Application
- Upload of PDF, JPEG and PNG documents, with validation by content (type, size, page count, image pixels) and deduplication per organisation.
- Background processing on an RQ worker: native PDF text or CPU OCR (RapidOCR); extraction with rules by default, or with a local LLM (`llama3.2:3b` through Ollama on the host). Every value is verified against the page, scored for risk, and routed to review or acceptance. Steps are idempotent, retried with backoff, and dead-lettered.
- Review UI (React): the page image with evidence boxes, approve, reject or correct per field, the document's audit trail (newest first, with the old and new value), a review queue, and an evaluation page with the final test results.
- JSON and CSV export, per document or for up to 50 reviewed documents at once (selected on the documents page); a read-only audit trail route per document; HMAC-signed webhooks with retries, a receiver-side replay window, and public-address-only targets.
- Authentication with JWT access and refresh tokens and API keys; roles; rate limits on login and upload.
- Docker Compose stack (PostgreSQL, Redis, API, worker, web). All containers run as non-root users, and all ports are bound to 127.0.0.1.

### Evaluation
- CORD v2 test split read once, under a protocol committed before any test access: S1 (rules), S2′, S3′, S4′ (LLM variants), S4h (pre-registered hybrid), and S5 (calibrated routing) on two bases. Also ablations and an image-degradation study. Results: `evals/results/final/`.
- A post hoc duplicate-exclusion check (addendum 01), registered before it was computed.
- Synthetic invoice set with a held-out layout, for S1 and S2′.

### Tooling
- `scripts/init_env.py`, `scripts/tasks.sh` (up, test, lint, typecheck, eval-smoke, reproduce, ci), `scripts/download_cord.py` (pinned revision, checksums).
- CI workflow with actions pinned to commit SHAs and read-only permissions; it needs no secrets.

### Known limitations
- The LLM mode inside Docker was not verified end to end (free-RAM gate on a 16 GB machine).
- Line items are effectively routed to human review; header precision on test is below the 0.98 target at the point estimate.
- CORD has near-duplicate documents across its official splits (7 test documents).

See `docs/limitations.md` and `docs/progress/final-report.md`.
