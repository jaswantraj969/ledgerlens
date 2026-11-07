"""The document job: parse, extract, verify, score, route, with results stored in PostgreSQL.

Claiming: a worker holds a PostgreSQL advisory lock on the job for as long as it runs. If the
worker dies, its connection closes and the lock is released, which is how recovery tells an
abandoned job from a running one.

Idempotency: each persisted step (parse, extract) is one transaction, keyed by a unique
(document, step, version) row. A retry reuses a finished step and redoes an unfinished one, so
a crash at any point leaves no partial or duplicate rows.

Failures: an error marked transient is raised so RQ retries it with backoff. On the last attempt,
or for a permanent error, the job is marked failed and dead-lettered with a reason. A model that
is unavailable never turns silently into a rules result labelled as the model: in "llm" mode
the job fails; in "llm_or_rules" mode the run is labelled as a rules fallback with the reason.

No document text or field value is logged.
"""

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache

import redis
import structlog
from rq import get_current_job
from sqlalchemy import Connection, Engine, create_engine, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from ledgerlens import __version__
from ledgerlens.core.config import Settings
from ledgerlens.db.models import (
    Document,
    ExtractionRun,
    Field,
    FieldEvidence,
    Job,
    OcrTokens,
    Validation,
    utcnow,
)
from ledgerlens.db.models import Page as PageRow
from ledgerlens.extraction.deterministic import DeterministicExtractor
from ledgerlens.extraction.llm import FALLBACK_SOURCE, LlmExtractor
from ledgerlens.fields import FieldRecord
from ledgerlens.llm.cache import CachingProvider, ReplayCache
from ledgerlens.llm.ollama import OllamaProvider
from ledgerlens.parsing.model import Page, ParsedDocument, Parser, Token
from ledgerlens.parsing.ocr import AutoParser
from ledgerlens.pipeline import Extractor, PrecomputedExtractor, process
from ledgerlens.schema import Schema, load_schema
from ledgerlens.storage.local import LocalStorage, StorageBackend
from ledgerlens.workers import webhooks
from ledgerlens.workers.queue import enqueue

_log = structlog.get_logger()
IN_PROGRESS = ("parsing", "extracting", "verifying", "scoring")
TERMINAL = ("ready_for_review", "completed", "failed")
PARSE_STEP = "parse"
EXTRACT_STEP = "extract"


class TransientJobError(Exception):
    """Worth retrying: the cause may go away (a model server or database restarting)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class PermanentJobError(Exception):
    """Retrying cannot help: the stored file is missing, or the model's output was unusable."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def checkpoint(step: str) -> None:
    """No-op hook between steps. Tests replace it to stop a worker at a known point."""


@dataclass
class ExtractionOutcome:
    records: list[FieldRecord]
    version: str
    provider: str
    model: str | None
    prompt_version: str | None
    degraded_reason: str | None = None
    latency_seconds: float | None = None
    cache_hit: bool | None = None


@dataclass
class WorkerContext:
    settings: Settings
    engine: Engine
    sessions: sessionmaker[Session]
    storage: StorageBackend
    redis: redis.Redis
    parser: Parser = field(default_factory=AutoParser)
    llm: Callable[[], LlmExtractor] | None = None

    @classmethod
    def build(cls, settings: Settings) -> "WorkerContext":
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        context = cls(
            settings=settings,
            engine=engine,
            sessions=sessionmaker(engine, expire_on_commit=False),
            storage=LocalStorage(settings.storage_dir),
            redis=redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2),
        )
        if settings.extraction_mode != "rules":
            context.llm = cache(lambda: _llm_extractor(settings))
        return context


def _llm_extractor(settings: Settings) -> LlmExtractor:
    provider = CachingProvider(
        ReplayCache(settings.llm_cache_dir),
        OllamaProvider(settings.ollama_url, timeout=settings.llm_timeout_seconds),
    )
    return LlmExtractor(provider, settings.llm_model, prompt=settings.llm_prompt)


def lock_key(job_id: uuid.UUID) -> int:
    return int.from_bytes(job_id.bytes[:8], "big", signed=True)


@contextmanager
def job_lock(engine: Engine, job_id: uuid.UUID) -> Iterator[bool]:
    """Hold the job's advisory lock on a dedicated connection. Yields whether it was taken."""
    with engine.connect() as connection:
        taken = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": lock_key(job_id)}
            ).scalar()
        )
        try:
            yield taken
        finally:
            if taken:
                _unlock(connection, job_id)


def _unlock(connection: Connection, job_id: uuid.UUID) -> None:
    connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key(job_id)})
    connection.commit()


def _set_state(context: WorkerContext, job_id: uuid.UUID, state: str) -> None:
    with context.sessions.begin() as session:
        job = session.get(Job, job_id)
        if job is not None:
            job.state = state
            document = session.get(Document, job.document_id)
            if document is not None:
                document.status = state


# Parse step ---------------------------------------------------------------------------------


def _load_parsed(session: Session, run: ExtractionRun) -> ParsedDocument:
    parser, _, parser_version = run.version.partition(":")
    rows = session.scalars(
        select(PageRow).where(PageRow.document_id == run.document_id).order_by(PageRow.number)
    ).all()
    pages = []
    for row in rows:
        stored = session.get(OcrTokens, row.id)
        tokens = [Token.model_validate(token) for token in (stored.tokens if stored else [])]
        pages.append(
            Page(
                number=row.number,
                width=row.width,
                height=row.height,
                coordinate_system=row.coordinate_system,
                source=row.source,  # type: ignore[arg-type]
                tokens=tokens,
            )
        )
    return ParsedDocument(parser=parser, parser_version=parser_version, pages=pages)


def _existing_run(session: Session, document_id: uuid.UUID, step: str) -> ExtractionRun | None:
    return session.scalar(
        select(ExtractionRun)
        .where(ExtractionRun.document_id == document_id, ExtractionRun.step == step)
        .order_by(ExtractionRun.created_at.desc())
    )


def parse_step(context: WorkerContext, document: Document, schema: Schema) -> ParsedDocument:
    with context.sessions() as session:
        run = _existing_run(session, document.id, PARSE_STEP)
        if run is not None:
            return _load_parsed(session, run)
    try:
        data = context.storage.get(document.storage_key)
    except OSError as error:
        raise PermanentJobError("file_missing", type(error).__name__) from error
    parsed = context.parser.parse(data)
    checkpoint("parse_computed")
    try:
        with context.sessions.begin() as session:
            session.add(
                ExtractionRun(
                    document_id=document.id,
                    step=PARSE_STEP,
                    version=f"{parsed.parser}:{parsed.parser_version}",
                    provider=parsed.parser,
                    schema_version=f"{schema.name}:{schema.version}",
                )
            )
            for page in parsed.pages:
                row = PageRow(
                    document_id=document.id,
                    number=page.number,
                    width=page.width,
                    height=page.height,
                    coordinate_system=page.coordinate_system,
                    source=page.source,
                )
                session.add(row)
                session.flush()
                session.add(OcrTokens(page_id=row.id, tokens=[t.model_dump() for t in page.tokens]))
    except IntegrityError:
        # Another attempt finished the step first. Use what it stored.
        with context.sessions() as session:
            run = _existing_run(session, document.id, PARSE_STEP)
            if run is None:
                raise
            return _load_parsed(session, run)
    return parsed


# Extract, verify, score ---------------------------------------------------------------------


def _rules(document: ParsedDocument, schema: Schema, reason: str | None) -> ExtractionOutcome:
    records = DeterministicExtractor().extract(document, schema)
    if reason is None:
        return ExtractionOutcome(
            records, f"rules:{__version__}:{schema.name}:{schema.version}", "deterministic",
            None, None,
        )  # fmt: skip
    for record in records:
        record.source = FALLBACK_SOURCE
    return ExtractionOutcome(
        records,
        f"rules-fallback:{__version__}:{schema.name}:{schema.version}",
        "deterministic",
        None,
        None,
        degraded_reason=reason,
    )


def extract(context: WorkerContext, document: ParsedDocument, schema: Schema) -> ExtractionOutcome:
    settings = context.settings
    if settings.extraction_mode == "rules" or context.llm is None:
        return _rules(document, schema, None)
    extractor = context.llm()
    result = extractor.run(document, schema)
    if not result.fell_back:
        responses = result.responses
        return ExtractionOutcome(
            result.records,
            f"llm:{settings.llm_model}:{extractor.prompt_version}:{schema.name}:{schema.version}",
            "ollama",
            settings.llm_model,
            extractor.prompt_version,
            latency_seconds=sum(r.latency_seconds or 0 for r in responses),
            cache_hit=all(r.cache_hit for r in responses) if responses else None,
        )
    provider_down = any(error.startswith("provider:") for error in result.errors)
    code = "llm_unavailable" if provider_down else "llm_invalid_output"
    detail = "; ".join(error[:200] for error in result.errors) or code
    if settings.extraction_mode == "llm_or_rules":
        return _rules(document, schema, f"{code}: {detail}")
    if provider_down:
        raise TransientJobError(code, detail)
    raise PermanentJobError(code, detail)


def _store_fields(session: Session, run: ExtractionRun, records: list[FieldRecord]) -> None:
    for record in records:
        row = Field(
            run_id=run.id,
            name=record.name,
            value_raw=record.value_raw,
            value_normalized=record.value_normalized,
            source=record.source,
            evidence_status=record.evidence_status,
            evidence_independent=record.evidence_independent,
            signals=dict(record.signals),
            risk_score=record.risk_score,
            calibrated_prob=record.calibrated_prob,
            decision=record.decision,
        )
        session.add(row)
        session.flush()
        for evidence in record.evidence:
            session.add(
                FieldEvidence(
                    field_id=row.id,
                    page=evidence.page,
                    text=evidence.text,
                    bbox=list(evidence.bbox) if evidence.bbox else None,
                    coordinate_system=evidence.coordinate_system,
                    confidence=evidence.confidence,
                )
            )
        for result in record.validation_results:
            session.add(
                Validation(
                    field_id=row.id,
                    rule_id=result.rule_id,
                    passed=result.passed,
                    message=result.message,
                )
            )


def extract_step(
    context: WorkerContext, job_id: uuid.UUID, document: Document, parsed: ParsedDocument,
    schema: Schema,
) -> ExtractionRun:  # fmt: skip
    with context.sessions() as session:
        run = _existing_run(session, document.id, EXTRACT_STEP)
        if run is not None:
            return run
    _set_state(context, job_id, "extracting")
    outcome = extract(context, parsed, schema)
    checkpoint("extract_computed")
    _set_state(context, job_id, "verifying")
    extractor: Extractor = PrecomputedExtractor(outcome.records)
    records = process(parsed, schema, extractor)
    _set_state(context, job_id, "scoring")
    try:
        with context.sessions.begin() as session:
            run = ExtractionRun(
                document_id=document.id,
                step=EXTRACT_STEP,
                version=outcome.version,
                model=outcome.model,
                provider=outcome.provider,
                prompt_version=outcome.prompt_version,
                schema_version=f"{schema.name}:{schema.version}",
                cost_usd=0.0,
                latency_seconds=outcome.latency_seconds,
                cache_hit=outcome.cache_hit,
                degraded_reason=outcome.degraded_reason,
            )
            session.add(run)
            session.flush()
            _store_fields(session, run, records)
    except IntegrityError:
        with context.sessions() as session:
            existing = _existing_run(session, document.id, EXTRACT_STEP)
            if existing is None:
                raise
            return existing
    return run


# The job ------------------------------------------------------------------------------------


def _finish(context: WorkerContext, job_id: uuid.UUID, run: ExtractionRun) -> str:
    with context.sessions.begin() as session:
        pending = session.scalar(
            select(func.count())
            .select_from(Field)
            .where(Field.run_id == run.id, Field.decision != "auto_accepted")
        )
        state = "ready_for_review" if pending else "completed"
        job = session.get(Job, job_id)
        if job is None:  # deleted with its document while running
            return "missing"
        job.state = state
        job.error_code = None
        job.error_detail = f"degraded: {run.degraded_reason}" if run.degraded_reason else None
        document = session.get(Document, job.document_id)
        deliveries: list[uuid.UUID] = []
        if document is not None:
            document.status = state
            deliveries = webhooks.emit(
                session, document.organization_id, f"job.{state}",
                {"job_id": str(job_id), "document_id": str(document.id), "state": state},
            )  # fmt: skip
    webhooks.enqueue_deliveries(context.redis, context.settings, deliveries)
    return state


def _record_failure(
    context: WorkerContext, job_id: uuid.UUID, code: str, detail: str, *, final: bool
) -> None:
    with context.sessions.begin() as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.error_code = code[:60]
        job.error_detail = detail[:2000]
        job.state = "failed" if final else "queued"
        if final:
            job.dead_lettered_at = utcnow()
        document = session.get(Document, job.document_id)
        deliveries: list[uuid.UUID] = []
        if document is not None:
            document.status = job.state
            if final:
                deliveries = webhooks.emit(
                    session, document.organization_id, "job.failed",
                    {"job_id": str(job_id), "document_id": str(document.id), "state": "failed",
                     "error_code": job.error_code},
                )  # fmt: skip
    if deliveries:
        webhooks.enqueue_deliveries(context.redis, context.settings, deliveries)


def run_job(context: WorkerContext, job_id: uuid.UUID, *, final_attempt: bool) -> str:
    """Run one attempt. Returns the job state afterwards, or "busy" if another worker has it."""
    with job_lock(context.engine, job_id) as taken:
        if not taken:
            _log.info("job.busy", job_id=str(job_id))
            return "busy"
        with context.sessions.begin() as session:
            job = session.get(Job, job_id)
            if job is None:
                return "missing"
            if job.state in TERMINAL:
                return job.state
            job.attempts += 1
            job.state = "parsing"
            document = session.get(Document, job.document_id)
            if document is None:
                return "missing"
            document.status = "parsing"
        _log.info("job.start", job_id=str(job_id), attempt=job.attempts)
        try:
            schema = load_schema(context.settings.schema_name)
            parsed = parse_step(context, document, schema)
            checkpoint("parsed")
            run = extract_step(context, job_id, document, parsed, schema)
            checkpoint("extracted")
            state = _finish(context, job_id, run)
        except PermanentJobError as error:
            _record_failure(context, job_id, error.code, error.detail, final=True)
            _log.warning("job.failed", job_id=str(job_id), code=error.code, retry=False)
            return "failed"
        except (TransientJobError, OperationalError, redis.RedisError) as error:
            code = error.code if isinstance(error, TransientJobError) else "transient_error"
            detail = error.detail if isinstance(error, TransientJobError) else type(error).__name__
            _record_failure(context, job_id, code, detail, final=final_attempt)
            _log.warning("job.failed", job_id=str(job_id), code=code, retry=not final_attempt)
            raise
        except Exception as error:
            _record_failure(context, job_id, "internal_error", type(error).__name__, final=True)
            _log.exception("job.failed", job_id=str(job_id), code="internal_error")
            raise
        _log.info("job.done", job_id=str(job_id), state=state)
        return state


def recover_abandoned(context: WorkerContext, max_attempts: int) -> list[uuid.UUID]:
    """Requeue jobs left in progress by a worker that died. Running jobs hold a lock and stay."""
    with context.sessions() as session:
        candidates = session.scalars(select(Job.id).where(Job.state.in_(IN_PROGRESS))).all()
    recovered = []
    for job_id in candidates:
        with job_lock(context.engine, job_id) as taken:
            if not taken:
                continue
            with context.sessions.begin() as session:
                job = session.get(Job, job_id)
                if job is None or job.state not in IN_PROGRESS:
                    continue
                if job.attempts >= max_attempts:
                    job.state = "failed"
                    job.error_code = "abandoned"
                    job.error_detail = f"worker stopped during {job.attempts} attempts"
                    job.dead_lettered_at = utcnow()
                    continue
                job.state = "queued"
                job.error_code = "abandoned"
                job.error_detail = "worker stopped mid-job; requeued"
        if enqueue(context.redis, context.settings, str(job_id), force=True):
            recovered.append(job_id)
            _log.warning("job.recovered", job_id=str(job_id))
    return recovered


_context: WorkerContext | None = None


def use_context(context: WorkerContext) -> None:
    """Set the context this process's jobs run with. The worker sets it once at start."""
    global _context
    _context = context


def _process_context() -> WorkerContext:
    if _context is None:
        use_context(WorkerContext.build(Settings()))  # type: ignore[call-arg]
    assert _context is not None  # noqa: S101 - set just above
    return _context


def process_document(job_id: str, context: WorkerContext | None = None) -> str:
    """RQ entry point. The last retry, or a job without retries, is the final attempt."""
    current = get_current_job()
    retries_left = current.retries_left if current is not None else None
    final = not retries_left
    return run_job(context or _process_context(), uuid.UUID(job_id), final_attempt=final)
