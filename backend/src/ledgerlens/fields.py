"""The field record: one extracted value with its evidence, checks and decision."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EvidenceStatus = Literal["exact", "fuzzy", "not_found", "self_sourced"]
Decision = Literal["auto_accepted", "needs_review", "approved", "corrected", "rejected"]
SignalValue = float | int | bool | str | None


class Evidence(BaseModel):
    page: int
    text: str
    bbox: tuple[float, float, float, float] | None
    coordinate_system: str | None
    confidence: float | None = None


class ValidationResult(BaseModel):
    rule_id: str
    passed: bool
    message: str


class FieldRecord(BaseModel):
    name: str
    value_raw: str | None
    value_normalized: str | None
    source: str
    evidence: list[Evidence] = []
    evidence_status: EvidenceStatus = "not_found"
    evidence_independent: bool = False
    validation_results: list[ValidationResult] = []
    signals: dict[str, SignalValue] = {}
    risk_score: float | None = None
    calibrated_prob: float | None = None
    decision: Decision = "needs_review"
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
