"""Download CORD v2 (CC BY 4.0) from Hugging Face at a pinned revision, and verify it.

    python scripts/download_cord.py            # download what is missing, then verify all six
    python scripts/download_cord.py --verify   # verify existing files only; no network

Dataset: naver-clova-ix/cord-v2 (Park et al., CORD: A Consolidated Receipt Dataset for
Post-OCR Parsing, 2019), licence CC BY 4.0. Files go to data/cord-v2/raw/ (gitignored, never
committed). Each file is checked against evals/datasets/checksums/cord-v2.sha256; a mismatch is
an error. Downloads resume from a .part file. Standard library only.
"""

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "cord-v2" / "raw"
CHECKSUMS = ROOT / "evals" / "datasets" / "checksums" / "cord-v2.sha256"
REPOSITORY = "naver-clova-ix/cord-v2"
REVISION = "7f0115a4b758a71d6473b8d085751692da2fef98"  # dataset commit, last modified 2022-07-19
URL = "https://huggingface.co/datasets/{repo}/resolve/{revision}/data/{name}"
CHUNK = 1 << 20


def expected() -> dict[str, str]:
    """File name to SHA-256, from the committed checksum list."""
    pairs = (line.split() for line in CHECKSUMS.read_text(encoding="utf-8").splitlines() if line)
    return {name: digest for digest, name in pairs}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def download(name: str, target: Path) -> None:
    partial = target.with_suffix(target.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    url = URL.format(repo=REPOSITORY, revision=REVISION, name=name)
    request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (fixed https URL)
        mode = "ab" if offset and response.status == 206 else "wb"
        with partial.open(mode) as handle:
            while block := response.read(CHUNK):
                handle.write(block)
    partial.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="check existing files; no network")
    parser.add_argument("--dest", type=Path, default=DEST)
    arguments = parser.parse_args()
    arguments.dest.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, digest in sorted(expected().items()):
        target = arguments.dest / name
        if not target.exists():
            if arguments.verify:
                print(f"missing  {name}")
                failures += 1
                continue
            print(f"download {name}", flush=True)
            download(name, target)
        actual = sha256(target)
        ok = actual == digest
        failures += not ok
        print(f"{'ok      ' if ok else 'MISMATCH'} {name}")
    print("all six files verified" if not failures else f"{failures} file(s) missing or wrong")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
