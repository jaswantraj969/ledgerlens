import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from evals import normalization
from evals.runners import llm_smoke, run_cord_s1

ROOT = Path(__file__).resolve().parents[3]
SPLITS = ROOT / "evals" / "splits" / "cord_v2"


def run_module(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "evals.runners.run_cord_s1", *arguments],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT), "SYSTEMROOT": "C:\\Windows", "PATH": ""},
        check=False,
    )


def test_test_split_requires_final_flag() -> None:
    completed = run_module("--split", "test")
    assert completed.returncode != 0
    assert "--final" in completed.stderr


def test_llm_smoke_can_only_read_validation() -> None:
    source = (ROOT / "evals" / "runners" / "llm_smoke.py").read_text(encoding="utf-8")
    assert 'SPLIT = "validation"' in source
    assert "--split" not in source
    assert llm_smoke.SPLIT == "validation"


def test_llm_smoke_sample_is_seeded_and_inside_validation() -> None:
    splits = json.loads((SPLITS / "ids.json").read_text(encoding="utf-8"))
    sample = llm_smoke.sample_ids()
    assert sample == llm_smoke.sample_ids()
    assert len(sample) == 10
    assert set(sample) <= set(splits["validation"]["ids"])
    assert not set(sample) & set(splits["test"]["ids"])


def test_split_ids_do_not_overlap_and_match_official_sizes() -> None:
    splits = json.loads((SPLITS / "ids.json").read_text(encoding="utf-8"))
    assert {name: part["n"] for name, part in splits.items()} == {
        "train": 800,
        "validation": 100,
        "test": 100,
    }
    seen = [set(part["ids"]) for part in splits.values()]
    assert sum(len(ids) for ids in seen) == len(set().union(*seen)) == 1000


def test_group_centroids_cover_every_document() -> None:
    groups = json.loads((SPLITS / "layout_groups.json").read_text(encoding="utf-8"))
    splits = json.loads((SPLITS / "ids.json").read_text(encoding="utf-8"))
    assert set(groups["assignments"]) == {i for part in splits.values() for i in part["ids"]}
    assert groups["k"] == 12


def test_header_compare_is_numeric() -> None:
    outcome, dropped = run_cord_s1.compare("total_amount", "1.000", "Rp 1,000")
    assert (outcome.tp, dropped) == (1, 0)


def test_unparsable_gold_is_counted_and_not_scored() -> None:
    outcome, dropped = run_cord_s1.compare("total_amount", "5", "unreadable")
    assert dropped == 1
    assert outcome.labelled is False


def test_line_descriptions_compare_as_text() -> None:
    outcome, _ = run_cord_s1.compare(
        "line_items.description", ["ICE  TEA", "Rice"], ["ice tea", "Soup"]
    )
    assert (outcome.tp, outcome.fp, outcome.fn) == (1, 1, 1)


def test_line_amounts_compare_as_numbers() -> None:
    outcome, _ = run_cord_s1.compare("line_items.amount", ["1.000"], ["1,000"])
    assert outcome.tp == 1
    assert normalization.money("1.000") == Decimal(1000)


@pytest.mark.parametrize("name", ["subtotal", "tax_amount", "total_amount"])
def test_missing_prediction_defaults_to_none(name: str) -> None:
    assert run_cord_s1.predictions([])[name] is None


def test_train_is_read_only_through_a_fixed_subset() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.runners.run_cord", "--system", "S1", "--split", "train"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT), "SYSTEMROOT": r"C:\Windows", "PATH": ""},
        check=False,
    )
    assert completed.returncode != 0
    assert "--subset" in completed.stderr


def run_cord(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "evals.runners.run_cord", *arguments],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT), "SYSTEMROOT": r"C:\Windows", "PATH": ""},
        check=False,
    )


@pytest.mark.parametrize("flag", [["--perturb", "jpeg-10"], ["--records-rerun"]])
def test_degradation_and_records_rerun_apply_to_test_only(flag: list[str]) -> None:
    completed = run_cord("--system", "S1", "--split", "validation", *flag)
    assert completed.returncode != 0
    assert "test split only" in completed.stderr


def test_degradation_on_test_still_needs_final() -> None:
    completed = run_cord("--system", "S1", "--split", "test", "--perturb", "blur-1.5")
    assert completed.returncode != 0
    assert "--final" in completed.stderr


def test_perturbation_and_records_rerun_do_not_combine() -> None:
    completed = run_cord(
        "--system", "S1", "--split", "test", "--final", "--perturb", "jpeg-30", "--records-rerun"
    )
    assert completed.returncode != 0
    assert "do not combine" in completed.stderr


def test_environment_records_an_unknown_commit_where_git_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_git(*_: object, **__: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(run_cord_s1.subprocess, "run", no_git)
    info = run_cord_s1.environment()
    assert info["git_commit"] is None and info["git_dirty"] is None


def test_environment_records_the_commit_in_a_repository() -> None:
    info = run_cord_s1.environment()
    assert info["git_commit"] and len(info["git_commit"]) == 40
    assert info["git_dirty"] in (True, False)
