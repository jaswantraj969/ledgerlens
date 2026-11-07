# ADR-0011: Default local extraction model

Status: Accepted
Date: 2026-11-07

## Decision
`llama3.2:3b` (2.02 GB, Q4_K_M, digest `a80c4f17acd5`) is the default local model, with `temperature` 0, `seed` 20261106, `num_ctx` 4096 and `num_predict` 1024. It is the only extraction-capable model installed. No other model is pulled without the project owner's approval.

## Evidence
A seeded 10-document sample of CORD validation, prompt `a-1.0`, one pass. Source: `evals/results/dev/llm_smoke_llama3.2-3b.json`, log `docs/progress/logs/run-llm-smoke.log`. This is a development smoke test, not an evaluation result.

| Measure | Value |
|---|---|
| JSON valid on first attempt | 10 of 10 |
| Retries, fallbacks, truncated replies | 0, 0, 0 |
| Placement | 100% GPU (2.56 of 2.56 GB in VRAM) |
| Latency p50, all 10 | 2.54 s |
| Latency p95, all 10 | 73.46 s |
| Latency p50, 9 warm documents | 2.47 s |
| Latency p95, 9 warm documents | 6.35 s |
| First document, cold | 127.62 s, of which 69.55 s is model load |
| Replay of the same 10 | 0 live calls, 10 hits, same outputs |

Read these with care:

- The all-document p95 is an interpolation dominated by the single cold start, so the warm figures describe normal running. With n=10 no p95 here is precise.
- 69.55 s of the cold document is measured load time. Ollama's figures do not explain the remaining 58 s.
- JSON validity is close to guaranteed, because Ollama constrains output to the schema. It shows the plumbing works and says nothing about correctness.
- Header fields were right on 15 of 17 labelled values, and 3 of 107 extracted values were not found in the document. Ten documents are far too few to compare models or systems.

## Consequences
Evaluation runs should load the model once and hold it with `keep_alive`, or report cold starts apart. A larger model is not proposed: warm speed is adequate, and this sample cannot show whether quality is limiting. That question waits for S2 on all of validation.
