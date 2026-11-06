"""Generate a Markdown table from a results file. Tables are never edited by hand."""

import json
import sys
from pathlib import Path
from typing import Any


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _interval(values: list[float] | None) -> str:
    return "n/a" if values is None else f"[{values[0]:.3f}, {values[1]:.3f}]"


def render(result: dict[str, Any], source: str) -> str:
    latency = result["latency_seconds"]
    failures = result["failures"]
    lines = [
        f"# {result['system']} on {result['dataset']} {result['split']}",
        "",
        f"Generated from `{source}`. Do not edit by hand.",
        "",
        f"- Documents: {result['n_documents']}. `n` is documents with a label for the field.",
        f"- Schema: {result['schema']} {result['schema_version']}.",
        f"- Normalisation: {result['normalization']['version']}, "
        f"sha256 `{result['normalization']['sha256']}`.",
        f"- Split sha256: `{result['split_sha256']}`.",
        f"- Intervals: 95% bootstrap, {result['bootstrap']['resamples']} resamples of documents, "
        f"seed {result['bootstrap']['seed']}.",
        f"- Failures: {failures['crashes']} crashes, "
        f"{failures['documents_without_tokens']} documents without tokens.",
        f"- Latency per document ({latency['scope']}): "
        f"p50 {latency['p50']:.2f} s, p95 {latency['p95']:.2f} s.",
        f"- Commit: `{result['environment']['git_commit']}`, "
        f"dirty: {result['environment']['git_dirty']}.",
        "",
        "| Field | n | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] | Exact match [95% CI] |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in result["fields"].items():
        lines.append(
            f"| {name} | {row['n_labelled']} "
            f"| {_rate(row['precision'])} {_interval(row['precision_ci95'])} "
            f"| {_rate(row['recall'])} {_interval(row['recall_ci95'])} "
            f"| {_rate(row['f1'])} {_interval(row['f1_ci95'])} "
            f"| {_rate(row['exact_match'])} {_interval(row['exact_match_ci95'])} |"
        )
    excluded = {k: v for k, v in result["gold_values_excluded_unparsable"].items() if v}
    lines += ["", f"Gold values excluded as unparsable: {excluded or 'none'}.", ""]
    return "\n".join(lines)


def main() -> None:
    source = Path(sys.argv[1])
    result = json.loads(source.read_text(encoding="utf-8"))
    output = source.with_suffix(".md")
    output.write_text(render(result, source.name), encoding="utf-8", newline="\n")
    print("wrote", output)


if __name__ == "__main__":
    main()
