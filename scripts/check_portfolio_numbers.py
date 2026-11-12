"""Check that every number in the portfolio texts appears in evals/results/final/.

    python scripts/check_portfolio_numbers.py

Scans the body of docs/portfolio/{summary,upwork-entry,case-study}.md (the text before the
"## Sources" heading) for numbers, and reports any that occur in no file under
evals/results/final/. Numbers that are names, not results, are listed in NOT_RESULTS. Also
prints the summary's word count. Exit 1 if any number is unmatched or the summary is over 150
words.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "evals" / "results" / "final"
TEXTS = ("summary.md", "upwork-entry.md", "case-study.md")
# Names and identifiers, not results: model size (llama3.2:3b), year and licence (CC BY 4.0),
# prompt version, protocol targets and list numbering.
NOT_RESULTS = {"3", "3.2", "2019", "4.0", "2.2", "1", "2", "4", "0.98", "0.99"}
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")


def main() -> int:
    corpus = "".join(
        p.read_text(encoding="utf-8") for p in FINAL.rglob("*") if p.suffix in {".md", ".json"}
    )
    failures = 0
    for name in TEXTS:
        text = (ROOT / "docs" / "portfolio" / name).read_text(encoding="utf-8")
        body = re.split(r"^## Sources", text, flags=re.M)[0]
        numbers = sorted(set(NUMBER.findall(body)) - NOT_RESULTS)
        missing = [n for n in numbers if n not in corpus]
        failures += len(missing)
        unmatched = missing or "none"
        print(f"{name}: {len(numbers)} numbers checked; not in evals/results/final/: {unmatched}")
    summary = (ROOT / "docs" / "portfolio" / "summary.md").read_text(encoding="utf-8")
    body = re.split(r"^## Sources", summary, flags=re.M)[0]
    body = body.split("Not validated for production use.", 1)[1]
    words = len(body.split())
    print(f"summary.md body: {words} words (limit 150)")
    return 0 if failures == 0 and words <= 150 else 1


if __name__ == "__main__":
    sys.exit(main())
