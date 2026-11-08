#!/usr/bin/env bash
# Log `ollama ps`, free RAM and pagefile use each time a run's log reports another 10 documents.
# When the run's log ends (EXIT=), release the keep-awake request and log that it was released.
#   scripts/monitor_run.sh <run log> <monitor log>
set -u
RUN_LOG=$1
OUT=$2
seen=""
echo "# monitor for $RUN_LOG, started $(date -u +%FT%TZ)" >> "$OUT"
snapshot() {
  {
    echo "== $(date -u +%FT%TZ) $1"
    ollama ps | sed 's/\x1b\[[0-9;?]*[A-Za-z]//g' | grep -v '^\s*$'
    powershell -NoProfile -Command "\$os = Get-CimInstance Win32_OperatingSystem; \$pf = Get-CimInstance Win32_PageFileUsage; 'free_ram_gib=' + [math]::Round(\$os.FreePhysicalMemory/1MB,3) + ' pagefile_used_mb=' + ((\$pf | Measure-Object CurrentUsage -Sum).Sum) + ' pagefile_peak_mb=' + ((\$pf | Measure-Object PeakUsage -Sum).Sum)"
    nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,clocks.sm,power.draw --format=csv,noheader 2>/dev/null | sed 's/^/gpu: /'
  } >> "$OUT" 2>&1
}
snapshot "start"
while true; do
  last=$(grep -E "processed [0-9]+" "$RUN_LOG" | tail -1)
  if [ -n "$last" ] && [ "$last" != "$seen" ]; then
    seen=$last
    snapshot "$last"
  fi
  if grep -q "^EXIT=" "$RUN_LOG"; then
    snapshot "run ended: $(grep '^EXIT=' "$RUN_LOG" | tail -1)"
    powershell -NoProfile -Command "\$p = Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'keep_awake.ps1' -and \$_.ProcessId -ne \$PID }; \$p | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }; 'keep-awake processes stopped: ' + @(\$p).Count; 'keep-awake processes left: ' + @(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'keep_awake.ps1' -and \$_.ProcessId -ne \$PID }).Count" >> "$OUT" 2>&1
    echo "== keep-awake release done $(date -u +%FT%TZ)" >> "$OUT"
    exit 0
  fi
  sleep 30
done
