# LedgerLens

Evaluation-driven extraction of invoices and receipts: parse with provenance, extract to a schema, verify against the source, and estimate error risk.

**Status: work in progress.** Research prototype evaluated on public datasets. Not validated for production use. No compliance certification. The API, review UI and deployment do not exist yet. See [docs/progress/TASKS.md](docs/progress/TASKS.md) and [docs/limitations.md](docs/limitations.md).

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

`make up` starts only Postgres and Redis today, because the application containers do not exist yet.

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

## Licence

Not chosen yet.
