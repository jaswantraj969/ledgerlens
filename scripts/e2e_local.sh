#!/usr/bin/env bash
# Run the Playwright flow against a local dev stack (not Docker): uvicorn API, RQ worker and the
# Vite dev server. Postgres and Redis come from `scripts/tasks.sh dev`. Everything started here is
# stopped on exit. Secrets are read from .env and never printed.
set -u
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export LEDGERLENS_DATABASE_URL="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5433/${POSTGRES_DB}"
export LEDGERLENS_REDIS_URL="redis://127.0.0.1:6380/0"
export LEDGERLENS_STORAGE_DIR="$PWD/var/e2e-storage"
export LEDGERLENS_EXTRACTION_MODE=rules

pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null; done
  # On Windows, uv starts python as a separate process that kill does not reach. Stop only the
  # processes this script started, matched by their command lines.
  if command -v powershell >/dev/null; then
    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'ledgerlens.api.app:create_app --factory --host 127.0.0.1 --port 8000|ledgerlens.workers.run|vite.+--port 5173' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
  fi
}
trap cleanup EXIT

bash scripts/tasks.sh dev >/dev/null
(cd backend && uv run --no-sync alembic upgrade head) || exit 1
(cd backend && exec uv run --no-sync uvicorn ledgerlens.api.app:create_app --factory --host 127.0.0.1 --port 8000) &
pids+=($!)
(cd backend && exec uv run --no-sync python -m ledgerlens.workers.run) &
pids+=($!)
(cd frontend && exec npx vite --host 127.0.0.1 --port 5173 --strictPort) &
pids+=($!)

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done
[ "${ready:-0}" = 1 ] || { echo "stack did not become ready"; exit 1; }
echo "local dev stack ready (API, worker, Vite)"
(cd frontend && E2E_BASE_URL=http://127.0.0.1:5173 npx playwright test)
