"""Confidence features for one field. The only place these features are computed.

Evidence match results enter only when the evidence is independent of the value's source. A
deterministic value is copied from the tokens it would be matched against, so its match
carries no information and must never reach a model as if it did. Missing values stay None
with an indicator feature; nothing is imputed here.
"""

from statistics import mean

from ledgerlens.fields import FieldRecord, SignalValue

Features = dict[str, SignalValue]


def build_features(record: FieldRecord) -> Features:
    independent = record.evidence_independent
    confidences = [e.confidence for e in record.evidence if e.confidence is not None]
    return {
        "value_present": record.value_raw is not None,
        "value_valid": record.value_normalized is not None,
        "rules_passed": sum(result.passed for result in record.validation_results),
        "rules_failed": sum(not result.passed for result in record.validation_results),
        "rules_checked": bool(record.validation_results),
        "independent_evidence": independent,
        "independent_match_exact": record.evidence_status == "exact" if independent else None,
        "independent_match_fuzzy": record.evidence_status == "fuzzy" if independent else None,
        "independent_match_absent": record.evidence_status == "not_found" if independent else None,
        "independent_match_score": record.signals.get("evidence_score") if independent else None,
        "ocr_confidence_mean": mean(confidences) if confidences else None,
        "ocr_confidence_min": min(confidences) if confidences else None,
        "ocr_confidence_available": bool(confidences),
        "agree_count": record.signals.get("agree_count"),
        "sources_with_value": record.signals.get("sources_with_value"),
        "agree_pass_a_b": record.signals.get("agree_pass_a_b"),
        "agree_pass_a_deterministic": record.signals.get("agree_pass_a_deterministic"),
        "cross_pass_available": "agree_count" in record.signals,
        # None when not checked: rule-extracted values are found by their label (circular).
        "label_supported": record.signals.get("label_supported"),
        # Deterministic rules and an LLM pass are independent sources (S4h).
        "agree_rules_llm": record.signals.get("agree_rules_llm"),
        # Prompt 2.1 and later: the line the model quoted, checked against the document.
        "llm_evidence_found": record.signals.get("llm_evidence_found"),
        "llm_value_in_evidence": record.signals.get("llm_value_in_evidence"),
    }
