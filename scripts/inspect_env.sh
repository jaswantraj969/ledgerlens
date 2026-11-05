#!/usr/bin/env bash
# Records the facts behind docs/progress/ENVIRONMENT.md. Read-only apart from its stdout.
set -u
echo "# captured: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "## os";      uname -srm
powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).Caption + ' ' + (Get-CimInstance Win32_OperatingSystem).Version"
echo "## hardware"
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | ForEach-Object { \$_.Name + ' cores=' + \$_.NumberOfCores + ' threads=' + \$_.NumberOfLogicalProcessors }; 'ram_gb=' + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1); Get-PSDrive -PSProvider FileSystem | ForEach-Object { \$_.Name + ': free_gb=' + [math]::Round(\$_.Free/1GB,1) }"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1
echo "## tools"
for c in python uv node npm docker git make tesseract ollama psql redis-server gitleaks; do
  printf '%s: ' "$c"; if command -v "$c" >/dev/null; then "$c" --version 2>&1 | head -1; else echo MISSING; fi
done
docker compose version 2>&1
docker info --format 'docker_server={{.ServerVersion}} mem={{.MemTotal}} cpus={{.NCPU}}' 2>&1 | head -1
echo "## git";     git config user.name; git config user.email
echo "## network"
for u in https://pypi.org/simple/pydantic/ https://registry.npmjs.org/typescript/-/typescript-5.6.2.tgz https://huggingface.co/api/datasets/naver-clova-ix/cord-v2 https://ollama.com/download/OllamaSetup.exe; do
  curl -s -o /dev/null -m 10 -L -w "%{http_code} %{speed_download}B/s $u\n" "$u"
done
