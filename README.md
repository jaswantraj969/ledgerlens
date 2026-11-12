# LedgerLens

Evaluation-driven extraction of invoices and receipts: parse with provenance, extract to a schema, verify against the source, and estimate error risk.

**Status: work in progress.** Research prototype evaluated on public datasets. Not validated for production use. No compliance certification. The API, worker, review UI and a local Docker Compose stack exist and pass their tests, including one end-to-end browser test (upload, review, export) against the Compose stack. The final CORD test read is complete; see Results below. See [docs/progress/TASKS.md](docs/progress/TASKS.md) and [docs/limitations.md](docs/limitations.md).

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

## Results

Research prototype evaluated on public datasets. Not validated for production use.

All figures below come from result files written by the final CORD test read. That read ran once, under a protocol committed before any test access ([docs/evaluation/final-test-protocol.md](docs/evaluation/final-test-protocol.md)), with `llama3.2:3b` running locally through Ollama, prompt 2.2, normalisation 1.0 and metrics 1.1.1. Intervals are 95% document-bootstrap intervals. Generated tables are in [evals/results/final/](evals/results/final/). No latency figures are quoted here.

**Headline.** The local LLM (`llama3.2:3b`) does not beat the tuned rules on CORD. It does transfer to an unseen synthetic layout where the rules fail.
- **CORD:** S4h (rules plus LLM) is slightly higher than the rules (S1) on total F1, with overlapping intervals, and lower on subtotal, tax and line items.
- **Unseen synthetic layout** (the held-out "ledger" layout, 40 native-PDF invoices; synthetic, not a real-dataset claim): the rules score F1 0.000 on vendor, invoice number, date, subtotal, tax and total. S2′ (the LLM alone) scores 0.775, 0.675, 1.000, 0.000, 0.656 and 1.000 on those fields. Subtotal does not transfer, and on line items the rules stay ahead (row F1 1.000 against 0.781). Sources: [synthetic_s1_v1_1.md](evals/results/synthetic_s1_v1_1.md) and [synthetic_s2p_v1_1_1.md](evals/results/synthetic_s2p_v1_1_1.md).

### CORD v2 test: field F1 and row-level F1

n = 100 test documents. The gold value is present for total in 95, subtotal in 65 and tax in 41, and there are 251 gold line-item rows.

| System | Total F1 | Subtotal F1 | Tax F1 | Row-level F1 |
|---|---|---|---|---|
| S1 (rules) | 0.793 [0.712, 0.866] | 0.804 [0.713, 0.876] | 0.763 [0.622, 0.881] | 0.365 [0.263, 0.471] |
| S2′ (LLM, one pass) | 0.765 [0.684, 0.843] | 0.478 [0.341, 0.602] | 0.554 [0.430, 0.667] | 0.193 [0.121, 0.272] |
| S3′ (S2′ plus evidence check) | 0.773 [0.696, 0.849] | 0.484 [0.346, 0.606] | 0.564 [0.442, 0.679] | 0.192 [0.118, 0.272] |
| S4′ (two LLM passes plus rules, merged) | 0.821 [0.747, 0.892] | 0.728 [0.633, 0.813] | 0.508 [0.393, 0.609] | 0.199 [0.126, 0.283] |
| S4h (hybrid, pre-registered) | 0.827 [0.753, 0.898] | 0.724 [0.627, 0.807] | 0.508 [0.393, 0.609] | 0.253 [0.168, 0.343] |

S1 is the Phase 4 test read; it was not scored again. Source: [cord_test_comparison_v1_1_1.md](evals/results/final/cord_test_comparison_v1_1_1.md).

### S5: which values can skip human review

S5 fits a logistic model on CORD train predictions to score each extracted value, and accepts a value without review only when its score clears a threshold set on validation for a precision target. Header slots (total, subtotal and tax, 3 per document, filled or not) and predicted line-item rows are scored separately. On CORD test:

| System | Target | Header automation [95% CI] | Header precision achieved [95% CI] | Row automation [95% CI] | Row precision achieved [95% CI] |
|---|---|---|---|---|---|
| S5-S1 | 0.98 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000], target not met | 0.012 [0.000, 0.033] (3 / 253) | 1.000 [1.000, 1.000] |
| S5-S1 | 0.99 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000], target not met | 0.012 [0.000, 0.033] (3 / 253) | 1.000 [1.000, 1.000] |
| S5-S4h | 0.98 | 0.163 [0.120, 0.210] (49 / 300) | 0.959 [0.891, 1.000], target not met | 0.000 [0.000, 0.000] (0 / 422) | none accepted |
| S5-S4h | 0.99 | 0.140 [0.097, 0.183] (42 / 300) | 0.976 [0.917, 1.000], target not met | 0.000 [0.000, 0.000] (0 / 422) | none accepted |

- **Line items are effectively routed to human review.** At either target, 3 of 253 rows (S5-S1) and 0 of 422 rows (S5-S4h) are accepted automatically, so a person reviews essentially every line item.
- **Header fields:** between 14% and 19% of header slots skip review, and the precision achieved on test falls short of the target set on validation.

**Unseen layout groups (grouped variant).** Here S5 is fitted and thresholded only on documents from the calibration layout groups. It is then scored on the 37 test documents from the four layout groups it never saw (111 header slots), with the same results at both targets:
- **S5-S1:** header automation 0.126 [0.045, 0.225] (14 / 111), precision 1.000 [1.000, 1.000]; rows 0 of 81 accepted.
- **S5-S4h:** header automation 0.081 [0.027, 0.153] (9 / 111), precision 1.000 [1.000, 1.000]; rows 0 of 142 accepted.

Source: [cord_s5_test_v1_1_1.md](evals/results/final/cord_s5_test_v1_1_1.md). Ablations: [cord_s5_ablations_test_v1_1_1.md](evals/results/final/cord_s5_ablations_test_v1_1_1.md).

### Degradation

Degradation was tested on the 100 test images, with fixed blur and JPEG perturbations. Strong blur (radius 3.0) cut the mean of the four F1 values most: S1 from 0.681 to 0.446, S4h from 0.578 to 0.399. JPEG quality 10 cut it less (S1 to 0.545, S4h to 0.483). S4h stayed below S1 under every condition. Source: [cord_degradation_test_v1_1_1.md](evals/results/final/cord_degradation_test_v1_1_1.md), [figure](evals/results/final/cord_degradation_test_v1_1_1.png).

## Licence

Not chosen yet.
