#!/usr/bin/env bash
# Log `ollama ps`, free RAM, pagefile use and GPU state each time any attempt log matching a glob
# reports another 10 documents, until the summary log has an EXIT= line.
#   scripts/monitor_run.sh '<attempt log glob>' <summary log> <monitor log>
set -u
GLOB=$1
SUMMARY=$2
OUT=$3
seen=""
echo "# monitor started $(date -u +%FT%TZ) for $GLOB" >> "$OUT"
snapshot() {
  {
    echo "== $(date -u +%FT%TZ) $1"
    ollama ps | sed 's/\x1b\[[0-9;?]*[A-Za-z]//g' | grep -v '^\s*$'
    powershell -NoProfile -Command "\$os = Get-CimInstance Win32_OperatingSystem; \$pf = Get-CimInstance Win32_PageFileUsage; 'free_ram_gib=' + [math]::Round(\$os.FreePhysicalMemory/1MB,3) + ' pagefile_used_mb=' + ((\$pf | Measure-Object CurrentUsage -Sum).Sum)"
    nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,clocks.sm,power.draw --format=csv,noheader 2>/dev/null | sed 's/^/gpu: /'
  } >> "$OUT" 2>&1
}
snapshot "start"
while ! grep -q "^EXIT=" "$SUMMARY" 2>/dev/null; do
  latest=$(ls -t $GLOB 2>/dev/null | head -1)
  if [ -n "$latest" ]; then
    last=$(grep -E "processed [0-9]+" "$latest" | tail -1)
    key="$latest $last"
    if [ -n "$last" ] && [ "$key" != "$seen" ]; then
      seen=$key
      snapshot "$(basename "$latest"): $last"
    fi
  fi
  sleep 30
done
snapshot "run ended: $(grep '^EXIT=' "$SUMMARY")"
grep "keep-awake" "$SUMMARY" >> "$OUT"
