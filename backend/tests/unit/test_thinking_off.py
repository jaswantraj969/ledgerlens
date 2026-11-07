import json
from dataclasses import replace

import httpx
import pytest
from tests.unit.test_llm import VALID, ScriptedProvider, document, ollama, request

from ledgerlens.extraction.llm import LlmExtractor, thinking_off
from ledgerlens.llm.base import LLMError
from ledgerlens.schema import load_schema

# Recorded before `think` existed. Every reply in the replay cache is keyed this way.
OLD_KEY_PAYLOAD = request(seed=1)


def reply(content: str = VALID, thinking: str | None = None) -> httpx.Response:
    message: dict[str, str] = {"content": content}
    if thinking is not None:
        message["thinking"] = thinking
    return httpx.Response(200, json={"message": message, "done_reason": "stop"})


def handler_with(response: httpx.Response, sent: dict[str, object]):  # type: ignore[no-untyped-def]
    def handler(call: httpx.Request) -> httpx.Response:
        if call.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        sent.update(json.loads(call.content))
        return response

    return handler


def test_unset_think_keeps_recorded_cache_keys() -> None:
    assert replace(OLD_KEY_PAYLOAD, think=None).cache_key() == OLD_KEY_PAYLOAD.cache_key()
    assert replace(OLD_KEY_PAYLOAD, think=False).cache_key() != OLD_KEY_PAYLOAD.cache_key()


def test_think_false_is_sent_and_unset_think_is_not() -> None:
    sent: dict[str, object] = {}
    ollama(handler_with(reply(), sent)).complete(replace(request(), think=False))
    assert sent["think"] is False
    sent.clear()
    ollama(handler_with(reply(), sent)).complete(request())
    assert "think" not in sent


@pytest.mark.parametrize(
    "response",
    [reply(thinking="Let me work out the total first."), reply(content="<think>hmm</think>{}")],
)
def test_reasoning_text_with_thinking_off_is_a_failure(response: httpx.Response) -> None:
    with pytest.raises(LLMError, match="reasoning"):
        ollama(handler_with(response, {})).complete(replace(request(), think=False))


def test_an_empty_thinking_field_is_accepted() -> None:
    response = ollama(handler_with(reply(thinking=""), {})).complete(
        replace(request(), think=False)
    )
    assert response.text == VALID


def test_thinking_is_turned_off_for_qwen3_only() -> None:
    assert thinking_off("qwen3:4b") is False
    assert thinking_off("llama3.2:3b") is None


def test_the_extractor_asks_qwen3_not_to_think_and_leaves_llama_alone() -> None:
    schema = load_schema("cord_receipt")
    for model, expected in (("qwen3:4b", False), ("llama3.2:3b", None)):
        provider = ScriptedProvider(VALID)
        LlmExtractor(provider, model, prompt="2.2").run(document(), schema)
        assert provider.requests[0].think is expected
