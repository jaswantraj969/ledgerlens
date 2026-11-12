"""Evaluation report: serves committed results files, read-only. Nothing is computed here.

Each block names the file it came from. A missing file is reported as missing, never filled in.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from ledgerlens.api.deps import PrincipalDep

router = APIRouter(tags=["evaluation"])

SOURCES = {
    "test_comparison": "final/cord_test_comparison_v1_1_1.json",
    "s5_test": "final/cord_s5_test_v1_1_1.json",
    "validation_comparison": "dev/cord_validation_comparison_v1_1_1.json",
    "prompt_round": "dev/prompt_round/prompt_round.json",
    "s1_test": "cord_s1_v1_1_1.json",
    "s5_s1_validation": "dev/cord_s5_s1_validation_v1_1_1.json",
    "s5_s4h_validation": "dev/cord_s5_s4h_validation_v1_1_1.json",
}
_S1_TEST_KEYS = ("system", "split", "n_documents", "metrics_version", "fields",
                 "line_items_row_level")  # fmt: skip


def default_results_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "evals" / "results"


def _load(directory: Path, relative: str) -> dict[str, Any]:
    path = directory / relative
    if not path.is_file():
        return {"available": False, "source": f"evals/results/{relative}"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"available": True, "source": f"evals/results/{relative}", "data": data}


@router.get("/evaluation/report")
def evaluation_report(request: Request, _principal: PrincipalDep) -> dict[str, Any]:
    directory = request.app.state.settings.results_dir or default_results_dir()
    report: dict[str, Any] = {
        name: _load(directory, relative) for name, relative in SOURCES.items()
    }
    s1 = report["s1_test"]
    if s1["available"]:
        s1["data"] = {key: s1["data"][key] for key in _S1_TEST_KEYS if key in s1["data"]}
    report["note"] = (
        "The final CORD test read is complete: S1 to S4h and S5 were each read once on test, "
        "under docs/evaluation/final-test-protocol.md. Test tables come from "
        "evals/results/final/. Validation results are for development only."
    )
    return report
