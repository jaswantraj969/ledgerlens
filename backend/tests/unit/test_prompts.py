import json

import pytest
from tests.unit.test_llm import VALID, ScriptedProvider, document

from ledgerlens.extraction import prompts
from ledgerlens.extraction.llm import SYSTEM_PROMPT, LlmExtractor, _prompt, _prompt_b
from ledgerlens.pipeline import PrecomputedExtractor, process
from ledgerlens.schema import load_schema

SCHEMA = load_schema("cord_receipt")


def first_request(prompt: str, mode: str = "a"):  # type: ignore[no-untyped-def]
    provider = ScriptedProvider(VALID)
    extractor = LlmExtractor(provider, "m", mode=mode, prompt=prompt)  # type: ignore[arg-type]
    extractor.run(document(), SCHEMA)
    return provider.requests[0]


@pytest.mark.parametrize(("mode", "build"), [("a", _prompt), ("b", _prompt_b)])
def test_prompt_1_0_requests_are_unchanged_so_recorded_replies_replay(mode, build) -> None:  # type: ignore[no-untyped-def]
    request = first_request("1.0", mode)
    assert request.prompt == build(document(), SCHEMA)
    assert request.system == SYSTEM_PROMPT
    assert request.schema_version == f"cord_receipt:{SCHEMA.version}:{mode}-1.0"
    assert set(request.json_schema["properties"]) == {
        "subtotal", "tax_amount", "total_amount", "line_items",
    }  # fmt: skip


def test_unknown_prompt_versions_are_refused() -> None:
    with pytest.raises(ValueError, match="unknown prompt"):
        LlmExtractor(ScriptedProvider(), "m", prompt="9.9")


def test_round_two_prompts_carry_the_review_changes() -> None:
    text = first_request("2.0").prompt
    assert "Null if no total is printed" in text
    assert "Never make an entry from a summary or payment line" in text
    assert "quantity" in text and "whenever the line prints one" in text
    assert "_evidence" not in text
    assert first_request("2.0").system == prompts.SYSTEM_PROMPT_2


def test_evidence_prompts_ask_for_and_allow_evidence_fields() -> None:
    request = first_request("2.1")
    assert "_evidence" in request.prompt
    assert "total_amount_evidence" in request.json_schema["properties"]
    assert "<example>" not in request.prompt
    assert "<example>" in first_request("2.2").prompt


def test_the_example_is_left_out_for_schemas_it_does_not_fit() -> None:
    text = prompts.prompt_a(document(), load_schema("default"), "2.2")
    assert "<example>" not in text


def test_prompt_versions_change_the_cache_key() -> None:
    keys = {first_request(version).cache_key() for version in ("1.0", "2.0", "2.1", "2.2")}
    assert len(keys) == 4


def test_quoted_evidence_is_checked_against_the_document() -> None:
    reply = json.loads(VALID) | {
        "total_amount_evidence": "Total 10,000",
        "subtotal_evidence": "Subtotal 99,999 invented",
    }
    provider = ScriptedProvider(json.dumps(reply))
    result = LlmExtractor(provider, "m", prompt="2.1").run(document(), SCHEMA)
    records = {r.name: r for r in process(document(), SCHEMA, PrecomputedExtractor(result.records))}
    assert records["total_amount"].signals["llm_evidence_found"] is True
    assert records["total_amount"].signals["llm_value_in_evidence"] is True
    assert records["subtotal"].signals["llm_evidence_found"] is False
    assert records["subtotal"].signals["llm_value_in_evidence"] is False
    assert records["tax_amount"].signals["llm_evidence_found"] is None
    assert "llm_evidence" not in {
        k for r in records.values() if r.name.startswith("line") for k in r.signals
    }
