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


def _units_with_two_signals(count: int = 120) -> list[Unit]:
    rng = np.random.default_rng(3)
    units = []
    for index in range(count):
        correct = bool(rng.random() < 0.6)
        features = {
            "label_supported": correct if rng.random() < 0.9 else not correct,
            "amount_rules_passed": int(rng.integers(0, 3)),
            "ocr_confidence_mean": float(rng.random()),
        }
        units.append(Unit(f"d{index // 3}", "header", "total_amount", features, correct))
    return units


def test_dropping_a_family_removes_its_columns_and_row_prefixed_columns() -> None:
    units = _units_with_two_signals()
    full = Calibrator.fit(units).vectorizer.columns()
    assert "label_supported" in full and "amount_rules_passed" in full
    no_label = Calibrator.fit(units, drop=["label_supported"]).vectorizer.columns()
    assert "label_supported" not in no_label and "label_supported_missing" not in no_label
    no_rules = Calibrator.fit(units, drop=["rules_passed"]).vectorizer.columns()
    assert "amount_rules_passed" not in no_rules and "ocr_confidence_mean" in no_rules


def test_signal_families_match_by_name_or_cell_suffix_only() -> None:
    from evals.s5 import SIGNAL_FAMILIES, in_family

    assert in_family("description_rules_failed", SIGNAL_FAMILIES["format_validation"])
    assert not in_family("independent_match_exact", SIGNAL_FAMILIES["format_validation"])
    assert in_family("agree_count", SIGNAL_FAMILIES["ab_agreement"])
    assert in_family("agree_count", SIGNAL_FAMILIES["rule_llm_agreement"])


def test_isotonic_calibrator_gives_probabilities_and_keeps_the_ranking_signal() -> None:
    units = _units_with_two_signals(300)
    calibrator = Calibrator.fit(units, method="isotonic")
    probabilities = calibrator.predict(units)
    assert ((probabilities >= 0) & (probabilities <= 1)).all()
    supported = np.array([u.features["label_supported"] for u in units], dtype=bool)
    assert probabilities[supported].mean() > probabilities[~supported].mean()
    with pytest.raises(ValueError):
        Calibrator.fit(units, method="beta")
