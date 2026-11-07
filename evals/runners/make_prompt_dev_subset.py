"""Draw the fixed prompt-development subset: 100 CORD train documents, seeded.

Prompts are developed on this subset only. Validation is read once, for the final prompt.
"""

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "evals" / "splits" / "cord_v2" / "ids.json"
OUTPUT = ROOT / "evals" / "splits" / "cord_v2" / "prompt_dev_train100.json"
SEED = 20261107
SIZE = 100


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} exists: the subset is fixed once written")
    train = json.loads(SPLITS.read_text(encoding="utf-8"))["train"]["ids"]
    ids = sorted(random.Random(SEED).sample(sorted(train), SIZE))  # noqa: S311 - not security
    payload = {
        "split": "train",
        "seed": SEED,
        "method": f"random.Random({SEED}).sample(sorted train ids, {SIZE})",
        "n": len(ids),
        "sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
        "ids": ids,
    }
    OUTPUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("n", len(ids), "sha256", payload["sha256"])


if __name__ == "__main__":
    main()
