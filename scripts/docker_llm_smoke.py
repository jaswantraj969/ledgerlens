"""Smoke test: the containerised worker in LLM mode, calling Ollama on the host.

Run from the repository root, with the Compose stack up (web on LEDGERLENS_WEB_PORT):
    uv run --project backend --no-sync python scripts/docker_llm_smoke.py

1. Checks free RAM (at least 2 GiB) and that the worker container reaches the host's Ollama;
   if either fails it stops and records why (exit 2 for RAM, 3 for networking).
2. Recreates only the worker with LEDGERLENS_EXTRACTION_MODE=llm.
3. Uploads 3 CORD train images (the first 3 train ids) through the API and waits, with a hard
   deadline, for each job to finish.
4. Records job states and counts of field sources and decisions, never field values or text.
5. Always puts the worker back in its default rules mode.

Writes docs/progress/logs/docker-llm-smoke.json. Exit 0 only if all 3 jobs finished with fields
whose source is an LLM pass.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.datasets.cord import DEFAULT_RAW_DIR, iter_documents  # noqa: E402

API = "http://127.0.0.1:8000"
OUTPUT = ROOT / "docs" / "progress" / "logs" / "docker-llm-smoke.json"
COMPOSE = ["docker", "compose", "-f", "infra/docker-compose.yml", "--env-file", ".env"]
MIN_FREE_GIB = 2.0
DEADLINE_SECONDS = 900
TERMINAL = {"ready_for_review", "completed", "failed"}


def log(message: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message}", flush=True)


def worker(mode: str) -> int:
    env = os.environ | {"LEDGERLENS_EXTRACTION_MODE": mode}
    env.setdefault("LEDGERLENS_WEB_PORT", "8081")
    command = [*COMPOSE, "up", "-d", "--no-deps", "--wait", "--wait-timeout", "120", "worker"]
    done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)  # noqa: S603
    return done.returncode


def container_reaches_ollama() -> str | None:
    probe = (
        "import os,urllib.request,json;u=os.environ['LEDGERLENS_OLLAMA_URL'];"
        "print(json.load(urllib.request.urlopen(u+'/api/version',timeout=5))['version'])"
    )
    command = ["docker", "exec", "ledgerlens-worker-1", "python", "-c", probe]
    done = subprocess.run(  # noqa: S603 (fixed command)
        command, capture_output=True, text=True, check=False, timeout=30
    )
    return done.stdout.strip() if done.returncode == 0 else None


def train_images(directory: Path, count: int = 3) -> list[Path]:
    files = []
    for document in iter_documents("train", DEFAULT_RAW_DIR, with_images=True):
        data = document.image or b""
        suffix = ".png" if data.startswith(b"\x89PNG") else ".jpg"
        path = directory / f"cord-train-{document.document_id.split(':')[-1]}{suffix}"
        path.write_bytes(data)
        files.append(path)
        if len(files) == count:
            break
    return files


def run(summary: dict[str, Any]) -> int:
    free = psutil.virtual_memory().available / 2**30
    summary["free_ram_gib_before"] = round(free, 3)
    if free < MIN_FREE_GIB:
        summary["outcome"] = f"not run: free RAM {free:.2f} GiB below {MIN_FREE_GIB}"
        return 2
    version = container_reaches_ollama()
    summary["ollama_version_seen_from_worker"] = version
    if version is None:
        summary["outcome"] = "not run: the worker container cannot reach Ollama on the host"
        return 3
    if worker("llm") != 0:
        summary["outcome"] = "not run: the worker did not restart in llm mode"
        return 3
    log("worker recreated in llm mode")
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as temporary, httpx.Client(base_url=API, timeout=60) as http:
        email = f"smoke-{uuid.uuid4().hex[:8]}@example.test"
        account = {"organization": "LLM smoke", "email": email, "password": uuid.uuid4().hex}
        token = http.post("/auth/register", json=account).json()
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        documents = []
        for path in train_images(Path(temporary)):
            with path.open("rb") as handle:
                reply = http.post(
                    "/documents", headers=headers, files={"file": (path.name, handle)}
                )
            reply.raise_for_status()
            documents.append(reply.json())
            log(f"uploaded {path.name}")
        results = []
        for document in documents:
            status = document["status"]
            while status not in TERMINAL and time.monotonic() - started < DEADLINE_SECONDS:
                time.sleep(5)
                status = http.get(f"/documents/{document['id']}", headers=headers).json()["status"]
            job = http.get(f"/jobs/{document['job_id']}", headers=headers).json()
            fields = http.get(f"/documents/{document['id']}/fields", headers=headers)
            rows = fields.json() if fields.status_code == 200 else []
            results.append({
                "file": document["filename"],
                "status": status,
                "job_state": job.get("state"),
                "job_error_code": job.get("error_code"),
                "attempts": job.get("attempts"),
                "field_sources": dict(Counter(r["source"] for r in rows)),
                "field_decisions": dict(Counter(r["decision"] for r in rows)),
            })  # fmt: skip
            log(f"{document['filename']}: {status}, sources {results[-1]['field_sources']}")
    summary["documents"] = results
    summary["elapsed_seconds"] = round(time.monotonic() - started, 1)
    summary["free_ram_gib_after"] = round(psutil.virtual_memory().available / 2**30, 3)
    llm_used = all(
        r["status"] in {"ready_for_review", "completed"}
        and any(source.startswith("llm") for source in r["field_sources"])
        for r in results
    )
    summary["outcome"] = "passed" if llm_used and len(results) == 3 else "failed"
    return 0 if summary["outcome"] == "passed" else 1


def main() -> int:
    summary: dict[str, Any] = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        code = run(summary)
    except Exception as error:  # record the failure, then restore the worker
        summary["outcome"] = f"failed: {type(error).__name__}: {str(error)[:200]}"
        code = 1
    finally:
        summary["worker_restored_to_rules"] = worker("rules") == 0
        log(f"worker restored to rules mode: {summary['worker_restored_to_rules']}")
        summary["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        OUTPUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"outcome: {summary['outcome']}")
    return code


if __name__ == "__main__":
    sys.exit(main())
