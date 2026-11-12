"""Write the README paragraph and the limitations line for the duplicate-exclusion check, from
evals/results/final/cord_test_dedup_sensitivity_v1_1_1.json and the duplicate log. Each goes
between marker comments, so the text is regenerated, never edited by hand.

    python -m evals.runners.make_dedup_text
"""

import json
import re
from pathlib import Path
from typing import Any

from evals.atomic import write_text_atomic

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "evals" / "results" / "final" / "cord_test_dedup_sensitivity_v1_1_1.json"
DUPLICATES = ROOT / "docs" / "progress" / "logs" / "cord-cross-split-duplicates.txt"
NAMES = {"total_amount": "total", "subtotal": "subtotal", "tax_amount": "tax", "rows": "row-level"}
START, END = "<!-- dedup-sensitivity:start -->", "<!-- dedup-sensitivity:end -->"


def duplicate_counts() -> tuple[int, int]:
    """(train-validation groups, within-split groups) under the token-text definition."""
    text = DUPLICATES.read_text(encoding="utf-8")
    block = text.split("identical token text:")[1].split("identical full OCR output:")[0]
    within = int(re.search(r"(\d+) within one split only", block)[1])  # type: ignore[index]
    lines = [line for line in block.splitlines() if line.startswith("  cord-v2:")]
    train_validation = sum("train" in line and "validation" in line and "test" not in line
                           for line in lines)  # fmt: skip
    return train_validation, within


def ordering_sentence(result: dict[str, Any]) -> str:
    rows = result["s1_vs_s4h"]
    changed = [r for r in rows if r["ordering_changes"]]
    parts = []
    for row in rows:
        b = row["without_excluded"]
        parts.append(f"{NAMES[row['field']]} {b['S1']:.3f} against {b['S4h']:.3f}")
    verdict = (
        "no S1-against-S4h ordering changes on any field"
        if not changed
        else "the S1-against-S4h ordering changes on "
        + ", ".join(NAMES[r["field"]] for r in changed)
    )
    return f"{verdict} (on the 93, S1 against S4h: " + "; ".join(parts) + ")."


def paragraph(result: dict[str, Any]) -> str:
    train_validation, within = duplicate_counts()
    s5 = result["s5"]
    header = {name: s5[name]["header"]["targets"]["0.98"] for name in s5}
    s5_text = "; ".join(
        f"{name} header automation {v['automation_rate']:.3f} at precision "
        f"{v['achieved_precision']:.3f}"
        for name, v in header.items()
    )
    return (
        "**Duplicate-exclusion check (post hoc, [addendum 01](docs/evaluation/addendum-01-"
        "duplicate-sensitivity.md)).** Leaving out the 7 test documents with a near-copy in train "
        f"or validation (n = 93): {ordering_sentence(result)} At the 0.98 target on the 93: "
        f"{s5_text}. The primary results above are unchanged. CORD also has "
        f"{train_validation} train-validation groups and {within} within-split groups with "
        "identical OCR token text. So validation choices were made partly on near-copies of "
        "train, and the document-bootstrap intervals, which treat documents as independent, are "
        "slightly optimistic. Source: [cord_test_dedup_sensitivity_v1_1_1.md]"
        "(evals/results/final/cord_test_dedup_sensitivity_v1_1_1.md)."
    )


def limitation(result: dict[str, Any]) -> str:
    train_validation, within = duplicate_counts()
    sentence = ordering_sentence(result)
    return (
        "Duplicate-exclusion check (post hoc, `docs/evaluation/addendum-01-duplicate-"
        f"sensitivity.md`): {sentence[0].upper()}{sentence[1:]} There are also {train_validation} "
        f"train-validation and {within} within-split groups of near-copies, so validation choices "
        "rest partly on near-copies of train, and the bootstrap intervals are slightly "
        "optimistic. No clustered bootstrap was run."
    )


def replace_block(path: Path, text: str, anchor: str) -> None:
    content = path.read_text(encoding="utf-8")
    block = f"{START}\n{text}\n{END}"
    if START in content:
        content = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, content,
                         flags=re.S)  # fmt: skip
    else:
        if anchor not in content:
            raise SystemExit(f"anchor not found in {path}")
        content = content.replace(anchor, f"{anchor}\n\n{block}", 1)
    write_text_atomic(path, content)


def main() -> None:
    result = json.loads(SOURCE.read_text(encoding="utf-8"))
    replace_block(
        ROOT / "README.md",
        paragraph(result),
        "They are included in every figure here, as read ([limitations](docs/limitations.md)).",
    )
    replace_block(
        ROOT / "docs" / "limitations.md",
        limitation(result),
        "or the S1 rules (tuned on validation).",
    )
    print("wrote the README paragraph and the limitations line")


if __name__ == "__main__":
    main()
