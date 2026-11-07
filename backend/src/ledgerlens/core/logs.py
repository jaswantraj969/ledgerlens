"""Structured JSON logs. Sensitive keys are redacted before anything is written."""

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

REDACTED = "[redacted]"
SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "document_text",
        "password",
        "refresh_token",
        "secret",
        "text",
        "token",
        "value",
        "value_normalized",
        "value_raw",
    }
)


def redact(_logger: Any, _method: str, event: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key in event:
        if key.casefold() in SENSITIVE_KEYS:
            event[key] = REDACTED
    return event


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
