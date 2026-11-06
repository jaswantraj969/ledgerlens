from ledgerlens.confidence.features import build_features
from ledgerlens.confidence.risk import risk_score
from ledgerlens.extraction.layout import Line
from ledgerlens.fields import Evidence, FieldRecord, ValidationResult
from ledgerlens.parsing.model import Token
from ledgerlens.verification.evidence import assess_evidence


def record(**updates: object) -> FieldRecord:
    values: dict[str, object] = {
        "name": "total_amount",
        "value_raw": "10.00",
        "value_normalized": "10.00",
        "source": "deterministic",
    }
    return FieldRecord.model_validate(values | updates)


LINES = [Line(page=1, tokens=(Token(text="10.00", bbox=(0, 0, 1, 1)),), coordinate_system="x")]


def test_deterministic_evidence_is_self_sourced_never_exact() -> None:
    field = record()
    assess_evidence(field, LINES, is_amount=True)
    assert field.evidence_status == "self_sourced"
    assert field.evidence_independent is False


def test_value_from_another_source_is_matched_independently() -> None:
    field = record(source="llm_pass_a")
    assess_evidence(field, LINES, is_amount=True)
    assert field.evidence_status == "exact"
    assert field.evidence_independent is True


def test_independent_value_absent_from_the_document_is_not_found() -> None:
    field = record(source="llm_pass_a", value_raw="99.00", value_normalized="99.00")
    assess_evidence(field, LINES, is_amount=True)
    assert field.evidence_status == "not_found"
    assert field.evidence_independent is True


def test_missing_value_is_not_found_and_not_independent() -> None:
    field = record(value_raw=None, value_normalized=None)
    assess_evidence(field, LINES, is_amount=True)
    assert field.evidence_status == "not_found"
    assert field.evidence_independent is False


def test_feature_builder_ignores_non_independent_matches() -> None:
    """Even a forged perfect match on self-sourced evidence must not reach the features."""
    plain = build_features(record(evidence_status="self_sourced"))
    forged = build_features(
        record(
            evidence_status="exact",
            evidence_independent=False,
            signals={"evidence_score": 100.0, "evidence_kind": "verbatim"},
        )
    )
    assert forged == plain
    assert forged["independent_match_exact"] is None
    assert forged["independent_match_score"] is None


def test_feature_builder_keeps_independent_matches() -> None:
    features = build_features(
        record(
            source="llm_pass_a",
            evidence_status="exact",
            evidence_independent=True,
            signals={"evidence_score": 100.0},
        )
    )
    assert features["independent_match_exact"] is True
    assert features["independent_match_score"] == 100.0


def test_risk_ignores_a_forged_match_on_self_sourced_evidence() -> None:
    assert risk_score(record(evidence_status="exact")) == risk_score(
        record(evidence_status="self_sourced")
    )


def test_self_sourced_value_needs_a_passing_rule_to_score_low() -> None:
    unchecked = record(evidence_status="self_sourced")
    checked = record(
        evidence_status="self_sourced",
        validation_results=[ValidationResult(rule_id="r", passed=True, message="")],
    )
    assert risk_score(checked) < risk_score(unchecked)


def test_ocr_confidence_is_summarised_and_null_when_unavailable() -> None:
    def evidence(confidence: float | None) -> Evidence:
        return Evidence(page=1, text="x", bbox=None, coordinate_system=None, confidence=confidence)

    with_scores = build_features(record(evidence=[evidence(0.8), evidence(0.6)]))
    assert with_scores["ocr_confidence_min"] == 0.6
    assert with_scores["ocr_confidence_mean"] == 0.7

    without = build_features(record(evidence=[evidence(None)]))
    assert without["ocr_confidence_mean"] is None
    assert without["ocr_confidence_available"] is False
