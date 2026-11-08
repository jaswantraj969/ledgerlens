# Environment

Raw capture: [logs/environment.txt](logs/environment.txt) (regenerate with `bash scripts/inspect_env.sh`).

| Item | Finding |
|---|---|
| OS / shell | Windows 11 Home 10.0.26300; PowerShell 5.1 and Git Bash |
| CPU / RAM | i5-13420H, 8 cores / 12 threads; 15.6 GB RAM |
| GPU | NVIDIA RTX 3050 Laptop, 6 GB VRAM. Optional only: CPU-only must keep working (R6) |
| Disk | C: 85 GB free; D: 4 GB free |
| Python | System 3.13.5; project uses 3.12 through uv (0.11.29) |
| Node / npm | 22.19.0 / 10.9.3 |
| Docker | Engine 29.7.2, Compose 5.5.0. Desktop was stopped and had to be started; VM has 8 GB and 12 CPUs |
| Git | 2.55.0; identity `jaswantraj969` configured globally |
| Missing | make, tesseract, psql, redis-server, gitleaks on PATH |

## Notes that affect the plan

- **Network is reachable but slow and uneven.** Single samples ranged from about 3 KB/s to 170 KB/s
  across PyPI, npm, GitHub, PyTorch and Ollama hosts. The lowest readings in the log (including
  0 B/s and 486 B/s) were taken while another install was using the link, so they are not
  baselines. Large downloads must be backgrounded and resumable.
- **Ollama was reinstalled by the owner.** See "Local models" below.
- **Installs need care on this link.** `uv` cannot resume a partial wheel and hung on dead
  connections, and archive errors appeared on two unrelated wheels. What worked: the default uv
  cache, a timeout per attempt, and `curl -C -` with SHA-256 checks for wheels over about 10 MB.
- **`make` is missing.** The Makefile stays as specified; Windows needs a documented equivalent.
- **PostgreSQL 18 is partly present** (`C:\Program Files\PostgreSQL\18`, pgAgent entry, no `psql`
  or `pg_ctl` in `bin`) and is not used.
- **Docker holds images from other projects.** They are left alone.

## Local models

Ollama 0.40.15, checked 2026-11-07 with `ollama --version`, `ollama list` and `/api/tags`. No model was pulled for this project.

| Model | Size on disk | Details | Use |
|---|---|---|---|
| `llama3.2:3b` | 2.02 GB | 3.2B parameters, Q4_K_M, digest `a80c4f17acd5` | Extraction default, see ADR-0011 |
| `nomic-embed-text:latest` | 0.27 GB | nomic-bert embeddings, digest `0a109f422b47` | Not usable for extraction |

Fit for `llama3.2:3b`, measured in `evals/results/dev/llm_smoke_llama3.2-3b.json`:

- **VRAM:** with `num_ctx` 4096 it loads 2.56 GB of 2.56 GB into VRAM, shown as 100% GPU by `ollama ps`. `nvidia-smi` rose from 54 MiB to about 2,590 MiB of 6,144 MiB, leaving about 3.5 GB free.
- **RAM:** 15.64 GB total, 1.66 GB free just after the run. The runner process held 0.98 GB. Free RAM is the tight resource here, so a model that spills out of VRAM would be at risk.
- **Cold start:** the first load took 69.6 s by Ollama's own `load_duration`.

Low-RAM settings, from the 2026-11-07 review:

- `OLLAMA_MAX_LOADED_MODELS=1`, set as a user environment variable. The Ollama app was stopped and started again (not reinstalled), and its server log shows `OLLAMA_MAX_LOADED_MODELS:1` and `OLLAMA_NUM_PARALLEL:1`. Evidence: `docs/progress/logs/ollama-config.txt`.
- One worker, no parallel model calls.
- Every evaluation run aborts cleanly when free system RAM falls below 0.4 GiB, records the abort under `evals/results/aborted/`, and writes no results (`evals/memory_guard.py`). The S2 and S4 validation runs of 2026-11-07 reached 0.27 and 0.25 GiB free, so under this rule they would have aborted.
- `num_ctx` for round-two prompts is measured per prompt by `evals/runners/measure_prompt_tokens.py`.

### Memory measurement, 2026-11-08

Method: `evals/runners/measure_memory.py` samples every 0.5 s psutil `available` (the value the abort guard uses), the model runner's RSS, and Windows `FreePhysicalMemory` (the value ad-hoc PowerShell checks read). Phases: no model loaded; `llama3.2:3b` loaded and idle at `num_ctx` 2304; one live S4' document (passes A and B, prompt 2.2, a train document outside the prompt subset); idle again. Result: `evals/results/dev/memory_measurement.json`, log `docs/progress/logs/run-memory-measurement.log`.

| Phase | psutil available, lowest | Windows free physical | Runner RSS |
|---|---|---|---|
| No model loaded | 3.57 GiB | 3.56 GiB | 0.05 GiB |
| Model loaded, idle | 2.96 GiB | 2.94 GiB | 0.70 GiB |
| During one S4' document | 2.75 GiB | 2.75 GiB | 0.91 GiB |

The two free-RAM measures agree within 0.02 GiB, so the gap between the "about 3.3 GiB" and "0.3 to 0.4 GiB" figures reported on 2026-11-07 is not a difference of definition. Explanation:

- The model itself costs about 0.6 to 0.9 GiB of system RAM at `num_ctx` 2304; its weights sit in VRAM.
- The 0.25 to 0.4 GiB lows were in runs with more memory in use: `num_ctx` 4096 or 8192 (runner RSS 2.8 to 3.5 GiB in those runs), every image loaded into the evaluation process (1.7 to 2.2 GiB, fixed in `9d1e4eb`), or train OCR running at the same time.
- The completed prompt-2.2 validation runs used `num_ctx` 2304 with no images, and their lowest free RAM was about 3.3 GiB.
- Two S4' attempts aborted at 0.35 and 0.37 GiB under that same lean configuration. Something outside the run took about 3 GiB for a while. It was not identified; candidates are other applications on this machine (VS Code, browsers, Defender). The statement "about 0.3 to 0.4 GiB with the model loaded" in the 2026-11-07 report was too general and is corrected here.

### llama3.2:3b S4h baseline on the train subset, 2026-11-08

Recorded as measured and not rerun: mean F1 0.578 (total, subtotal, tax, row-level), warm LLM p50 7.95 s and p95 19.73 s per document (both passes, load excluded), 3 memory aborts before the run that completed (records in `evals/results/aborted/`). Source: `evals/results/dev/prompt_round/cord_s4h_prompt_dev_train100_p2.2_v1_1_1.json`.

Why p95 is higher than S4' on validation (14.05 s): the medians are close (7.95 s against 7.68 s), so the shift is in the tail. On the train subset, 6 replies were truncated (generation ran to `num_predict` 1024) and 4 calls were retried, each a full extra call, against 1 and 1 on validation. With about 96 warm documents, p95 is set by the five or so slowest, which are those cases. The document sets also differ (train subset against validation). Nothing points to the machine running slower. Most timings in both files were recorded when each call was first made, some in runs that later aborted (labelled "mixed").

### S4h train run: 48 s against 10 s per document, explained, 2026-11-08

Latency per LLM call (generation time, load excluded), split by when each reply was recorded, never pooled (`evals/runners/segment_latency.py`, output `docs/progress/logs/s4h-train-all-segments.json`):

| Segment | Calls | p50 s | p95 s | Completion tokens p50 | Tokens/s median | Truncated |
|---|---|---|---|---|---|---|
| Before sleep, 21:11 to 21:40 UTC | 51 | 29.1 | 55.53 | 191 | 6.7 | 0 |
| After restart, from 05:44 UTC (at the time of writing) | 308 | 3.88 | 9.65 | 180 | 47.9 | 10 |

Replies were about the same length, but generation ran about 7 times slower before the sleep. Evidence:

- Ollama's server log for the 21:11 UTC load: `offloaded 29/29 layers to GPU`, and 2,916 MiB of VRAM left free. The model was fully on the GPU, so CPU offload is ruled out.
- Windows System log, Kernel-Power event 105: AC power went offline at 20:52:04 UTC (`AcOnline` false, battery 43,324 of 43,762) and came back at 05:42:29 UTC (`AcOnline` true, 4,446 of 43,762). Event 524 "Critical Battery Trigger Met" at 21:40:46 UTC was followed by sleep (event 42).

Explanation: the pre-sleep segment ran on battery, where the laptop GPU runs at a lower power limit, until the battery reached its critical level and the machine slept. The restart ran on AC. From the restart on, `ollama ps`, free RAM, pagefile use and GPU clocks are logged every 10 documents in `docs/progress/logs/s4h-train-all-monitor.txt`. The qwen3:4b token-measurement aborts (about 21:05 UTC) also happened on battery; they were memory aborts, so this does not change ADR-0012. Long runs need AC power.

## Decision

Docker-first for services (`postgres:16-alpine`, `redis:7-alpine`, both pulled), native Python and
Node for development. SQLite is allowed for unit tests only.

## Datasets

CORD v2 (`naver-clova-ix/cord-v2`): API reports public, ungated, `cc-by-4.0`; 2.3 GB of parquet
(test 234 MB, validation 242 MB, train 1.8 GB). All six data files later downloaded and matched
their published SHA-256 (a `/resolve/` request for the README returned 401 once; data files were unaffected).
