"""Data access. Tenant queries require an organization id, so scoping cannot be forgotten."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlens.db.models import AuditLog, Document, Job


class DocumentRepository:
    def __init__(self, session: Session, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def get(self, document_id: uuid.UUID) -> Document | None:
        return self.session.scalar(
            select(Document).where(
                Document.id == document_id, Document.organization_id == self.organization_id
            )
        )

    def by_sha256(self, sha256: str) -> Document | None:
        return self.session.scalar(
            select(Document).where(
                Document.sha256 == sha256, Document.organization_id == self.organization_id
            )
        )

    def list(self, limit: int, offset: int) -> Sequence[Document]:
        return self.session.scalars(
            select(Document)
            .where(Document.organization_id == self.organization_id)
            .order_by(Document.created_at.desc(), Document.id)
            .limit(limit)
            .offset(offset)
        ).all()

    def add(self, document: Document) -> None:
        document.organization_id = self.organization_id
        self.session.add(document)

    def delete(self, document: Document) -> None:
        self.session.delete(document)

    def latest_job(self, document_id: uuid.UUID) -> Job | None:
        return self.session.scalar(
            select(Job)
            .join(Document, Job.document_id == Document.id)
            .where(Job.document_id == document_id, Document.organization_id == self.organization_id)
            .order_by(Job.created_at.desc())
        )

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self.session.scalar(
            select(Job)
            .join(Document, Job.document_id == Document.id)
            .where(Job.id == job_id, Document.organization_id == self.organization_id)
        )


def audit(
    session: Session,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    entity: str,
    entity_id: object,
    *,
    request_id: str | None = None,
    after_hash: str | None = None,
) -> None:
    session.add(
        AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id),
            after_hash=after_hash,
            request_id=request_id,
        )
    )
