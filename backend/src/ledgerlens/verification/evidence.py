"""Check a value against the document text, independently of how it was extracted."""

from dataclasses import dataclass

from rapidfuzz import fuzz

from ledgerlens.extraction.layout import Line
from ledgerlens.fields import EvidenceStatus, FieldRecord
from ledgerlens.verification.normalize import normalize_amount, normalize_text

# Sources whose values are copied from the tokens the matcher would search.
TOKEN_DERIVED_SOURCES = frozenset({"deterministic"})
FUZZY_THRESHOLD = 85.0
_MAX_WINDOW = 8


@dataclass(frozen=True)
class EvidenceMatch:
    status: EvidenceStatus
    kind: str | None
    score: float | None


NOT_FOUND = EvidenceMatch(status="not_found", kind=None, score=None)


def assess_evidence(record: FieldRecord, lines: list[Line], *, is_amount: bool) -> None:
    """Set evidence status. A token-derived value is `self_sourced`: matching it proves nothing."""
    if record.value_raw is None:
        record.evidence_status = "not_found"
        record.evidence_independent = False
        return
    if record.source in TOKEN_DERIVED_SOURCES:
        record.evidence_status = "self_sourced"
        record.evidence_independent = False
        return
    match = match_evidence(record.value_raw, lines, is_amount=is_amount)
    record.evidence_status = match.status
    record.evidence_independent = True
    record.signals.update(evidence_kind=match.kind, evidence_score=match.score)


def match_evidence(value: str | None, lines: list[Line], *, is_amount: bool) -> EvidenceMatch:
    """Find `value` in token windows: verbatim, then normalised, then fuzzy."""
    if not value:
        return NOT_FOUND
    target_text = normalize_text(value)
    target_amount = normalize_amount(value) if is_amount else None
    best = 0.0
    found_normalized = False
    for window in _windows(lines):
        if window == value:
            return EvidenceMatch(status="exact", kind="verbatim", score=100.0)
        if is_amount:
            found_normalized |= (
                target_amount is not None and normalize_amount(window) == target_amount
            )
            continue
        found_normalized |= normalize_text(window) == target_text
        best = max(best, fuzz.ratio(normalize_text(window), target_text))
    if found_normalized:
        return EvidenceMatch(status="exact", kind="normalized", score=100.0)
    if best >= FUZZY_THRESHOLD:
        return EvidenceMatch(status="fuzzy", kind="fuzzy", score=best)
    return NOT_FOUND


def _windows(lines: list[Line]) -> list[str]:
    windows: list[str] = []
    for line in lines:
        texts = [token.text for token in line.tokens]
        for start in range(len(texts)):
            for end in range(start + 1, min(start + _MAX_WINDOW, len(texts)) + 1):
                windows.append(" ".join(texts[start:end]))
    return windows
