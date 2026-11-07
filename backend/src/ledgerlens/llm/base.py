"""Provider-neutral LLM request and response types."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel


class LLMError(Exception):
    """A provider could not produce a response."""


@dataclass(frozen=True)
class LLMRequest:
    model: str
    prompt: str
    system: str
    json_schema: dict[str, Any]
    schema_version: str
    params: dict[str, Any] = field(default_factory=dict)

    def cache_key(self) -> str:
        """sha256 of model, prompt, params and schema version, as ADR-0003 specifies."""
        payload = json.dumps(
            {
                "model": self.model,
                "system": self.system,
                "prompt": self.prompt,
                "params": self.params,
                "json_schema": self.json_schema,
                "schema_version": self.schema_version,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class LLMResponse(BaseModel):
    text: str
    model: str
    model_digest: str | None = None
    done_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_seconds: float | None = None
    load_seconds: float | None = None
    cache_hit: bool = False


class LLMProvider(Protocol):
    def complete(self, request: LLMRequest) -> LLMResponse: ...
