"""Generate the synthetic dev versus held-out table. Never edited by hand."""

import json
import sys
from pathlib import Path
from typing import Any


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _route(name: str, route: dict[str, Any], dev: list[str], held: list[str]) -> list[str]:
    layouts = route["layouts"]
    ordered = [*dev, *held]
    lines = [
        f"## Route: {name}, {route['documents_per_layout']} documents per layout",
        "",
        "### Dev versus held-out, F1 pooled over documents",
        "",
        "| Field | Dev F1 | Held-out F1 | Gap (dev minus held-out) |",
        "|---|---|---|---|",
    ]
    for field, row in route["dev_vs_held_out"].items():
        lines.append(
            f"| {field} | {_rate(row['dev_f1'])} | {_rate(row['held_out_f1'])} "
            f"| {_rate(row['gap'])} |"
        )
    lines += [
        "",
        "### F1 per layout",
        "",
        "| Field | "
        + " | ".join(f"{layout} (held out)" if layout in held else layout for layout in ordered)
        + " |",
        "|---|" + "---|" * len(ordered),
    ]
    for field in next(iter(layouts.values()))["fields"]:
        cells = " | ".join(_rate(layouts[layout]["fields"][field]["f1"]) for layout in ordered)
        lines.append(f"| {field} | {cells} |")
    cells = " | ".join(_rate(layouts[layout]["line_items_row_level"]["f1"]) for layout in ordered)
    lines += [f"| line_items (row level) | {cells} |", ""]
    return lines


def main() -> None:
    source = Path(sys.argv[1])
    result = json.loads(source.read_text(encoding="utf-8"))
    lines = [
        "# S1 on synthetic invoices (metrics 1.1)",
        "",
        f"Generated from `{source.name}`. Do not edit by hand. {result['note']}",
        "",
        f"Commit `{result['environment']['git_commit']}`, "
        f"dirty: {result['environment']['git_dirty']}.",
        "",
    ]
    for name, route in result["routes"].items():
        lines += _route(name, route, result["dev_layouts"], result["held_out_layouts"])
    output = source.with_suffix(".md")
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote", output)


if __name__ == "__main__":
    main()
