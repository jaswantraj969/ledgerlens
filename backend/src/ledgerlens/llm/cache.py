"""Disk replay cache. Every LLM call goes through here, so results reproduce offline."""

import json
from pathlib import Path

from ledgerlens.llm.base import LLMError, LLMProvider, LLMRequest, LLMResponse


class ReplayMissError(LLMError):
    """Replay mode found no cached response. It never falls through to a live call."""


class ReplayCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path_for(self, key: str) -> Path:
        return self._path(key)

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, request: LLMRequest) -> LLMResponse | None:
        path = self._path(request.cache_key())
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        return LLMResponse.model_validate(entry["response"])

    def put(self, request: LLMRequest, response: LLMResponse) -> None:
        path = self._path(request.cache_key())
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "schema_version": request.schema_version,
            "model": request.model,
            "params": request.params,
            "response": response.model_dump(mode="json"),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


class CachingProvider:
    """Record mode calls the provider on a miss. Replay mode (provider None) raises instead."""

    def __init__(self, cache: ReplayCache, provider: LLMProvider | None = None) -> None:
        self.cache = cache
        self.provider = provider
        self.hits = 0
        self.live_calls = 0
        # Keys of every reply used, so a run can say when each of its timings was recorded.
        self.keys_used: list[str] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.keys_used.append(request.cache_key())
        cached = self.cache.get(request)
        if cached is not None:
            self.hits += 1
            return cached.model_copy(update={"cache_hit": True})
        if self.provider is None:
            raise ReplayMissError(request.cache_key())
        self.live_calls += 1
        response = self.provider.complete(request)
        self.cache.put(request, response)
        return response
