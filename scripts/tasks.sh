#!/usr/bin/env bash
# Task runner: the single source of truth for project commands.
# The Makefile calls this, so `make test` and `bash scripts/tasks.sh test` do the same thing,
# and Windows needs only Git Bash, not GNU make.
set -u
cd "$(dirname "$0")/.." || exit 2
root=$PWD

python=backend/.venv/Scripts/python.exe
[ -x "$python" ] || python=backend/.venv/bin/python
separator=":"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) separator=";" ;; esac
export PYTHONPATH="$root$separator$root/backend/src"
compose=(docker compose -f infra/docker-compose.yml --env-file .env)

usage() {
  echo "usage: scripts/tasks.sh <dev|up|down|test|lint|typecheck|ci|eval-smoke|tables|reproduce>"
}

case "${1:-}" in
  dev) "${compose[@]}" up -d --wait postgres redis ;;
  up) "${compose[@]}" up -d --build --wait --wait-timeout 300 ;;
  down) "${compose[@]}" down ;;
  test)
    (cd backend && ../"$python" -m pytest -q) && npm --prefix frontend test
    ;;
  lint)
    (cd backend &&
      ../"$python" -m ruff check . ../evals --config pyproject.toml &&
      ../"$python" -m ruff format --check . ../evals --config pyproject.toml)
    ;;
  typecheck) (cd backend && ../"$python" -m mypy) ;;
  ci)
    # Written outside the repository first: pre-commit fails on files that change during a run.
    log=$(mktemp)
    bash scripts/ci_local.sh > "$log" 2>&1
    code=$?
    { cat "$log"; echo "COMMIT=$(git rev-parse HEAD)"; } > docs/progress/logs/ci-local.txt
    rm -f "$log"
    tail -14 docs/progress/logs/ci-local.txt
    exit "$code"
    ;;
  eval-smoke)
    # Offline by design: no model, no network, and no licensed dataset.
    "$python" -m evals.runners.run_synthetic --smoke
    ;;
  tables)
    "$python" -m evals.runners.make_tables evals/results/cord_s1_v1.json evals/results/cord_s1_v1_1.json
    "$python" -m evals.runners.make_tables evals/results/dev/cord_s*_validation_v1_1.json
    "$python" -m evals.runners.make_tables evals/results/cord_s1_v1_1_1.json evals/results/dev/cord_s*_validation_v1_1_1.json
    "$python" -m evals.runners.make_synthetic_table evals/results/synthetic_s1_v1_1.json
    ;;
  reproduce)
    # Rebuilds validation results from the OCR and replay caches, then regenerates tables.
    # It never reads the test split, and a replay miss counts as a failed extraction.
    for system in S1 S2 S3 S4; do
      flags=()
      [ "$system" = S1 ] || flags=(--replay)
      "$python" -m evals.runners.run_cord --system "$system" --split validation "${flags[@]}" || exit $?
    done
    "$0" tables
    "$python" -m evals.runners.make_validation_comparison || exit $?
    "$python" -m evals.runners.make_s5_table s1 s4h || exit $?
    # Final test tables and figure, from saved result files only (no test data is read).
    "$python" -m evals.runners.make_final_tables || exit $?
    ;;
  *) usage; exit 2 ;;
esac
