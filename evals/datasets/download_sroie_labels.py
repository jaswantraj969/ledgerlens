"""Fetch SROIE key files only, from a community mirror, into data/sroie/key (gitignored).

No images are fetched. SROIE's terms are unverified, so it is treated as research-only: see
LICENSES.md. Nothing downloaded here may be committed or used in the public demo. Files are
checked against the git blob hash from the tree listing, and finished files are skipped, so
a run can resume.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = "zzzDavid/ICDAR-2019-SROIE"
BRANCH = "master"
TREE_URL = f"https://api.github.com/repos/{REPOSITORY}/git/trees/{BRANCH}?recursive=1"
RAW_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}/"
OUTPUT = Path(__file__).resolve().parents[2] / "data" / "sroie" / "key"


def curl(url: str, target: Path) -> bool:
    command = ["curl", "-sS", "-L", "-m", "40", "--retry", "4", "-o", str(target), url]
    return subprocess.run(command, check=False).returncode == 0  # noqa: S603


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(  # noqa: S324 - git object id, not security
        f"blob {len(data)}\0".encode() + data
    ).hexdigest()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    listing = OUTPUT.parent / "tree.json"
    if not curl(TREE_URL, listing):
        print("could not list the repository")
        return 1
    tree = json.loads(listing.read_text(encoding="utf-8"))
    if tree.get("truncated"):
        print("tree listing truncated")
        return 1
    entries = [e for e in tree["tree"] if e["path"].startswith("data/key/")]
    print("key files listed:", len(entries), flush=True)
    failed = 0
    for index, entry in enumerate(entries, start=1):
        target = OUTPUT / Path(entry["path"]).name
        if target.exists() and blob_sha(target) == entry["sha"]:
            continue
        if not curl(RAW_URL + entry["path"], target) or blob_sha(target) != entry["sha"]:
            target.unlink(missing_ok=True)
            failed += 1
        if index % 50 == 0:
            print(f"checked {index}, failed {failed}", flush=True)
    print(f"done: {len(entries)} listed, {failed} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
