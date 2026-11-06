"""Write the SROIE vendor-grouped split. Only IDs and anonymous group numbers are saved."""

import collections
import hashlib
import json
from pathlib import Path

from evals.datasets.sroie import load_documents, split_payload

OUTPUT = Path(__file__).resolve().parents[1] / "splits" / "sroie" / "vendor_groups.json"


def main() -> None:
    payload = split_payload(load_documents())
    documents = payload["documents"]
    by_split: dict[str, list[str]] = collections.defaultdict(list)
    groups: dict[str, set[int]] = collections.defaultdict(set)
    for document_id, row in documents.items():
        by_split[row["split"]].append(document_id)
        groups[row["split"]].add(row["vendor_group"])
    payload["splits"] = {
        name: {
            "n": len(ids),
            "vendors": len(groups[name]),
            "sha256": hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest(),
        }
        for name, ids in sorted(by_split.items())
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="\n")

    sizes = collections.Counter(row["vendor_group"] for row in documents.values())
    print("documents", len(documents), "vendor groups", len(sizes))
    print("largest groups", [count for _, count in sizes.most_common(5)])
    print("single-document groups", sum(count == 1 for count in sizes.values()))
    print("splits", {k: (v["n"], v["vendors"]) for k, v in payload["splits"].items()})


if __name__ == "__main__":
    main()
