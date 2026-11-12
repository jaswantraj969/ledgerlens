# Documentation index

Research prototype evaluated on public datasets. Not validated for production use.

## Start here
- [../README.md](../README.md): what LedgerLens is, the quickstart, all commands, and the results.
- [architecture.md](architecture.md): running services, pipeline and data model (Mermaid diagrams).
- [limitations.md](limitations.md): what does not work, or was not measured.
- [security-review.md](security-review.md): the API and worker security review, item by item.

## Evaluation
- [evaluation.md](evaluation.md): splits, metric definitions, pre-registrations, tuning log and the development results.
- [evaluation/final-test-protocol.md](evaluation/final-test-protocol.md): the final CORD test protocol, committed before any test access.
- [evaluation/addendum-01-duplicate-sensitivity.md](evaluation/addendum-01-duplicate-sensitivity.md): the post hoc duplicate-exclusion check.
- [acceptance-criteria.md](acceptance-criteria.md): acceptance criteria A1 to A17.
- Results files: [../evals/results/final/](../evals/results/final/) (final test tables and figure); [../evals/datasets/LICENSES.md](../evals/datasets/LICENSES.md) (datasets and licences).

## Decisions (ADRs)
- [adr/0001-stack.md](adr/0001-stack.md): stack
- [adr/0002-ocr-engine.md](adr/0002-ocr-engine.md): OCR engine
- [adr/0003-llm-replay.md](adr/0003-llm-replay.md): LLM providers and the replay cache
- [adr/0004-job-queue.md](adr/0004-job-queue.md): job queue
- [adr/0005-auth.md](adr/0005-auth.md): authentication
- [adr/0006-storage.md](adr/0006-storage.md): document storage
- [adr/0007-confidence.md](adr/0007-confidence.md): risk score and calibration
- [adr/0008-datasets.md](adr/0008-datasets.md): datasets
- [adr/0009-frontend.md](adr/0009-frontend.md): frontend
- [adr/0010-deployment.md](adr/0010-deployment.md): deployment
- [adr/0011-default-extraction-model.md](adr/0011-default-extraction-model.md): default extraction model
- [adr/0012-qwen3-not-adopted.md](adr/0012-qwen3-not-adopted.md): qwen3:4b not adopted
- [adr/0013-a11-synthetic-scope.md](adr/0013-a11-synthetic-scope.md): A11 synthetic scope

## Progress and evidence
- [progress/TASKS.md](progress/TASKS.md): task status with the five labels and acceptance-criteria status.
- [progress/PROGRESS.md](progress/PROGRESS.md): dated progress log.
- [progress/ENVIRONMENT.md](progress/ENVIRONMENT.md): machine, memory and power notes.
- [progress/logs/](progress/logs/): command logs cited as evidence.
- [portfolio/](portfolio/): portfolio drafts, published by the owner only.
