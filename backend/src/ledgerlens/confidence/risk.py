"""Heuristic error-risk score (baseline B1).

The output is a hand-weighted score in [0, 1]. It is not a probability and must not be
presented as one. The weights are not fitted to data.
"""

from ledgerlens.confidence.features import build_features
from ledgerlens.fields import FieldRecord

DEFAULT_REVIEW_THRESHOLD = 0.2

_NO_INDEPENDENT_EVIDENCE_RISK = 0.1
_FUZZY_RISK = 0.3
_ABSENT_RISK = 0.6
_INVALID_VALUE_RISK = 0.5
_FAILED_RULE_RISK = 0.4
_UNCHECKED_RISK = 0.1


def risk_score(record: FieldRecord) -> float:
    features = build_features(record)
    if not features["value_present"]:
        return 1.0
    if not features["independent_evidence"]:
        risk = _NO_INDEPENDENT_EVIDENCE_RISK
    elif features["independent_match_absent"]:
        risk = _ABSENT_RISK
    elif features["independent_match_fuzzy"]:
        risk = _FUZZY_RISK
    else:
        risk = 0.0
    if not features["value_valid"]:
        risk += _INVALID_VALUE_RISK
    if features["rules_failed"]:
        risk += _FAILED_RULE_RISK
    elif not features["rules_checked"]:
        risk += _UNCHECKED_RISK
    return min(risk, 1.0)


def route(record: FieldRecord, threshold: float = DEFAULT_REVIEW_THRESHOLD) -> None:
    """Score a field and decide. Missing and invalid values always go to a person."""
    record.risk_score = risk_score(record)
    accepted = record.value_normalized is not None and record.risk_score < threshold
    record.decision = "auto_accepted" if accepted else "needs_review"
