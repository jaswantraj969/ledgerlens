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
    }
