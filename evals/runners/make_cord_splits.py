"""Write CORD split ID lists, their hashes, and layout group assignments.

Group centroids are fitted on train only. Validation and test join the nearest centroid.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from evals.datasets.cord import iter_documents
from evals.grouping import GROUP_COUNT, GROUP_SEED, fit_groups, layout_descriptor

OUTPUT = Path(__file__).resolve().parents[1] / "splits" / "cord_v2"


def ids_hash(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ids: dict[str, list[str]] = {}
    descriptors: dict[str, np.ndarray] = {}
    for split in ("train", "validation", "test"):
        documents = list(iter_documents(split, with_images=False))
        ids[split] = [document.document_id for document in documents]
        descriptors[split] = np.array(
            [layout_descriptor(d.word_boxes, d.width, d.height) for d in documents]
        )

    model = fit_groups(descriptors["train"])
    groups = {
        document_id: int(group)
        for split, values in descriptors.items()
        for document_id, group in zip(ids[split], model.predict(values), strict=True)
    }
    (OUTPUT / "ids.json").write_text(
        json.dumps(
            {
                split: {"n": len(values), "sha256": ids_hash(values), "ids": sorted(values)}
                for split, values in ids.items()
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "layout_groups.json").write_text(
        json.dumps(
            {
                "method": "k-means on word-position grid, fitted on train only; see evaluation.md",
                "k": GROUP_COUNT,
                "seed": GROUP_SEED,
                "assignments": groups,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for split, values in ids.items():
        print(split, len(values), ids_hash(values)[:16])


if __name__ == "__main__":
    main()
