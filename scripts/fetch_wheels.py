"""Fetch pinned wheels with resumable curl and verify them against PyPI's sha256.

Usage: fetch_wheels.py <wheelhouse> <platform-substring> name==version [name==version ...]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

house = pathlib.Path(sys.argv[1])
platform = sys.argv[2]
house.mkdir(parents=True, exist_ok=True)


def run_curl(args: list[str]) -> int:
    return subprocess.run(["curl", "-sS", "-L", "--retry", "30", "--retry-delay", "10",
                           "--retry-all-errors", "--speed-limit", "256", "--speed-time", "90",
                           *args]).returncode


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


failed = []
for spec in sys.argv[3:]:
    name, version = spec.split("==")
    meta = house / f"{name}-{version}.json"
    if run_curl(["-o", str(meta), f"https://pypi.org/pypi/{name}/{version}/json"]) != 0:
        failed.append(spec); continue
    urls = json.loads(meta.read_text(encoding="utf-8"))["urls"]
    wheels = [u for u in urls if u["filename"].endswith(".whl")
              and (platform in u["filename"] or "py3-none-any" in u["filename"])
              and any(tag in u["filename"] for tag in ("cp312", "py3-none", "abi3"))]
    if not wheels:
        print("NO WHEEL", spec, flush=True); failed.append(spec); continue
    wheel = wheels[0]
    target = house / wheel["filename"]
    for attempt in range(1, 41):
        if target.exists() and target.stat().st_size >= wheel["size"]:
            break
        run_curl(["-C", "-", "-o", str(target), wheel["url"]])
    ok = target.exists() and sha256(target) == wheel["digests"]["sha256"]
    print("OK " if ok else "BAD", wheel["filename"], flush=True)
    if not ok:
        failed.append(spec)
print("DONE failed=" + ",".join(failed), flush=True)
sys.exit(1 if failed else 0)
