#!/usr/bin/env bash
# Run a long command under a hard timeout and a stall detector.
#
#   scripts/run_logged.sh NAME TIMEOUT_SECONDS STALL_SECONDS [WATCH_PATH] -- COMMAND...
#
# Writes docs/progress/logs/run-NAME.log. Adds a HEARTBEAT line at least every 4 minutes and
# always ends the log with EXIT=<code>. That line is the authoritative result: a wrapper's own
# exit status or a job-completion notice is not. EXIT=125 means the stall detector stopped it.
# Progress means output grew or WATCH_PATH (a file or directory) grew.
set -u
name=$1; limit=$2; stall=$3; shift 3
watch=""
if [ "$1" != "--" ]; then watch=$1; shift; fi
shift

root=$(cd "$(dirname "$0")/.." && pwd)
log="$root/docs/progress/logs/run-$name.log"
heartbeat_every=240
poll=15

: > "$log"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
append_meta() { printf '%s\n' "$1" >> "$log"; meta_bytes=$((meta_bytes + ${#1} + 1)); }
progress() {
  local size watched=0
  size=$(wc -c < "$log")
  [ -n "$watch" ] && [ -e "$watch" ] && watched=$(du -sb "$watch" 2>/dev/null | cut -f1)
  echo $((size - meta_bytes + watched))
}

meta_bytes=0
append_meta "START $(stamp) timeout=${limit}s stall=${stall}s cmd: $*"
timeout -k 15 "$limit" "$@" >> "$log" 2>&1 &
pid=$!

last_progress=$(progress)
last_change=$SECONDS
last_heartbeat=$SECONDS
stalled=0
while kill -0 "$pid" 2>/dev/null; do
  sleep "$poll"
  current=$(progress)
  if [ "$current" != "$last_progress" ]; then
    last_progress=$current
    last_change=$SECONDS
  fi
  if [ $((SECONDS - last_heartbeat)) -ge "$heartbeat_every" ]; then
    append_meta "HEARTBEAT $(stamp) elapsed=${SECONDS}s progress=$current idle=$((SECONDS - last_change))s"
    last_heartbeat=$SECONDS
  fi
  if [ $((SECONDS - last_change)) -ge "$stall" ]; then
    append_meta "STALLED $(stamp) no progress for ${stall}s"
    stalled=1
    kill "$pid" 2>/dev/null
    break
  fi
done
wait "$pid"
code=$?
[ "$stalled" -eq 1 ] && code=125
append_meta "END $(stamp) elapsed=${SECONDS}s"
append_meta "EXIT=$code"
exit "$code"
