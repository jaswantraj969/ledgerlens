# Final CORD test read, unattended (docs/evaluation/final-test-protocol.md).
# Run from the repository root in Windows Terminal, with VS Code and Claude Code closed:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_final_test.ps1
# Add -CheckOnly to run the pre-flight and flag checks without reading test.
# Exit codes: 0 done, 10 pre-flight failed (test not read), 11 a step failed, 12 interrupted.
# Rerunning the same command resumes: steps whose output exists are skipped.
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-Location -Path (Split-Path -Parent $PSScriptRoot)
$arguments = @('run', '--project', 'backend', '--no-sync', 'python', '-u', '-m', 'evals.runners.run_final_test')
if ($CheckOnly) { $arguments += '--check-only' }
& uv @arguments
$code = $LASTEXITCODE
Write-Host "EXIT=$code"
exit $code
