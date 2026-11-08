# LedgerLens

Evaluation-driven extraction of invoices and receipts: parse with provenance, extract to a schema, verify against the source, and estimate error risk.

**Status: work in progress.** Research prototype evaluated on public datasets. Not validated for production use. No compliance certification. The API, worker, review UI and a local Docker Compose stack exist and pass their tests, including one end-to-end browser test (upload, review, export) against the Compose stack. The final test-split evaluation has not been run. See [docs/progress/TASKS.md](docs/progress/TASKS.md) and [docs/limitations.md](docs/limitations.md).

## Commands

Every command works two ways. `make` is optional, because each target only calls `scripts/tasks.sh`.

| Task | With GNU make | Without make (Git Bash on Windows, or any Unix shell) |
|---|---|---|
| Start Postgres and Redis | `make dev` | `bash scripts/tasks.sh dev` |
| Start the whole stack | `make up` | `bash scripts/tasks.sh up` |
| Stop the stack | `make down` | `bash scripts/tasks.sh down` |
| Run tests | `make test` | `bash scripts/tasks.sh test` |
| Lint and format check | `make lint` | `bash scripts/tasks.sh lint` |
| Type check | `make typecheck` | `bash scripts/tasks.sh typecheck` |
| Local CI mirror | `make ci` | `bash scripts/tasks.sh ci` |
| Offline smoke evaluation | `make eval-smoke` | `bash scripts/tasks.sh eval-smoke` |
| Regenerate tables | `make tables` | `bash scripts/tasks.sh tables` |
| Rebuild validation results from caches | `make reproduce` | `bash scripts/tasks.sh reproduce` |

`make up` builds and starts the whole stack: Postgres, Redis, API, worker and web. The web UI is at http://127.0.0.1:8080 by default. Set `LEDGERLENS_WEB_PORT` in `.env` if that port is taken. The worker uses rules only by default; set `LEDGERLENS_EXTRACTION_MODE=llm_or_rules` to use a local Ollama on the host.

On Windows, GNU make is optional: `winget install GnuWin32.Make`, or use the right-hand column.

## Setup

```
cd backend
uv sync --python 3.12 --extra eval --extra ocr
uv run pre-commit install
```

Run the install step once per clone, so commits run the hooks. Copy `.env.example` to `.env` before starting services.

## Evaluation

The protocol, metric formulas and results are in [docs/evaluation.md](docs/evaluation.md). Every reported number comes from a file in `evals/results/`.

### S5: when a value can skip human review

S5 scores each extracted value with a risk score from a logistic model fitted on CORD train predictions, and accepts a value without review only when its score clears a threshold set for a precision target. Header fields (total, subtotal, tax) and line-item rows are scored separately. On CORD validation, at a 0.98 precision target:

| Base system | Header automation rate | Row automation rate |
|---|---|---|
| S5-S1 (rules) | 0.237 (71 of 300 header slots) | 0.013 (3 of 230 predicted rows) |
| S5-S4h (rules plus llama3.2:3b) | 0.197 (59 of 300 header slots) | 0.003 (1 of 354 predicted rows) |

**Line items are effectively routed to human review.** At this precision target almost no row is accepted automatically, so in practice a person reviews every line item. Only about a fifth to a quarter of header fields skip review.

These are development numbers: the thresholds were chosen on the same validation documents, so the rates are optimistic, and the test split has not been read for S5. Source: [evals/results/dev/cord_s5_validation_comparison_v1_1_1.md](evals/results/dev/cord_s5_validation_comparison_v1_1_1.md).

Latency figures are quoted only from runs recorded entirely on AC power. Every results table has a Power column, and runs that were partly on battery are labelled `battery-affected`.

## Licence

Not chosen yet.
