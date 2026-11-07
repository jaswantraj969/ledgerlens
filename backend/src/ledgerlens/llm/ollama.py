"""Local Ollama provider using structured output. Nothing leaves this machine."""

import time
from typing import Any

import httpx

from ledgerlens.llm.base import LLMError, LLMRequest, LLMResponse

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 300.0
_NANOSECONDS = 1_000_000_000
_THINK_TAG = "<think>"


class OllamaProvider:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)
        self._digests: dict[str, str | None] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": request.model,
            "stream": False,
            "format": request.json_schema,
            "options": request.params,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.think is not None:
            payload["think"] = request.think
        try:
            reply = self._client.post("/api/chat", json=payload)
            reply.raise_for_status()
        except httpx.HTTPError as error:
            raise LLMError(f"ollama request failed: {type(error).__name__}") from error
        body = reply.json()
        content = body["message"]["content"]
        if request.think is False and (body["message"].get("thinking") or _THINK_TAG in content):
            # Thinking was turned off; a reply carrying reasoning is not a usable answer.
            raise LLMError("ollama reply contained reasoning text although thinking was off")
        return LLMResponse(
            text=content,
            model=request.model,
            model_digest=self._digest(request.model),
            done_reason=body.get("done_reason"),
            prompt_tokens=body.get("prompt_eval_count"),
            completion_tokens=body.get("eval_count"),
            latency_seconds=time.perf_counter() - started,
            load_seconds=_seconds(body.get("load_duration")),
        )

    def _digest(self, model: str) -> str | None:
        if model not in self._digests:
            reply = self._client.get("/api/tags")
            models: list[dict[str, Any]] = reply.json().get("models", [])
            self._digests[model] = next(
                (entry.get("digest") for entry in models if entry.get("name") == model), None
            )
        return self._digests[model]

    def loaded_models(self) -> list[dict[str, Any]]:
        """What Ollama reports as loaded, including how much of each model sits in VRAM."""
        models: list[dict[str, Any]] = self._client.get("/api/ps").json().get("models", [])
        return models


def _seconds(nanoseconds: int | None) -> float | None:
    return None if nanoseconds is None else nanoseconds / _NANOSECONDS
