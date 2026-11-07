"""Application factory."""

import time
import uuid
from collections.abc import Awaitable, Callable

import redis
import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import Histogram
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ledgerlens import __version__
from ledgerlens.api import auth, documents, health
from ledgerlens.core.config import Settings
from ledgerlens.core.errors import install_handlers
from ledgerlens.core.logs import configure_logging
from ledgerlens.storage.local import LocalStorage

REQUEST_SECONDS = Histogram(
    "ledgerlens_request_seconds", "HTTP request latency", ["method", "status"]
)
_log = structlog.get_logger()


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    resolved = settings or Settings()  # type: ignore[call-arg]
    app = FastAPI(title="LedgerLens", version=__version__)
    engine = create_engine(resolved.database_url, pool_pre_ping=True)
    app.state.settings = resolved
    app.state.engine = engine
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    app.state.redis = redis.Redis.from_url(resolved.redis_url, socket_connect_timeout=2)
    app.state.storage = LocalStorage(resolved.storage_dir)
    install_handlers(app)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        REQUEST_SECONDS.labels(request.method, response.status_code).observe(elapsed)
        _log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            seconds=round(elapsed, 4),
        )
        structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    return app
