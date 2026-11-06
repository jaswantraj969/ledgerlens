#!/usr/bin/env bash
# Local mirror of .github/workflows/ci.yml. Runs every step even after a failure, so one log
# shows the whole state, and ends with CI_LOCAL_EXIT=<code>. This is not a GitHub Actions run:
# it uses this machine's OS, tools and services.
set -u
cd "$(dirname "$0")/.." || exit 2
root=$PWD
failures=0

step() {
  local label=$1; shift
  printf '\n=== %s\n$ %s\n' "$label" "$*"
  "$@"
  local code=$?
  echo "STEP_EXIT[$label]=$code"
  [ "$code" -eq 0 ] || failures=$((failures + 1))
}

cd "$root/backend" || exit 2
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=.venv/bin/python
step ruff-check "$PY" -m ruff check . ../evals --config pyproject.toml
step ruff-format "$PY" -m ruff format --check .
step mypy "$PY" -m mypy
step pytest-coverage "$PY" -m pytest -q --cov=ledgerlens --cov-report=term

cd "$root/frontend" || exit 2
step npm-lint npm run lint
step npm-test npm test
step npm-build npm run build

cd "$root" || exit 2
GITLEAKS=$(command -v gitleaks || find "$HOME/.cache/pre-commit" -iname 'gitleaks*' -type f 2>/dev/null | head -1)
if [ -n "$GITLEAKS" ]; then
  step gitleaks-full-history "$GITLEAKS" detect --source . --no-banner --redact --log-opts=--all
else
  echo "STEP_EXIT[gitleaks-full-history]=not-found"
  failures=$((failures + 1))
fi

echo
echo "CI_LOCAL_EXIT=$failures"
exit "$failures"
