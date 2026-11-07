from evals.metrics import EXACT_MATCH_NOTE, single_outcome, summarize_single
from evals.runners.make_tables import field_table
from evals.runners.rescore import differences


def fields() -> dict[str, object]:
    outcomes = [single_outcome("1", "1"), single_outcome(None, "1"), single_outcome("2", None)]
    return {"total": summarize_single(outcomes)}


def test_exact_match_is_kept_in_json_and_flagged() -> None:
    row = fields()["total"]
    assert isinstance(row, dict)
    assert row["exact_match"] == row["recall"]
    assert row["exact_match_redundant"] == EXACT_MATCH_NOTE


def test_current_tables_drop_the_exact_match_column() -> None:
    header = field_table(fields())[0]  # type: ignore[arg-type]
    assert "Exact match" not in header
    assert header.count("|") == field_table(fields())[2].count("|")  # type: ignore[arg-type]


def test_legacy_tables_keep_the_exact_match_column() -> None:
    lines = field_table(fields(), exact_match=True)  # type: ignore[arg-type]
    assert "Exact match" in lines[0]
    assert lines[0].count("|") == lines[1].count("|") == lines[2].count("|")


def test_differences_ignore_added_keys_only() -> None:
    old = {"a": {"x": 1, "ci": [0.1, 0.2]}}
    assert differences(old, {"a": {"x": 1, "ci": [0.1, 0.2], "note": "new"}}) == []
    assert differences(old, {"a": {"x": 2, "ci": [0.1, 0.2]}}) == [".a.x: 1 != 2"]
    assert differences(old, {"a": {"ci": [0.1, 0.2]}}) == [".a.x missing"]
