# LLM mode inside Docker: smoke test on 3 CORD train documents, with the worker container calling
# Ollama on the host. Run from the repository root in Windows Terminal, with VS Code closed:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_docker_llm_smoke.ps1
# Needs: Docker Desktop running, Ollama running with llama3.2:3b pulled, .env present, and the
# CORD files in data/cord-v2/raw (python scripts/download_cord.py).
# The Python script stops before doing anything if free RAM is under 2 GiB (exit 2) or the worker
# cannot reach Ollama (exit 3). This wrapper adds a hard timeout and always puts the worker back
# in rules mode. Output: docs/progress/logs/docker-llm-smoke.json and docker-llm-smoke.log.
param([int]$TimeoutSeconds = 1200, [int]$WebPort = 0)
$ErrorActionPreference = 'Stop'
Set-Location -Path (Split-Path -Parent $PSScriptRoot)
$log = 'docs\progress\logs\docker-llm-smoke.log'
if ($WebPort -gt 0) { $env:LEDGERLENS_WEB_PORT = "$WebPort" }
$compose = @('compose', '-f', 'infra/docker-compose.yml', '--env-file', '.env')

function Write-Log([string]$message) {
  $line = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') + ' ' + $message
  Write-Host $line
  Add-Content -Path $log -Value $line -Encoding utf8
}

Set-Content -Path $log -Value '' -Encoding utf8
Write-Log "START commit $(git rev-parse --short HEAD); hard timeout $TimeoutSeconds s"
Write-Log 'bringing the Compose stack up (rules mode)'
& docker @compose up -d --wait --wait-timeout 300 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Log 'the Compose stack did not become healthy'; Write-Log 'EXIT=4'; exit 4 }

$output = Join-Path $env:TEMP "ledgerlens-llm-smoke-$PID.txt"
$process = Start-Process -FilePath 'uv' -NoNewWindow -PassThru -RedirectStandardOutput $output `
  -ArgumentList @('run', '--project', 'backend', '--no-sync', 'python', 'scripts/docker_llm_smoke.py')
if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
  Write-Log "timed out after $TimeoutSeconds s; stopping the smoke test"
  & taskkill /PID $process.Id /T /F 2>&1 | Out-Null
  $code = 124
} else {
  $code = $process.ExitCode
}
if (Test-Path $output) { Get-Content $output | ForEach-Object { Write-Log $_ }; Remove-Item $output }

# Always restore the default rules mode, also after a timeout.
$env:LEDGERLENS_EXTRACTION_MODE = 'rules'
& docker @compose up -d --no-deps --wait --wait-timeout 120 worker 2>&1 | Out-Null
Write-Log "worker restored to rules mode: $($LASTEXITCODE -eq 0)"
Write-Log "EXIT=$code (0 passed, 1 failed, 2 not run: free RAM, 3 not run: networking, 124 timed out)"
exit $code
