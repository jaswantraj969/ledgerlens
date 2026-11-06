"""Heuristic error-risk score (baseline B1).

The output is a hand-weighted score in [0, 1]. It is not a probability and must not be
presented as one. The weights are not fitted to data.
"""

from ledgerlens.fields import FieldRecord

DEFAULT_REVIEW_THRESHOLD = 0.2

_EVIDENCE_RISK = {"exact": 0.0, "fuzzy": 0.3, "not_found": 0.6}
_INVALID_VALUE_RISK = 0.5
_FAILED_RULE_RISK = 0.4
_UNCHECKED_RISK = 0.1


def risk_score(record: FieldRecord) -> float:
    if record.value_raw is None:
        return 1.0
    risk = _EVIDENCE_RISK[record.evidence_status]
    if record.value_normalized is None:
        risk += _INVALID_VALUE_RISK
    if any(not result.passed for result in record.validation_results):
        risk += _FAILED_RULE_RISK
    elif not record.validation_results:
        risk += _UNCHECKED_RISK
    return min(risk, 1.0)


def route(record: FieldRecord, threshold: float = DEFAULT_REVIEW_THRESHOLD) -> None:
    """Score a field and decide. Missing and invalid values always go to a person."""
    record.risk_score = risk_score(record)
    accepted = record.value_normalized is not None and record.risk_score < threshold
    record.decision = "auto_accepted" if accepted else "needs_review"
