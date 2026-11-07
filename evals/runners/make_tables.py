"""Generate a Markdown table from a results file. Tables are never edited by hand."""

import json
import sys
from pathlib import Path
from typing import Any


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _interval(values: list[float] | None) -> str:
    return "n/a" if values is None else f"[{values[0]:.3f}, {values[1]:.3f}]"


def _cell(row: dict[str, Any], name: str) -> str:
    return f"{_rate(row[name])} {_interval(row[f'{name}_ci95'])}"


def _seconds(block: dict[str, Any]) -> str:
    if not block["n"]:
        return "n/a"
    return f"p50 {block['p50']:.2f} s, p95 {block['p95']:.2f} s (n={block['n']})"


def render_v1(result: dict[str, Any], source: str) -> str:
    """Metrics 1.0 layout, kept so old tables regenerate unchanged."""
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


def field_table(fields: dict[str, Any], *, exact_match: bool = False) -> list[str]:
    """`exact_match` adds the redundant column, as metrics 1.1 tables showed it."""
    exact_header = " Exact match |" if exact_match else ""
    lines = [
        f"| Field | n present | n absent | Precision | Recall | F1 |{exact_header} "
        "False fill rate |",
        "|---|---|---|---|---|---|" + ("---|" if exact_match else "") + "---|",
    ]
    for name, row in fields.items():
        exact = f" {_cell(row, 'exact_match')} |" if exact_match else ""
        lines.append(
            f"| {name} | {row['n_present']} | {row['n_absent']} | {_cell(row, 'precision')} "
            f"| {_cell(row, 'recall')} | {_cell(row, 'f1')} |{exact} "
            f"{_cell(row, 'false_fill_rate')} |"
        )
    return lines


def row_table(row: dict[str, Any]) -> list[str]:
    return [
        "| Rows correct | Rows predicted | Rows gold | Precision | Recall | F1 "
        "| Documents with all rows correct |",
        "|---|---|---|---|---|---|---|",
        f"| {row['rows_correct']} | {row['rows_predicted']} | {row['rows_gold']} "
        f"| {_cell(row, 'precision')} | {_cell(row, 'recall')} | {_cell(row, 'f1')} "
        f"| {_cell(row, 'documents_all_rows_correct')} |",
    ]


def set_table(block: dict[str, Any]) -> list[str]:
    lines = [
        f"Secondary score, {block['label']}.",
        "",
        "| Cell | Precision | Recall | F1 |",
        "|---|---|---|---|",
    ]
    for name, row in block["fields"].items():
        lines.append(
            f"| {name} | {_cell(row, 'precision')} | {_cell(row, 'recall')} | {_cell(row, 'f1')} |"
        )
    return lines


def _llm_latency(result: dict[str, Any]) -> list[str]:
    latency = result["latency_seconds"]
    if "llm" not in result:
        return [f"- Total per document: {_seconds(latency['warm_total'])}. No model is used."]
    cold = latency["cold"]
    return [
        f"- Warm LLM, load excluded: {_seconds(latency['warm_llm'])}.",
        f"- Warm total per document: {_seconds(latency['warm_total'])}.",
        f"- Cold documents: {cold['documents']}. Model load (s): "
        f"{[round(x, 2) for x in cold['model_load_seconds']]}. Cold LLM time excluding load (s): "
        f"{[round(x, 2) for x in cold['cold_llm_seconds_excluding_load']]}.",
    ]


def render_v1_1(result: dict[str, Any], source: str) -> str:
    failures = result["failures"]
    latency = result["latency_seconds"]
    memory = result.get("memory_live_run", result["memory"])
    memory_label = "Memory, live run" if "memory_live_run" in result else "Memory"
    version = result["metrics_version"]
    legacy = version == "1.1"
    exact_note = (
        "`exact_match` equals `recall` by definition under metrics 1.1; see docs/evaluation.md."
        if legacy
        else "Exact match is not shown: for single-valued fields it equals recall. It stays in "
        "the JSON, flagged redundant. See docs/evaluation.md."
    )
    rescored = result.get("rescored_from")
    provenance = (
        [
            f"- Rescored from saved predictions of `{rescored['results_file']}`, with no rerun. "
            f"Rescored at commit `{rescored['environment']['git_commit']}`, "
            f"dirty: {rescored['environment']['git_dirty']}."
        ]
        if rescored
        else []
    )
    lines = [
        f"# {result['system']} on {result['dataset']} {result['split']} (metrics {version})",
        "",
        f"Generated from `{source}`. Do not edit by hand.",
        "",
        f"- Documents: {result['n_documents']}. Workers: {result['workers']}.",
        f"- Metrics {result['metrics_version']}, normalisation "
        f"{result['normalization']['version']} (sha256 `{result['normalization']['sha256']}`).",
        f"- Schema: {result['schema']} {result['schema_version']}. "
        f"Split sha256: `{result['split_sha256']}`.",
        f"- Predictions sha256: `{result['predictions_sha256']}`.",
        f"- Intervals: 95% bootstrap, {result['bootstrap']['resamples']} resamples of documents, "
        f"seed {result['bootstrap']['seed']}.",
        f"- Commit: `{result['environment']['git_commit']}`, "
        f"dirty: {result['environment']['git_dirty']}.",
        *provenance,
        "",
        "## Single-valued fields",
        "",
        exact_note,
        "",
        *field_table(result["fields"], exact_match=legacy),
        "",
        "## Line items, row level (primary)",
        "",
        *row_table(result["line_items_row_level"]),
        "",
        "## Line items, set-based (secondary)",
        "",
        *set_table(result["line_items_set_based"]),
        "",
        "## Failures",
        "",
        f"- Crashes: {failures['crashes']}.",
        f"- Failed extractions (scored as empty): {failures['failed_extractions']}.",
        f"- Documents with a fallback: {failures['documents_with_a_fallback']}. "
        f"Pass fallbacks: {failures['pass_fallbacks']}.",
        f"- Retries: {failures['retries']}. Truncated replies: {failures['truncated_replies']}.",
        "",
        "## Verification",
        "",
        f"- Values output: {result['verification']['values_output']}.",
        f"- Not found in the document: {result['verification']['values_not_found_in_document']}.",
        f"- Withheld: {result['verification']['values_withheld']}.",
        f"- Rule failures: {result['verification']['rule_failures']}.",
        "",
        "## Latency and memory",
        "",
        f"Timings are {latency['source']}.",
        "",
        f"- OCR: {_seconds(latency['ocr'])}.",
        *_llm_latency(result),
        f"- {memory_label}: peak process RSS {memory['peak_process_rss_gib']} GiB, "
        f"peak model runner RSS {memory['peak_model_runner_rss_gib']} GiB, lowest available "
        f"system RAM {memory['lowest_available_system_ram_gib']} of "
        f"{memory['total_system_ram_gib']} GiB.",
        "",
    ]
    excluded = {k: v for k, v in result["gold_values_excluded_unparsable"].items() if v}
    lines += [f"Gold values excluded as unparsable: {excluded or 'none'}.", ""]
    return "\n".join(lines)


def render(result: dict[str, Any], source: str) -> str:
    if "metrics_version" in result:
        return render_v1_1(result, source)
    return render_v1(result, source)


def main() -> None:
    for argument in sys.argv[1:]:
        source = Path(argument)
        result = json.loads(source.read_text(encoding="utf-8"))
        output = source.with_suffix(".md")
        output.write_text(render(result, source.name), encoding="utf-8", newline="\n")
        print("wrote", output)


if __name__ == "__main__":
    main()
