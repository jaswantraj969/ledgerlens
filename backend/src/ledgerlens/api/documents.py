"""Document upload, listing, retrieval and deletion, and job status."""

import uuid
from datetime import datetime
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile
from pydantic import BaseModel

from ledgerlens.api.deps import (
    DocumentsDep,
    Principal,
    PrincipalDep,
    SessionDep,
    SettingsDep,
    rate_limit,
    require_role,
)
from ledgerlens.core.config import Settings
from ledgerlens.core.errors import Problem
from ledgerlens.db.models import Document, Job
from ledgerlens.db.repositories import DocumentRepository, audit
from ledgerlens.ingest.validate import validate_upload
from ledgerlens.storage.local import StorageBackend
from ledgerlens.workers.queue import enqueue

router = APIRouter(tags=["documents"])
MAX_BATCH_FILES = 20
UploaderDep = Annotated[Principal, Depends(require_role("admin", "reviewer"))]
AdminDep = Annotated[Principal, Depends(require_role("admin"))]
_not_found = Problem(404, "Not found", "No such document.", "not_found")


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    mime: str
    sha256: str
    status: str
    pages: int | None
    created_at: datetime
    duplicate: bool = False
    job_id: uuid.UUID | None = None


class BatchResult(BaseModel):
    filename: str | None
    document: DocumentOut | None = None
    error: str | None = None
    code: str | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    state: str
    attempts: int
    error_code: str | None
    error_detail: str | None
    dead_lettered: bool


def _out(document: Document, duplicate: bool, job: Job | None) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        mime=document.mime,
        sha256=document.sha256,
        status=document.status,
        pages=document.pages,
        created_at=document.created_at,
        duplicate=duplicate,
        job_id=job.id if job else None,
    )


def _enqueue(request: Request, settings: Settings, job: Job) -> None:
    """Queue a job once. Safe to repeat, so a retry recovers an upload that missed the queue.

    A job RQ already holds (waiting, running or scheduled for a retry) is not queued again.
    """
    client: redis.Redis = request.app.state.redis
    try:
        enqueue(client, settings, str(job.id))
    except redis.RedisError as error:
        raise Problem(
            503, "Service unavailable", "The job queue is unavailable.", "redis_unavailable"
        ) from error


def _ingest(
    filename: str | None,
    data: bytes,
    repository: DocumentRepository,
    principal: Principal,
    request: Request,
    settings: Settings,
) -> DocumentOut:
    upload = validate_upload(filename, data, settings.max_upload_bytes, settings.max_pages)
    existing = repository.by_sha256(upload.sha256)
    if existing is not None:
        job = repository.latest_job(existing.id)
        if job is not None and job.state == "queued":
            _enqueue(request, settings, job)
        return _out(existing, True, job)
    storage: StorageBackend = request.app.state.storage
    document = Document(
        filename=upload.filename,
        mime=upload.mime,
        sha256=upload.sha256,
        pages=upload.pages,
        storage_key=storage.put(principal.organization_id, upload.sha256, data),
    )
    repository.add(document)
    session = repository.session
    session.flush()
    job = Job(document_id=document.id)
    session.add(job)
    session.flush()
    audit(
        session,
        principal.organization_id,
        principal.user_id,
        "document.upload",
        "document",
        document.id,
        request_id=getattr(request.state, "request_id", None),
        after_hash=upload.sha256,
    )
    session.commit()
    _enqueue(request, settings, job)
    return _out(document, False, job)


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile,
    request: Request,
    response: Response,
    repository: DocumentsDep,
    principal: UploaderDep,
    settings: SettingsDep,
) -> DocumentOut:
    rate_limit(request, "upload", str(principal.user_id), settings.upload_rate_limit)
    data = await file.read(settings.max_upload_bytes + 1)
    result = _ingest(file.filename, data, repository, principal, request, settings)
    if result.duplicate:
        response.status_code = 200
    return result


@router.post("/documents/batch")
async def upload_batch(
    files: list[UploadFile],
    request: Request,
    repository: DocumentsDep,
    principal: UploaderDep,
    settings: SettingsDep,
) -> list[BatchResult]:
    """One result per file, so one bad file does not fail the others."""
    if len(files) > MAX_BATCH_FILES:
        raise Problem(413, "Too many files", f"At most {MAX_BATCH_FILES} files.", "batch_too_large")
    results = []
    for file in files:
        rate_limit(request, "upload", str(principal.user_id), settings.upload_rate_limit)
        data = await file.read(settings.max_upload_bytes + 1)
        try:
            document = _ingest(file.filename, data, repository, principal, request, settings)
            results.append(BatchResult(filename=document.filename, document=document))
        except Problem as problem:
            if problem.status >= 500:
                raise
            results.append(BatchResult(filename=None, error=problem.detail, code=problem.code))
    return results


@router.get("/documents")
def list_documents(
    repository: DocumentsDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentOut]:
    return [_out(document, False, None) for document in repository.list(limit, offset)]


@router.get("/documents/{document_id}")
def get_document(document_id: uuid.UUID, repository: DocumentsDep) -> DocumentOut:
    document = repository.get(document_id)
    if document is None:
        raise _not_found
    return _out(document, False, repository.latest_job(document.id))


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    principal: AdminDep,
) -> Response:
    repository = DocumentRepository(session, principal.organization_id)
    document = repository.get(document_id)
    if document is None:
        raise _not_found
    key = document.storage_key
    repository.delete(document)
    audit(
        session,
        principal.organization_id,
        principal.user_id,
        "document.delete",
        "document",
        document_id,
    )
    session.commit()
    request.app.state.storage.delete(key)
    return Response(status_code=204)


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, repository: DocumentsDep, _principal: PrincipalDep) -> JobOut:
    job = repository.get_job(job_id)
    if job is None:
        raise Problem(404, "Not found", "No such job.", "not_found")
    return JobOut(
        id=job.id,
        document_id=job.document_id,
        state=job.state,
        attempts=job.attempts,
        error_code=job.error_code,
        error_detail=job.error_detail,
        dead_lettered=job.dead_lettered_at is not None,
    )
