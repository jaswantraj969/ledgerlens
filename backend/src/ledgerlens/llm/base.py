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
    # None: the provider's default. False: ask a reasoning model not to think (qwen3).
    think: bool | None = None

    def cache_key(self) -> str:
        """sha256 of model, prompt, params and schema version, as ADR-0003 specifies.

        `think` joins the key only when set, so keys recorded before it existed still match.
        """
        fields: dict[str, Any] = {
            "model": self.model,
            "system": self.system,
            "prompt": self.prompt,
            "params": self.params,
            "json_schema": self.json_schema,
            "schema_version": self.schema_version,
        }
        if self.think is not None:
            fields["think"] = self.think
        payload = json.dumps(
            fields,
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
