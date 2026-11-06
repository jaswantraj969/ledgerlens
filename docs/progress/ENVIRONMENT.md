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
| Missing | make, tesseract, psql, redis-server, gitleaks, ollama on PATH |

## Notes that affect the plan

- **Network is reachable but slow and uneven.** Single samples ranged from about 3 KB/s to 170 KB/s
  across PyPI, npm, GitHub, PyTorch and Ollama hosts. The lowest readings in the log (including
  0 B/s and 486 B/s) were taken while another install was using the link, so they are not
  baselines. Large downloads must be backgrounded and resumable.
- **Ollama is not usable as found.** Windows lists it as installed, but the install directory is
  gone. `~/.ollama/models` survives (2.2 GB: llama3.2, nomic-embed-text). Status: BLOCKED until a
  working binary exists, either by reinstalling or through the `ollama/ollama` image.
- **Installs need care on this link.** `uv` cannot resume a partial wheel and hung on dead
  connections, and archive errors appeared on two unrelated wheels. What worked: the default uv
  cache, a timeout per attempt, and `curl -C -` with SHA-256 checks for wheels over about 10 MB.
- **`make` is missing.** The Makefile stays as specified; Windows needs a documented equivalent.
- **PostgreSQL 18 is partly present** (`C:\Program Files\PostgreSQL\18`, pgAgent entry, no `psql`
  or `pg_ctl` in `bin`) and is not used.
- **Docker holds images from other projects.** They are left alone.

## Decision

Docker-first for services (`postgres:16-alpine`, `redis:7-alpine`, both pulled), native Python and
Node for development. SQLite is allowed for unit tests only.

## Datasets

CORD v2 (`naver-clova-ix/cord-v2`): API reports public, ungated, `cc-by-4.0`; 2.3 GB of parquet
(test 234 MB, validation 242 MB, train 1.8 GB). All six data files later downloaded and matched
their published SHA-256 (a `/resolve/` request for the README returned 401 once; data files were unaffected).
