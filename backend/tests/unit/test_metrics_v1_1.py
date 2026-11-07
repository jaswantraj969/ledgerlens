import pytest
from evals.metrics import (
    METRICS_VERSION,
    RowOutcome,
    SingleOutcome,
    match_rows,
    row_score,
    single_outcome,
    summarize_rows,
    summarize_single,
)


def test_version() -> None:
    assert METRICS_VERSION == "1.1.1"


@pytest.mark.parametrize(
    ("predicted", "gold", "expected"),
    [
        ("1", "1", SingleOutcome(True, True, True)),
        ("2", "1", SingleOutcome(True, True, False)),
        (None, "1", SingleOutcome(False, True, False)),
        ("1", None, SingleOutcome(True, False, False)),
        (None, None, SingleOutcome(False, False, False)),
    ],
)
def test_single_outcome_cases(
    predicted: str | None, gold: str | None, expected: SingleOutcome
) -> None:
    assert single_outcome(predicted, gold) == expected


def test_single_summary_hand_computed() -> None:
    """Two right, one wrong, one missed, one false fill, three correctly empty."""
    outcomes = [
        single_outcome("1", "1"),
        single_outcome("1", "1"),
        single_outcome("2", "1"),
        single_outcome(None, "1"),
        single_outcome("9", None),
        single_outcome(None, None),
        single_outcome(None, None),
        single_outcome(None, None),
    ]
    summary = summarize_single(outcomes)
    assert summary["n_documents"] == 8
    assert (summary["n_present"], summary["n_absent"]) == (4, 4)
    assert (summary["tp"], summary["fp"], summary["fn"]) == (2, 2, 2)
    assert summary["false_fills"] == 1
    assert summary["exact_match"] == pytest.approx(2 / 4)
    assert summary["false_fill_rate"] == pytest.approx(1 / 4)
    assert summary["precision"] == pytest.approx(2 / 4)
    assert summary["recall"] == pytest.approx(2 / 4)
    assert summary["f1"] == pytest.approx(2 / 4)


def test_absent_documents_no_longer_inflate_exact_match() -> None:
    """Under 1.0 this scored 0.9, because empty documents counted as agreement."""
    outcomes = [single_outcome(None, "1")] + [single_outcome(None, None)] * 9
    assert summarize_single(outcomes)["exact_match"] == 0


def test_all_gold_present_gives_null_false_fill_rate() -> None:
    summary = summarize_single([single_outcome("1", "1")])
    assert summary["false_fill_rate"] is None
    assert summary["false_fill_rate_ci95"] is None


def test_all_gold_absent_gives_null_exact_match() -> None:
    summary = summarize_single([single_outcome("1", None), single_outcome(None, None)])
    assert summary["exact_match"] is None
    assert summary["false_fill_rate"] == 0.5


def test_empty_predictions_on_present_gold() -> None:
    summary = summarize_single([single_outcome(None, "1")] * 3)
    assert summary["precision"] is None
    assert summary["recall"] == 0
    assert summary["exact_match"] == 0


def test_interval_is_reproducible() -> None:
    outcomes = [single_outcome("1", "1")] * 20 + [single_outcome("2", "1")] * 20
    assert summarize_single(outcomes) == summarize_single(outcomes)
    low, high = summarize_single(outcomes)["exact_match_ci95"]  # type: ignore[misc]
    assert low < 0.5 < high


TEA = {"description": "tea", "quantity": 1, "amount": 5}
RICE = {"description": "rice", "quantity": 2, "amount": 9}


def test_row_score_uses_only_fields_the_gold_row_labels() -> None:
    gold = {"description": "tea", "unit_price": None, "amount": 5}
    assert row_score({"description": "tea", "unit_price": 99, "amount": 5}, gold) == (True, 1.0)


def test_row_score_counts_partial_matches() -> None:
    assert row_score({"description": "tea", "quantity": 7, "amount": 5}, TEA) == (False, 2 / 3)


def test_row_alignment_is_required_unlike_the_set_based_score() -> None:
    """Every value is right, but swapped between rows: set-based would call this perfect."""
    swapped = [
        {"description": "tea", "quantity": 2, "amount": 9},
        {"description": "rice", "quantity": 1, "amount": 5},
    ]
    assert match_rows(swapped, [TEA, RICE]) == RowOutcome(0, 2, 2)


def test_order_does_not_matter() -> None:
    assert match_rows([RICE, TEA], [TEA, RICE]) == RowOutcome(2, 2, 2)


def test_duplicate_gold_rows_need_duplicate_predictions() -> None:
    assert match_rows([TEA], [TEA, TEA]) == RowOutcome(1, 1, 2)
    assert match_rows([TEA, TEA], [TEA, TEA]) == RowOutcome(2, 2, 2)


def test_duplicate_predictions_match_one_gold_row() -> None:
    assert match_rows([TEA, TEA, TEA], [TEA]) == RowOutcome(1, 3, 1)


def test_empty_predictions_and_empty_gold() -> None:
    assert match_rows([], [TEA]) == RowOutcome(0, 0, 1)
    assert match_rows([TEA], []) == RowOutcome(0, 1, 0)
    assert match_rows([], []) == RowOutcome(0, 0, 0)


def test_gold_row_with_no_labelled_field_is_not_scored() -> None:
    blank = {"description": None, "amount": None}
    assert match_rows([TEA], [TEA, blank]) == RowOutcome(1, 1, 1)


def test_assignment_prefers_full_matches_over_many_partial_ones() -> None:
    """A greedy first-fit would give pred 0 to gold 0 and lose the only full match."""
    gold = [
        {"description": "tea", "amount": 5},
        {"description": "tea", "amount": 7},
    ]
    predicted = [{"description": "tea", "amount": 7}, {"description": "coffee", "amount": 5}]
    assert match_rows(predicted, gold).correct == 1


@pytest.mark.parametrize("flip_predicted", [False, True])
@pytest.mark.parametrize("flip_gold", [False, True])
def test_a_partial_score_tie_still_keeps_the_full_match(
    flip_predicted: bool, flip_gold: bool
) -> None:
    """Both pairings total 1.0 on partial share. Only one of them has a fully correct row."""
    exact = {"description": "tea", "quantity": 1, "unit_price": 2, "amount": 5}
    near = {"description": "tea", "quantity": 1, "unit_price": 2, "amount": 7}
    other = {"description": "x", "quantity": 8, "unit_price": 9, "amount": 5}
    gold = [near, exact] if flip_gold else [exact, near]
    predicted = [other, exact] if flip_predicted else [exact, other]
    assert match_rows(predicted, gold).correct == 1


def test_row_summary_hand_computed() -> None:
    summary = summarize_rows([RowOutcome(2, 2, 2), RowOutcome(1, 3, 2), RowOutcome(0, 1, 0)])
    assert (summary["rows_correct"], summary["rows_predicted"], summary["rows_gold"]) == (3, 6, 4)
    assert summary["precision"] == pytest.approx(3 / 6)
    assert summary["recall"] == pytest.approx(3 / 4)
    assert summary["f1"] == pytest.approx(0.6)
    assert summary["n_documents_with_rows"] == 2
    assert summary["documents_all_rows_correct"] == pytest.approx(1 / 2)


def test_row_summary_with_no_predictions() -> None:
    summary = summarize_rows([RowOutcome(0, 0, 3)])
    assert summary["precision"] is None
    assert summary["recall"] == 0
