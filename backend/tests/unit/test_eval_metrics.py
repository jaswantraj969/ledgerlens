import pytest
from evals.datasets.cord import map_gold
from evals.grouping import layout_descriptor
from evals.metrics import Outcome, header_outcome, multiset_outcome, summarize


def test_header_outcome_cases() -> None:
    assert header_outcome("1", "1") == Outcome(1, 0, 0, True, True)
    assert header_outcome("2", "1") == Outcome(0, 1, 1, False, True)
    assert header_outcome(None, "1") == Outcome(0, 0, 1, False, True)
    assert header_outcome("1", None) == Outcome(0, 1, 0, False, False)
    assert header_outcome(None, None) == Outcome(0, 0, 0, True, False)


def test_multiset_counts_duplicates() -> None:
    assert multiset_outcome(["a", "a", "b"], ["a", "c"]) == Outcome(1, 2, 1, False, True)
    assert multiset_outcome(["a", "b"], ["b", "a"]) == Outcome(2, 0, 0, True, True)


def test_summary_matches_hand_calculation() -> None:
    outcomes = [
        header_outcome("1", "1"),
        header_outcome("1", "1"),
        header_outcome("2", "1"),
        header_outcome(None, "1"),
        header_outcome(None, None),
    ]
    summary = summarize(outcomes)
    assert summary["tp"] == 2
    assert summary["fp"] == 1
    assert summary["fn"] == 2
    assert summary["precision"] == pytest.approx(2 / 3)
    assert summary["recall"] == pytest.approx(0.5)
    assert summary["f1"] == pytest.approx(4 / 7)
    assert summary["exact_match"] == pytest.approx(3 / 5)
    assert summary["n_documents"] == 5
    assert summary["n_labelled"] == 4


def test_interval_brackets_the_estimate_and_is_reproducible() -> None:
    outcomes = [header_outcome("1", "1")] * 30 + [header_outcome("2", "1")] * 10
    first, second = summarize(outcomes), summarize(outcomes)
    assert first == second
    low, high = first["precision_ci95"]  # type: ignore[misc]
    assert low < first["precision"] < high  # type: ignore[operator]


def test_perfect_results_have_a_degenerate_interval() -> None:
    summary = summarize([header_outcome("1", "1")] * 5)
    assert summary["precision_ci95"] == [1.0, 1.0]


def test_no_predictions_gives_null_precision_not_zero() -> None:
    summary = summarize([header_outcome(None, "1")] * 3)
    assert summary["precision"] is None
    assert summary["recall"] == 0
    assert summary["precision_ci95"] is None


def test_gold_mapping_handles_dict_list_and_absent_marker() -> None:
    gold = map_gold(
        {
            "total": {"total_price": "20,000"},
            "sub_total": [{"subtotal_price": ["10,000", "18,000"]}, {"tax_price": "-"}],
            "menu": [{"nm": "Tea", "price": "5,000", "cnt": "1"}, {"nm": "Rice", "price": "-"}],
        }
    )
    assert gold["total_amount"] == "20,000"
    assert gold["subtotal"] == "18,000"
    assert gold["tax_amount"] is None
    assert gold["line_items.description"] == ["Tea", "Rice"]
    assert gold["line_items.amount"] == ["5,000"]


def test_single_menu_row_may_be_a_dict() -> None:
    assert map_gold({"menu": {"nm": "Tea"}})["line_items.description"] == ["Tea"]


def test_descriptor_uses_positions_and_sums_to_one() -> None:
    descriptor = layout_descriptor([(10, 10), (90, 190)], 100, 200)
    assert descriptor[:-1].sum() == pytest.approx(1)
    assert descriptor[-1] == pytest.approx(0.5)
    assert descriptor[0] == pytest.approx(0.5)
