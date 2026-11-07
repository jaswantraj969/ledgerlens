# ADR-0012: qwen3:4b is not adopted; llama3.2:3b stays the default

Status: Accepted
Date: 2026-11-08

## Context
The owner approved pulling `qwen3:4b` (2.5 GB, digest `359d7dd4bcda`) and declined `qwen2.5:7b` for lack of RAM. The comparison against `llama3.2:3b` was pre-registered in `docs/evaluation.md` (commit `33eb171`) before any qwen3 result: adopt qwen3:4b only if its S4h mean F1 on the train subset is at least 0.05 higher, its warm p95 latency is at most twice llama's, and no more than one of its runs aborts on memory.

## What happened
The pull completed on 2026-11-07 after about 1 h 40 min. Thinking-off was implemented and tested before any run (`dffefb0`). The first qwen3 step, measuring prompt length in qwen3 tokens to set `num_ctx`, aborted twice under the 0.4 GiB free-RAM rule: at 0.321 GiB with Docker Desktop running, and at 0.304 GiB with Docker Desktop stopped and 3.69 GiB free before the run. Record: `evals/results/aborted/qwen3-4b_token_measurement_aborts.json`. With qwen3:4b loaded at `num_ctx` 4096 and fully on the GPU, its runner held about 2.9 GB of system RAM, against 0.7 to 0.9 GiB for llama3.2:3b at `num_ctx` 2304.

## Decision
Under the pre-registered rule, two memory aborts mean qwen3:4b is not adopted. The decision was taken before any qwen3 extraction result existed, so no quality number influenced it. No qwen3 smoke test, comparison or validation read was run, and there is no S4h-qwen row. `llama3.2:3b` stays the default, and S5-S4h uses it.

## Consequences
- The model question stays open on this machine: RAM, not VRAM, is the limit. A model is only worth trying here if its runner fits in about 1 GiB of system RAM next to the other applications, or on a machine with more RAM.
- `qwen3:4b` stays installed (2.5 GB on disk). The owner may remove it with `ollama rm qwen3:4b`.
