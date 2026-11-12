#!/usr/bin/env bash
# Final CORD test read (docs/evaluation/final-test-protocol.md); same as scripts/run_final_test.ps1.
#   bash scripts/run_final_test.sh [--check-only]
# Exit codes: 0 done, 10 pre-flight failed (test not read), 11 a step failed, 12 interrupted.
set -u
cd "$(dirname "$0")/.."
uv run --project backend --no-sync python -u -m evals.runners.run_final_test "$@"
code=$?
echo "EXIT=$code"
exit $code
