"""Database schema. Tenant data carries organization_id, and repositories always filter on it."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROLES = ("admin", "reviewer", "viewer")
JOB_STATES = (
    "queued",
    "parsing",
    "extracting",
    "verifying",
    "scoring",
    "ready_for_review",
    "completed",
    "failed",
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def _fk(target: str) -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey(target, ondelete="CASCADE"), nullable=False, index=True
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = _id()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = _created()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'reviewer', 'viewer')", name="user_role"),)

    id: Mapped[uuid.UUID] = _id()
    organization_id: Mapped[uuid.UUID] = _fk("organizations.id")
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = _created()


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = _created()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("organization_id", "sha256", name="document_org_sha256"),)

    id: Mapped[uuid.UUID] = _id()
    organization_id: Mapped[uuid.UUID] = _fk("organizations.id")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    pages: Mapped[int | None] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = _created()


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("document_id", "number", name="page_document_number"),)

    id: Mapped[uuid.UUID] = _id()
    document_id: Mapped[uuid.UUID] = _fk("documents.id")
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(nullable=False)
    height: Mapped[float] = mapped_column(nullable=False)
    coordinate_system: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)


class OcrTokens(Base):
    """Tokens for one page as JSONB: [{text, bbox, confidence}]."""

    __tablename__ = "ocr_tokens"

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), primary_key=True
    )
    tokens: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued', 'parsing', 'extracting', 'verifying', 'scoring', "
            "'ready_for_review', 'completed', 'failed')",
            name="job_state",
        ),
    )

    id: Mapped[uuid.UUID] = _id()
    document_id: Mapped[uuid.UUID] = _fk("documents.id")
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(60))
    error_detail: Mapped[str | None] = mapped_column(Text)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "step", "version", name="extraction_run_idempotency"),
    )

    id: Mapped[uuid.UUID] = _id()
    document_id: Mapped[uuid.UUID] = _fk("documents.id")
    step: Mapped[str] = mapped_column(String(30), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str | None] = mapped_column(String(60))
    prompt_version: Mapped[str | None] = mapped_column(String(30))
    schema_version: Mapped[str] = mapped_column(String(60), nullable=False)
    cost_usd: Mapped[float | None] = mapped_column()
    latency_seconds: Mapped[float | None] = mapped_column()
    cache_hit: Mapped[bool | None] = mapped_column()
    degraded_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()


class Field(Base):
    __tablename__ = "fields"
    __table_args__ = (UniqueConstraint("run_id", "name", name="field_run_name"),)

    id: Mapped[uuid.UUID] = _id()
    run_id: Mapped[uuid.UUID] = _fk("extraction_runs.id")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value_raw: Mapped[str | None] = mapped_column(Text)
    value_normalized: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_independent: Mapped[bool] = mapped_column(nullable=False, default=False)
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_score: Mapped[float | None] = mapped_column()
    calibrated_prob: Mapped[float | None] = mapped_column()
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="needs_review")


class FieldEvidence(Base):
    __tablename__ = "field_evidence"

    id: Mapped[uuid.UUID] = _id()
    field_id: Mapped[uuid.UUID] = _fk("fields.id")
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB)
    coordinate_system: Mapped[str | None] = mapped_column(String(40))
    confidence: Mapped[float | None] = mapped_column()


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[uuid.UUID] = _id()
    field_id: Mapped[uuid.UUID] = _fk("fields.id")
    rule_id: Mapped[str] = mapped_column(String(80), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class ConfidenceModel(Base):
    __tablename__ = "confidence_models"

    id: Mapped[uuid.UUID] = _id()
    version: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    features: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    split_hashes: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created()


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = _id()
    field_id: Mapped[uuid.UUID] = _fk("fields.id")
    reviewer_id: Mapped[uuid.UUID] = _fk("users.id")
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    corrected_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = _id()
    organization_id: Mapped[uuid.UUID] = _fk("organizations.id")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    before_hash: Mapped[str | None] = mapped_column(String(64))
    after_hash: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created()


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = _id()
    organization_id: Mapped[uuid.UUID] = _fk("organizations.id")
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = _created()


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = _id()
    webhook_id: Mapped[uuid.UUID] = _fk("webhooks.id")
    event: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = _created()
