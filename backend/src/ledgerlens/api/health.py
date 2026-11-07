"""Liveness, readiness and metrics."""

import redis
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from rq import Worker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
def ready(request: Request) -> JSONResponse:
    state = request.app.state
    checks = {"database": True, "redis": True, "storage": state.storage.healthy(), "worker": False}
    try:
        with state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        checks["database"] = False
    try:
        state.redis.ping()
        checks["worker"] = Worker.count(connection=state.redis) > 0
    except redis.RedisError:
        checks["redis"] = False
    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
