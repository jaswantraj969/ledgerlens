#!/usr/bin/env bash
# Regression tests for run_logged.sh. Uses a real native child because a shell child hid a
# bug: native Windows programs overwrote the wrapper's log lines.
cd "$(dirname "$0")/.." || exit 2
PY=backend/.venv/Scripts/python.exe
[ -x "$PY" ] || PY=backend/.venv/bin/python
export RUN_LOG_DIR
RUN_LOG_DIR=$(mktemp -d)
failures=0

check() {
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: expected '$3', got '$2'"; failures=$((failures + 1)); fi
}

emit='import time
for i in range(6):
    print("line", i, flush=True); time.sleep(1)'

HEARTBEAT_EVERY=2 POLL=1 bash scripts/run_logged.sh native 30 4 -- "$PY" -u -c "$emit"
check "native child exit code" "$?" 0
log="$RUN_LOG_DIR/run-native.log"
check "every child line kept" "$(grep -c '^line [0-9]$' "$log")" 6
check "heartbeats survive" "$([ "$(grep -c '^HEARTBEAT ' "$log")" -ge 2 ] && echo yes)" yes
check "log ends in EXIT=0" "$(tail -1 "$log")" "EXIT=0"
check "no corrupted lines" "$(grep -vcE '^(START|HEARTBEAT|END|EXIT=|line |import time|for i in|    print)' "$log")" 0
check "steady output never stalls" "$(grep -c '^STALLED' "$log")" 0

POLL=1 bash scripts/run_logged.sh fail 30 10 -- "$PY" -c "raise SystemExit(7)"
check "real failure code" "$?" 7
check "log records failure" "$(tail -1 "$RUN_LOG_DIR/run-fail.log")" "EXIT=7"

POLL=1 bash scripts/run_logged.sh stall 60 3 -- "$PY" -c "import time; time.sleep(40)"
check "silent child is stopped" "$?" 125
check "log records stall" "$(tail -1 "$RUN_LOG_DIR/run-stall.log")" "EXIT=125"

POLL=1 bash scripts/run_logged.sh limit 3 60 -- "$PY" -c "import time; time.sleep(40)"
check "hard timeout" "$?" 124

printf '{"x":1}\n' > "$RUN_LOG_DIR/watched"
POLL=1 bash scripts/run_logged.sh watched 30 3 "$RUN_LOG_DIR/growing" -- bash -c \
  'for i in 1 2 3 4 5 6; do printf "%s" "$i" >> "$RUN_LOG_DIR/growing"; sleep 1; done'
check "growing watch path counts as progress" "$?" 0

leftover=$(find "$RUN_LOG_DIR" -name '*.pid' -o -name '*.code' | wc -l)
check "no temp files left" "$leftover" 0
rm -rf "$RUN_LOG_DIR"
echo "RUN_LOGGED_TEST_EXIT=$failures"
exit "$failures"
