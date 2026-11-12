"""Assign whole CORD layout groups to calibration-train or evaluation, for the grouped S5 variant.

Written before any S5 result exists. Groups are drawn with a fixed seed; nothing about results
or group contents other than their id is used. Evaluation groups are never seen by a calibrator
or a threshold.
"""

import collections
import hashlib
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GROUPS_FILE = ROOT / "evals" / "splits" / "cord_v2" / "layout_groups.json"
OUTPUT = ROOT / "evals" / "splits" / "cord_v2" / "layout_group_holdout.json"
SEED = 20261107
EVALUATION_GROUP_COUNT = 4


def ids_hash(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} exists: the assignment is fixed once written")
    groups_payload = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
    assignments: dict[str, int] = groups_payload["assignments"]
    group_ids = sorted(set(assignments.values()))
    evaluation = sorted(random.Random(SEED).sample(group_ids, EVALUATION_GROUP_COUNT))  # noqa: S311
    roles = {g: "evaluation" if g in evaluation else "calibration" for g in group_ids}
    members: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for document_id, group in assignments.items():
        split = document_id.split(":")[1]
        members[(split, roles[group])].append(document_id)
    payload: dict[str, Any] = {
        "seed": SEED,
        "method": f"random.Random({SEED}).sample(sorted group ids, {EVALUATION_GROUP_COUNT})",
        "layout_groups_sha256": hashlib.sha256(GROUPS_FILE.read_bytes()).hexdigest(),
        "group_roles": {str(g): roles[g] for g in group_ids},
        "use": {
            "calibrator_fit": "train documents in calibration groups",
            "threshold_choice": "validation documents in calibration groups",
            "evaluation": "test documents in evaluation groups, read once at the end",
        },
        "counts": {
            f"{split}/{role}": {"n": len(ids), "sha256": ids_hash(ids)}
            for (split, role), ids in sorted(members.items())
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("evaluation groups", evaluation)
    print({key: value["n"] for key, value in payload["counts"].items()})


if __name__ == "__main__":
    main()
