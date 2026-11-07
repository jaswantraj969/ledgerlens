import numpy as np
import pytest
from evals.s5 import Calibrator, Unit, build_units, choose_threshold, ece, routing_report


def record(name: str, exact: bool = True, present: bool = True) -> dict[str, object]:
    return {
        "name": name,
        "value_normalized": "1",
        "value_present": present,
        "source": "llm_pass_a",
        "features": {"independent_match_exact": exact, "label_supported": None,
                     "s4h_choice": "pass_a"},
    }  # fmt: skip


def test_units_are_labelled_with_the_scoring_normalisation_and_row_assignment() -> None:
    predictions = [{
        "document_id": "d",
        "failed": False,
        "header": {"subtotal": None, "tax_amount": "1.000", "total_amount": "10,000"},
        "rows": [{"description": "tea", "amount": "10.000"}, {"description": "x", "amount": "3"}],
    }]  # fmt: skip
    names = ["tax_amount", "total_amount", "line_items[0].description", "line_items[0].amount",
             "line_items[1].description", "line_items[1].amount"]  # fmt: skip
    records = {"d": [record(name) for name in names]}
    gold_headers = {"d": {"subtotal": None, "tax_amount": None, "total_amount": "10.000"}}
    gold_rows = {"d": [{"description": "tea", "quantity": None, "unit_price": None,
                        "amount": "10,000"}]}  # fmt: skip
    units, slots = build_units(predictions, records, gold_headers, gold_rows)
    assert slots == {"d": 3}
    header = {u.name: u.correct for u in units if u.kind == "header"}
    assert header == {"tax_amount": False, "total_amount": True}, "a false fill is wrong"
    assert [u.correct for u in units if u.kind == "row"] == [True, False]


def test_failed_documents_give_no_units_but_keep_their_slots() -> None:
    predictions = [{"document_id": "d", "failed": True, "header": {}, "rows": []}]
    units, slots = build_units(predictions, {}, {"d": {}}, {})
    assert units == [] and slots == {"d": 3}


def test_threshold_is_the_lowest_meeting_the_target_or_none() -> None:
    p = np.array([0.2, 0.6, 0.9, 0.95])
    correct = np.array([False, True, True, True])
    assert choose_threshold(p, correct, 0.98) == pytest.approx(0.201)
    assert choose_threshold(p, np.zeros(4, bool), 0.98) is None


def test_ece_is_zero_for_perfect_calibration_and_positive_otherwise() -> None:
    assert ece(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 0.0
    assert ece(np.array([0.9, 0.9]), np.array([0.0, 0.0])) == pytest.approx(0.9)


def unit(document: str, correct: bool, exact: bool) -> Unit:
    return Unit(document, "header", "total_amount", {"independent_match_exact": exact,
                "s4h_choice": "rules", "source": "deterministic"}, correct)  # fmt: skip


def test_calibrator_learns_an_informative_feature() -> None:
    train = [unit(f"d{i}", i % 2 == 0, i % 2 == 0) for i in range(40)]
    probabilities = Calibrator.fit(train).predict(train)
    assert probabilities[0] > 0.8 > 0.2 > probabilities[1]


def test_routing_counts_empty_slots_against_automation_and_reports_unmet_targets() -> None:
    units = [unit("a", True, True), unit("b", False, True)]
    probabilities = np.array([0.99, 0.95])
    report = routing_report(units, probabilities, {"a": 3, "b": 3}, {0.98: 0.9, 0.99: None})
    met = report["targets"]["0.98"]
    assert met["accepted"] == 2
    assert met["automation_rate"] == pytest.approx(2 / 6)
    assert met["achieved_precision"] == 0.5 and met["target_met"] is False
    assert report["targets"]["0.99"]["automation_rate"] == 0.0
    assert report["targets"]["0.99"]["achieved_precision"] is None
