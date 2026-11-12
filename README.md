# LedgerLens

Evaluation-driven extraction of invoices and receipts: parse with provenance, extract to a schema, verify every value against the source document, and route uncertain values to a person.

**Status: v1.0.0, research prototype.** Research prototype evaluated on public datasets. Not validated for production use. No compliance certification. Licence: MIT ([LICENSE](LICENSE)). Progress: [docs/progress/TASKS.md](docs/progress/TASKS.md). Limitations: [docs/limitations.md](docs/limitations.md).

## What it is

- **Application:** you upload a PDF, JPEG or PNG, and a background worker extracts the total, subtotal, tax and line items. Each value keeps the page region it came from, is checked against the document text and arithmetic rules, and either goes to a review queue or is accepted. Reviewed results export as CSV or JSON, and signed webhooks report job events.
- **Evaluation:** the same pipeline is measured on the public CORD v2 receipt dataset and on seeded synthetic invoices, under protocols committed before any test data was read. Results are below.

## Architecture

- A React app served by Caddy talks to a FastAPI service. The service stores documents and jobs in PostgreSQL and queues work in Redis.
- An RQ worker parses each document (native PDF text, or CPU OCR with RapidOCR) and extracts with rules by default, or with a local LLM (`llama3.2:3b` through Ollama on the host). It then verifies and scores every value.
- Evaluation code in `evals/` runs the same pipeline offline against cached OCR and recorded LLM replies. Diagram and data model: [docs/architecture.md](docs/architecture.md). All docs: [docs/README.md](docs/README.md).

## Quickstart (Docker Compose, rules mode)

Needs Docker with Compose v2, Python 3.10 or later, and Git Bash on Windows (any shell elsewhere). Run from the repository root.

On Windows, clone to a short path such as `C:\src\ledgerlens`, or enable long paths. Some files in the Python environment have names near the 260-character path limit, and a deep clone folder makes `import sklearn` fail. A clone at a 212-character folder depth failed this way in the fresh-clone check.

```
python scripts/init_env.py
bash scripts/tasks.sh up
```

- `init_env.py` writes `.env` with new random secrets. If port 8080 is taken, use `python scripts/init_env.py --web-port 8081` and open that port instead.
- `tasks.sh up` builds and starts PostgreSQL, Redis, the API, the worker and the web app, and waits until all five are healthy.
- Then open http://127.0.0.1:8080, register (the first user of a new organisation is its admin), and upload a document.
- `bash scripts/tasks.sh down` stops the stack and keeps its data.

The worker extracts with rules only by default; no model is needed.

### Tests and checks

With the stack running (the backend tests use its PostgreSQL and Redis):

```
cd backend && uv sync --python 3.12 --extra eval --extra ocr && cd ..
npm --prefix frontend ci
bash scripts/tasks.sh test
bash scripts/tasks.sh lint
bash scripts/tasks.sh typecheck
bash scripts/tasks.sh eval-smoke
E2E_BASE_URL=http://127.0.0.1:8080 npm --prefix frontend run e2e
```

- `test` runs the backend tests and the frontend unit tests.
- `typecheck` runs mypy over the backend and `evals/`.
- `eval-smoke` is a small offline synthetic run: no model, no network, no dataset.
- The last line is the Playwright upload, review and export test against the running stack. It uses the installed Google Chrome; use your web port if it is not 8080.

### Optional: LLM mode with Ollama on the host (not run in Docker here)

Install [Ollama](https://ollama.com), run `ollama pull llama3.2:3b`, set `LEDGERLENS_EXTRACTION_MODE=llm_or_rules` in `.env`, and run `bash scripts/tasks.sh up` again. The worker reaches the host's Ollama at `host.docker.internal:11434`.

**Not verified:** this mode has not been run end to end inside Docker. A smoke test stopped at its free-RAM gate on a 16 GB machine ([limitations](docs/limitations.md)).

### All commands

`make <target>` calls `bash scripts/tasks.sh <target>`. The Status column says how far each command has been run.

| Task | Command | Status |
|---|---|---|
| Start PostgreSQL and Redis only | `bash scripts/tasks.sh dev` | run |
| Build and start the whole stack | `bash scripts/tasks.sh up` | run |
| Stop the stack | `bash scripts/tasks.sh down` | run |
| Backend and frontend unit tests | `bash scripts/tasks.sh test` | run |
| Lint and format check | `bash scripts/tasks.sh lint` | run |
| Type check (backend and `evals/`) | `bash scripts/tasks.sh typecheck` | run |
| Offline smoke evaluation | `bash scripts/tasks.sh eval-smoke` | run |
| Local CI mirror | `bash scripts/tasks.sh ci` | last run 2026-11-07; not re-run since |
| Regenerate tables | `bash scripts/tasks.sh tables` | run |
| Rebuild validation results and the final tables from caches | `bash scripts/tasks.sh reproduce` | run |
| Download CORD v2 (2.3 GB) | `python scripts/download_cord.py` | verify mode and a one-file download run; the full download was not repeated with this script |
| Any of the above through GNU make | `make <target>` | not run: make is not installed on the development machine |

The Status column records what was run on the development machine and, for the quickstart, in a fresh clone ([docs/progress/logs/phase12-fresh-clone.log](docs/progress/logs/phase12-fresh-clone.log)).

## Data and licences

- **CORD v2:** receipts from Park et al., "CORD: A Consolidated Receipt Dataset for Post-OCR Parsing" (2019), published by NAVER Clova as [`naver-clova-ix/cord-v2`](https://huggingface.co/datasets/naver-clova-ix/cord-v2) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). No CORD file is committed. `scripts/download_cord.py` fetches it at a pinned revision and checks every file against [evals/datasets/checksums/cord-v2.sha256](evals/datasets/checksums/cord-v2.sha256). Field mapping and counts: [evals/datasets/LICENSES.md](evals/datasets/LICENSES.md).
- **Synthetic invoices:** generated by `evals/synthetic/generate.py` with fixed seeds. They are fictional, and their results are reported apart from real-data results.
- **Dependencies:** Python and npm dependencies are under permissive or weak-copyleft licences (MIT, BSD, Apache-2.0, ISC, MPL-2.0, LGPL-3.0 for psycopg); none is GPL or AGPL ([docs/progress/logs/prepush-audit.txt](docs/progress/logs/prepush-audit.txt)).

## Evaluation

The protocol, metric formulas and the development history are in [docs/evaluation.md](docs/evaluation.md) and [docs/evaluation/](docs/evaluation/). Every reported number comes from a file in `evals/results/`.

## Results

Research prototype evaluated on public datasets. Not validated for production use.

All figures below come from result files written by the final CORD test read. That read ran once, under a protocol committed before any test access ([docs/evaluation/final-test-protocol.md](docs/evaluation/final-test-protocol.md)), with `llama3.2:3b` running locally through Ollama, prompt 2.2, normalisation 1.0 and metrics 1.1.1. Intervals are 95% document-bootstrap intervals unless stated otherwise. Generated tables are in [evals/results/final/](evals/results/final/). No latency figures are quoted here.

The application's `risk_score` does not use the S5 calibrators: S5 exists only in the evaluation code.

**Headline.** The local LLM (`llama3.2:3b`) does not beat the tuned rules on CORD. It does transfer to an unseen synthetic layout where the rules fail.
- **CORD:** S4h (rules plus LLM) is slightly higher than the rules (S1) on total F1, with overlapping intervals, and lower on subtotal, tax and line items.
- **Unseen synthetic layout** (the held-out "ledger" layout, 40 native-PDF invoices; synthetic, not a real-dataset claim; S1 and S2′ both under metrics 1.1.1): the rules (S1) score F1 0.000 on vendor, invoice number, date, subtotal, tax and total. S2′ (the LLM alone) scores 0.775, 0.675, 1.000, 0.000, 0.656 and 1.000 on those fields. Subtotal does not transfer, and on line items the rules stay ahead (row F1 1.000 against 0.781). Sources: [synthetic_s1_v1_1_1.md](evals/results/synthetic_s1_v1_1_1.md) and [synthetic_s2p_v1_1_1.md](evals/results/synthetic_s2p_v1_1_1.md). S3 to S5 were not run on synthetic data ([ADR-0013](docs/adr/0013-a11-synthetic-scope.md)).

### CORD v2 test: field F1 and row-level F1

n = 100 test documents. The gold value is present for total in 95, subtotal in 65 and tax in 41, and there are 251 gold line-item rows.

| System | Total F1 | Subtotal F1 | Tax F1 | Row-level F1 |
|---|---|---|---|---|
| S1 (rules) | 0.793 [0.712, 0.866] | 0.804 [0.713, 0.876] | 0.763 [0.622, 0.881] | 0.365 [0.263, 0.471] |
| S2′ (LLM, one pass) | 0.765 [0.684, 0.843] | 0.478 [0.341, 0.602] | 0.554 [0.430, 0.667] | 0.193 [0.121, 0.272] |
| S3′ (S2′ plus evidence check) | 0.773 [0.696, 0.849] | 0.484 [0.346, 0.606] | 0.564 [0.442, 0.679] | 0.192 [0.118, 0.272] |
| S4′ (two LLM passes plus rules, merged) | 0.821 [0.747, 0.892] | 0.728 [0.633, 0.813] | 0.508 [0.393, 0.609] | 0.199 [0.126, 0.283] |
| S4h (hybrid, pre-registered) | 0.827 [0.753, 0.898] | 0.724 [0.627, 0.807] | 0.508 [0.393, 0.609] | 0.253 [0.168, 0.343] |

S1 was re-run in the final read (to save its per-field records for S5-S1). Its predictions hash matched the Phase 4 read exactly, so the S1 row is the same predictions scored the same way. Source: [cord_test_comparison_v1_1_1.md](evals/results/final/cord_test_comparison_v1_1_1.md).

Seven of the 100 test documents have identical OCR token text to a train or validation document (test 25, 28, 31, 33, 38, 44 and 75; images differ, labels identical in 5 of the 7). They are included in every figure here, as read ([limitations](docs/limitations.md)).

<!-- dedup-sensitivity:start -->
**Duplicate-exclusion check (post hoc, [addendum 01](docs/evaluation/addendum-01-duplicate-sensitivity.md)).** Leaving out the 7 test documents with a near-copy in train or validation (n = 93): no S1-against-S4h ordering changes on any field (on the 93, S1 against S4h: total 0.775 against 0.825; subtotal 0.819 against 0.729; tax 0.727 against 0.475; row-level 0.330 against 0.216). At the 0.98 target on the 93: S5-S1 header automation 0.194 at precision 0.963; S5-S4h header automation 0.168 at precision 0.957. The primary results above are unchanged. CORD also has 10 train-validation groups and 22 within-split groups with identical OCR token text. So validation choices were made partly on near-copies of train, and the document-bootstrap intervals, which treat documents as independent, are slightly optimistic. Source: [cord_test_dedup_sensitivity_v1_1_1.md](evals/results/final/cord_test_dedup_sensitivity_v1_1_1.md).
<!-- dedup-sensitivity:end -->

### S5: which values can skip human review

S5 fits a logistic model on CORD train predictions to score each extracted value, and accepts a value without review only when its score clears a threshold set on validation for a precision target. Header slots (total, subtotal and tax, 3 per document, filled or not) and predicted line-item rows are scored separately. On CORD test:

| System | Target | Header automation [95% CI] | Header precision achieved [95% CI] | Row automation [95% CI] | Row precision achieved |
|---|---|---|---|---|---|
| S5-S1 | 0.98 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000] | 0.012 [0.000, 0.033] (3 / 253) | 3 / 3 correct; exact 95% CI [0.292, 1.000] |
| S5-S1 | 0.99 | 0.193 [0.133, 0.257] (58 / 300) | 0.966 [0.906, 1.000] | 0.012 [0.000, 0.033] (3 / 253) | 3 / 3 correct; exact 95% CI [0.292, 1.000] |
| S5-S4h | 0.98 | 0.163 [0.120, 0.210] (49 / 300) | 0.959 [0.891, 1.000] | 0.000 [0.000, 0.000] (0 / 422) | none accepted |
| S5-S4h | 0.99 | 0.140 [0.097, 0.183] (42 / 300) | 0.976 [0.917, 1.000] | 0.000 [0.000, 0.000] (0 / 422) | none accepted |

- **Line items are effectively routed to human review.** At either target, 3 of 253 rows (S5-S1) and 0 of 422 rows (S5-S4h) are accepted automatically, so a person reviews essentially every line item.
- **Header fields:** between 14% and 19% of header slots skip review. For header precision, the point estimates fell below the target; every interval contains it; about 50 accepted values (42 to 58 here) cannot confirm or rule out the target.
- **Small samples:** where fewer than 30 values were accepted, the bootstrap interval of precision is degenerate (with every accepted value correct it is [1.000, 1.000]). The exact Clopper-Pearson 95% interval is given instead, and "target met" at these sizes is not evidence that the target holds.

**Review workload** (variant all, per test document, mean [95% CI]; 3 header slots plus the predicted rows):

| System | Target | Header slots routed | Rows routed | All slots routed | Share of slots routed |
|---|---|---|---|---|---|
| S5-S1 | 0.98 and 0.99 | 2.420 [2.230, 2.600] | 2.500 [1.990, 3.000] | 4.920 [4.370, 5.480] | 0.890 |
| S5-S4h | 0.98 | 2.510 [2.370, 2.640] | 4.220 [3.580, 5.040] | 6.730 [6.080, 7.570] | 0.932 |
| S5-S4h | 0.99 | 2.580 [2.450, 2.710] | 4.220 [3.580, 5.040] | 6.800 [6.140, 7.640] | 0.942 |

**Unseen layout groups (grouped variant).** Here S5 is fitted and thresholded only on documents from the calibration layout groups. It is then scored on the 37 test documents from the four layout groups it never saw (111 header slots), with the same results at both targets:
- **S5-S1:** header automation 0.126 [0.045, 0.225] (14 / 111); 14 of 14 accepted values correct, exact 95% CI [0.768, 1.000]; rows 0 of 81 accepted.
- **S5-S4h:** header automation 0.081 [0.027, 0.153] (9 / 111); 9 of 9 correct, exact 95% CI [0.664, 1.000]; rows 0 of 142 accepted.

Source: [cord_s5_test_v1_1_1.md](evals/results/final/cord_s5_test_v1_1_1.md) (and its JSON), [cord_s5_review_workload_v1_1_1.json](evals/results/final/cord_s5_review_workload_v1_1_1.json). Ablations: [cord_s5_ablations_test_v1_1_1.md](evals/results/final/cord_s5_ablations_test_v1_1_1.md).

### Degradation

Degradation was tested on the 100 test images, with fixed blur and JPEG perturbations. Strong blur (radius 3.0) cut the mean of the four F1 values most: S1 from 0.681 to 0.446, S4h from 0.578 to 0.399. JPEG quality 10 cut it less (S1 to 0.545, S4h to 0.483).
- **Mean of four F1:** S4h is below S1 in every condition.
- **Total F1:** S4h is above S1 in all five conditions: clean 0.827 against 0.793, blur 1.5 0.800 against 0.765, blur 3.0 0.549 against 0.540, JPEG 30 0.785 against 0.744, JPEG 10 0.685 against 0.654.
- **Tax and row-level F1:** S1 is above S4h in every condition.
- **Subtotal F1:** S1 is above S4h in four conditions, but S4h is above S1 under JPEG 10 (0.632 against 0.629). Under blur 3.0 the two are 0.001 apart (S1 0.506, S4h 0.505).

Source: [cord_degradation_test_v1_1_1.md](evals/results/final/cord_degradation_test_v1_1_1.md), [figure](evals/results/final/cord_degradation_test_v1_1_1.png).

## Licence

MIT, copyright 2026 Jaswant Raj. See [LICENSE](LICENSE). Datasets keep their own licences (see Data and licences above).
