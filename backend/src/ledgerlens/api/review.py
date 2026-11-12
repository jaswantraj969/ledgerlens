"""Review: a document's extracted fields with evidence, review actions, the queue, pages, export
(single and batch) and the document's audit trail.

Every query is scoped to the caller's organization. Field values are never logged; the audit
log stores a hash of a corrected value, not the value. The audit trail route joins each review
event to its review decision to show the old and new value to the document's own organization.
"""

import hashlib
import uuid
from datetime import datetime
from io import BytesIO
from typing import Annotated, Literal

import pypdfium2 as pdfium
from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ledgerlens.api.deps import Principal, PrincipalDep, SessionDep, require_role
from ledgerlens.core.errors import Problem
from ledgerlens.db.models import (
    AuditLog,
    Document,
    ExtractionRun,
    Field,
    FieldEvidence,
    Job,
    Page,
    ReviewDecision,
    User,
    Validation,
)
from ledgerlens.db.repositories import DocumentRepository, audit
from ledgerlens.export.exporters import to_csv, to_json
from ledgerlens.extraction.deterministic import normalized_value
from ledgerlens.fields import FieldRecord
from ledgerlens.pipeline import field_type
from ledgerlens.schema import load_schema
from ledgerlens.workers import webhooks

router = APIRouter(tags=["review"])
ReviewerDep = Annotated[Principal, Depends(require_role("admin", "reviewer"))]
PENDING = "needs_review"
RENDER_SCALE = 2.0
MAX_EXPORT_DOCUMENTS = 50
REVIEWED = "completed"
_no_document = Problem(404, "Not found", "No such document.", "not_found")
_no_field = Problem(404, "Not found", "No such field.", "not_found")
_no_results = Problem(409, "Not ready", "This document has no extraction yet.", "not_ready")


class EvidenceOut(BaseModel):
    page: int
    text: str
    bbox: list[float] | None
    coordinate_system: str | None
    confidence: float | None


class ValidationOut(BaseModel):
    rule_id: str
    passed: bool
    message: str


class FieldOut(BaseModel):
    id: uuid.UUID
    name: str
    value_raw: str | None
    value_normalized: str | None
    final_value: str | None
    source: str
    evidence_status: str
    evidence_independent: bool
    risk_score: float | None
    calibrated_prob: float | None
    decision: str
    evidence: list[EvidenceOut]
    validations: list[ValidationOut]


class PageOut(BaseModel):
    number: int
    width: float
    height: float
    coordinate_system: str
    source: str


class DocumentFields(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str
    run_version: str
    provider: str | None
    degraded_reason: str | None
    pages: list[PageOut]
    fields: list[FieldOut]


class ReviewIn(BaseModel):
    action: Literal["approve", "reject", "correct"]
    value: str | None = PydanticField(default=None, max_length=2000)


class AuditEventOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_email: str | None
    action: str
    entity: str
    field_name: str | None
    old_value: str | None
    new_value: str | None


class BatchExportIn(BaseModel):
    document_ids: list[uuid.UUID] = PydanticField(min_length=1)
    format: Literal["json", "csv"] = "json"


class QueueItem(BaseModel):
    field_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    name: str
    value_raw: str | None
    risk_score: float | None
    created_at: datetime


def final_value(field: Field, correction: str | None) -> str | None:
    """What a field exports as: a correction, an accepted value, or nothing."""
    if field.decision == "corrected":
        return correction
    if field.decision in ("auto_accepted", "approved"):
        return field.value_raw
    return None


def _latest_run(session: Session, document_id: uuid.UUID) -> ExtractionRun | None:
    return session.scalar(
        select(ExtractionRun)
        .where(ExtractionRun.document_id == document_id, ExtractionRun.step == "extract")
        .order_by(ExtractionRun.created_at.desc())
    )


def _corrections(session: Session, field_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    """The latest review decision's corrected value per field."""
    rows = session.execute(
        select(ReviewDecision.field_id, ReviewDecision.corrected_value)
        .where(ReviewDecision.field_id.in_(field_ids))
        .order_by(ReviewDecision.created_at)
    ).all()
    return {field_id: value for field_id, value in rows}  # noqa: C416 - rows are tuples


def _document(session: Session, principal: Principal, document_id: uuid.UUID) -> Document:
    document = DocumentRepository(session, principal.organization_id).get(document_id)
    if document is None:
        raise _no_document
    return document


def _fields_out(session: Session, run: ExtractionRun) -> list[FieldOut]:
    fields = session.scalars(select(Field).where(Field.run_id == run.id).order_by(Field.name)).all()
    ids = [f.id for f in fields]
    evidence: dict[uuid.UUID, list[EvidenceOut]] = {i: [] for i in ids}
    for row in session.scalars(select(FieldEvidence).where(FieldEvidence.field_id.in_(ids))):
        evidence[row.field_id].append(
            EvidenceOut(
                page=row.page,
                text=row.text,
                bbox=row.bbox,
                coordinate_system=row.coordinate_system,
                confidence=row.confidence,
            )
        )
    checks: dict[uuid.UUID, list[ValidationOut]] = {i: [] for i in ids}
    for check in session.scalars(select(Validation).where(Validation.field_id.in_(ids))):
        checks[check.field_id].append(
            ValidationOut(rule_id=check.rule_id, passed=check.passed, message=check.message)
        )
    corrections = _corrections(session, ids)
    return [
        FieldOut(
            id=f.id,
            name=f.name,
            value_raw=f.value_raw,
            value_normalized=f.value_normalized,
            final_value=final_value(f, corrections.get(f.id)),
            source=f.source,
            evidence_status=f.evidence_status,
            evidence_independent=f.evidence_independent,
            risk_score=f.risk_score,
            calibrated_prob=f.calibrated_prob,
            decision=f.decision,
            evidence=evidence[f.id],
            validations=checks[f.id],
        )
        for f in fields
    ]


@router.get("/documents/{document_id}/fields")
def document_fields(
    document_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> DocumentFields:
    document = _document(session, principal, document_id)
    run = _latest_run(session, document.id)
    if run is None:
        raise _no_results
    pages = session.scalars(
        select(Page).where(Page.document_id == document.id).order_by(Page.number)
    ).all()
    return DocumentFields(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        run_version=run.version,
        provider=run.provider,
        degraded_reason=run.degraded_reason,
        pages=[
            PageOut(
                number=p.number,
                width=p.width,
                height=p.height,
                coordinate_system=p.coordinate_system,
                source=p.source,
            )
            for p in pages
        ],
        fields=_fields_out(session, run),
    )


def _owned_field(
    session: Session, principal: Principal, field_id: uuid.UUID
) -> tuple[Field, Document, ExtractionRun]:
    row = session.execute(
        select(Field, Document, ExtractionRun)
        .join(ExtractionRun, Field.run_id == ExtractionRun.id)
        .join(Document, ExtractionRun.document_id == Document.id)
        .where(Field.id == field_id, Document.organization_id == principal.organization_id)
    ).first()
    if row is None:
        raise _no_field
    return row[0], row[1], row[2]


@router.post("/fields/{field_id}/review")
def review_field(
    field_id: uuid.UUID,
    body: ReviewIn,
    request: Request,
    session: SessionDep,
    principal: ReviewerDep,
) -> FieldOut:
    field, document, run = _owned_field(session, principal, field_id)
    correction: str | None = None
    if body.action == "correct":
        if body.value is None or not body.value.strip():
            raise Problem(422, "Invalid review", "A correction needs a value.", "value_required")
        schema = load_schema(run.schema_version.split(":", 1)[0])
        correction = body.value.strip()
        if normalized_value(field_type(schema, field.name), correction) is None:
            raise Problem(
                422,
                "Invalid review",
                "The corrected value does not parse for this field.",
                "value_invalid",
            )
    field.decision = {"approve": "approved", "reject": "rejected", "correct": "corrected"}[
        body.action
    ]
    session.add(
        ReviewDecision(
            field_id=field.id,
            reviewer_id=principal.user_id,
            decision=field.decision,
            corrected_value=correction,
        )
    )
    audit(
        session,
        principal.organization_id,
        principal.user_id,
        f"field.{body.action}",
        "field",
        field.id,
        request_id=getattr(request.state, "request_id", None),
        after_hash=hashlib.sha256(correction.encode()).hexdigest() if correction else None,
    )
    session.flush()
    deliveries: list[uuid.UUID] = []
    pending = session.scalar(
        select(func.count())
        .select_from(Field)
        .where(Field.run_id == run.id, Field.decision == PENDING)
    )
    if not pending:
        document.status = "completed"
        job = session.scalar(
            select(Job).where(Job.document_id == document.id).order_by(Job.created_at.desc())
        )
        if job is not None and job.state == "ready_for_review":
            job.state = "completed"
        deliveries = webhooks.emit(
            session, principal.organization_id, "document.reviewed",
            {"document_id": str(document.id), "state": "completed"},
        )  # fmt: skip
    session.commit()
    if not pending and deliveries:
        webhooks.enqueue_deliveries(request.app.state.redis, request.app.state.settings, deliveries)
    return next(f for f in _fields_out(session, run) if f.id == field.id)


@router.get("/review/queue")
def review_queue(
    session: SessionDep,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[QueueItem]:
    """Fields waiting for a person, highest risk first. Only each document's latest run."""
    latest = (
        select(ExtractionRun.document_id, func.max(ExtractionRun.created_at).label("at"))
        .where(ExtractionRun.step == "extract")
        .group_by(ExtractionRun.document_id)
        .subquery()
    )
    rows = session.execute(
        select(Field, Document, ExtractionRun)
        .join(ExtractionRun, Field.run_id == ExtractionRun.id)
        .join(
            latest,
            (latest.c.document_id == ExtractionRun.document_id)
            & (latest.c.at == ExtractionRun.created_at),
        )
        .join(Document, ExtractionRun.document_id == Document.id)
        .where(Document.organization_id == principal.organization_id, Field.decision == PENDING)
        .order_by(Field.risk_score.desc().nulls_first(), Document.created_at, Field.name)
        .limit(limit)
    ).all()
    return [
        QueueItem(
            field_id=f.id,
            document_id=d.id,
            filename=d.filename,
            name=f.name,
            value_raw=f.value_raw,
            risk_score=f.risk_score,
            created_at=d.created_at,
        )
        for f, d, _ in rows
    ]


@router.get("/documents/{document_id}/pages/{number}/image")
def page_image(
    document_id: uuid.UUID,
    number: int,
    request: Request,
    session: SessionDep,
    principal: PrincipalDep,
) -> Response:
    """The page as an image. PDF pages are rendered at RENDER_SCALE pixels per point."""
    document = _document(session, principal, document_id)
    data = request.app.state.storage.get(document.storage_key)
    if document.mime != "application/pdf":
        if number != 1:
            raise Problem(404, "Not found", "No such page.", "not_found")
        return Response(data, media_type=document.mime, headers={"Cache-Control": "private"})
    pdf = pdfium.PdfDocument(data)
    try:
        if not 1 <= number <= len(pdf):
            raise Problem(404, "Not found", "No such page.", "not_found")
        image = pdf[number - 1].render(scale=RENDER_SCALE).to_pil()
    finally:
        pdf.close()
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "private"})


def _export_records(session: Session, document: Document) -> list[FieldRecord]:
    """Final values only: corrections, approvals and auto-accepted values. Others export empty."""
    run = _latest_run(session, document.id)
    if run is None:
        raise _no_results
    schema = load_schema(run.schema_version.split(":", 1)[0])
    return [
        FieldRecord(
            name=f.name,
            value_raw=f.final_value,
            value_normalized=normalized_value(field_type(schema, f.name), f.final_value),
            source=f.source,
            evidence_status=f.evidence_status,  # type: ignore[arg-type]
            risk_score=f.risk_score,
            calibrated_prob=f.calibrated_prob,
            decision=f.decision,  # type: ignore[arg-type]
        )
        for f in _fields_out(session, run)
    ]


def _export_response(payload: dict[str, list[FieldRecord]], format: str, name: str) -> Response:
    if format == "csv":
        disposition = f'attachment; filename="{name}.csv"'
        return Response(
            to_csv(payload), media_type="text/csv", headers={"Content-Disposition": disposition}
        )
    return Response(to_json(payload), media_type="application/json")


@router.get("/documents/{document_id}/export")
def export_document(
    document_id: uuid.UUID,
    session: SessionDep,
    principal: PrincipalDep,
    format: Annotated[Literal["json", "csv"], Query()] = "json",
) -> Response:
    """Final values only: corrections, approvals and auto-accepted values. Others export empty."""
    document = _document(session, principal, document_id)
    payload = {str(document.id): _export_records(session, document)}
    return _export_response(payload, format, str(document.id))


@router.post("/documents/export")
def export_documents(body: BatchExportIn, session: SessionDep, principal: PrincipalDep) -> Response:
    """Several reviewed documents in one file, in the same format as the single export.

    All or nothing: if any document is not the caller's organization's, or is not reviewed
    (status "completed"), nothing is exported and the error lists the refused ids.
    """
    ids = list(dict.fromkeys(body.document_ids))
    if len(ids) > MAX_EXPORT_DOCUMENTS:
        raise Problem(
            413, "Too many documents",
            f"At most {MAX_EXPORT_DOCUMENTS} documents per export.", "batch_too_large",
        )  # fmt: skip
    owned = {
        d.id: d
        for d in session.scalars(
            select(Document).where(
                Document.id.in_(ids), Document.organization_id == principal.organization_id
            )
        )
    }
    missing = [str(i) for i in ids if i not in owned]
    if missing:
        raise Problem(404, "Not found", "No such documents: " + ", ".join(missing), "not_found")
    unreviewed = [str(i) for i in ids if owned[i].status != REVIEWED]
    if unreviewed:
        raise Problem(
            409, "Not reviewed",
            "These documents are not reviewed yet: " + ", ".join(unreviewed), "not_reviewed",
        )  # fmt: skip
    payload = {str(i): _export_records(session, owned[i]) for i in ids}
    return _export_response(payload, body.format, "ledgerlens-export")


def _value_after(decision: str, value_raw: str | None, correction: str | None) -> str | None:
    if decision == "corrected":
        return correction
    if decision == "approved":
        return value_raw
    return None


@router.get("/documents/{document_id}/audit")
def document_audit(
    document_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[AuditEventOut]:
    """Read-only audit trail of one document and its fields, newest first.

    Old value: the value under review (the extracted value, or the previous correction).
    New value: the correction, the approved value, or none for a rejection.
    """
    document = _document(session, principal, document_id)
    fields = {
        str(f.id): f
        for f in session.scalars(
            select(Field)
            .join(ExtractionRun, Field.run_id == ExtractionRun.id)
            .where(ExtractionRun.document_id == document.id)
        )
    }
    events = session.execute(
        select(AuditLog, User.email)
        .outerjoin(
            User,
            (User.id == AuditLog.actor_id) & (User.organization_id == AuditLog.organization_id),
        )
        .where(
            AuditLog.organization_id == principal.organization_id,
            ((AuditLog.entity == "document") & (AuditLog.entity_id == str(document.id)))
            | ((AuditLog.entity == "field") & AuditLog.entity_id.in_(list(fields))),
        )
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    decisions: dict[str, list[ReviewDecision]] = {}
    for decision in session.scalars(
        select(ReviewDecision)
        .where(ReviewDecision.field_id.in_([f.id for f in fields.values()]))
        .order_by(ReviewDecision.created_at, ReviewDecision.id)
    ):
        decisions.setdefault(str(decision.field_id), []).append(decision)
    # One review request writes one decision and one audit entry for its field, so the n-th
    # review event of a field belongs to its n-th decision.
    seen: dict[str, int] = {}
    current: dict[str, str | None] = {k: f.value_raw for k, f in fields.items()}
    out: list[AuditEventOut] = []
    for entry, email in events:
        field = fields.get(entry.entity_id or "") if entry.entity == "field" else None
        old_value = new_value = None
        if field is not None:
            key = str(field.id)
            index = seen.get(key, 0)
            seen[key] = index + 1
            matched = decisions.get(key, [])
            if index < len(matched):
                decision = matched[index]
                old_value = current[key]
                new_value = _value_after(
                    decision.decision, field.value_raw, decision.corrected_value
                )
                if decision.decision == "corrected":
                    current[key] = decision.corrected_value
        out.append(
            AuditEventOut(
                id=entry.id,
                created_at=entry.created_at,
                actor_email=email,
                action=entry.action,
                entity=entry.entity,
                field_name=field.name if field is not None else None,
                old_value=old_value,
                new_value=new_value,
            )
        )
    return out[::-1]
