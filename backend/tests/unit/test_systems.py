import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from evals.runners.run_cord import latency_report, llm_timing, percentiles
from evals.scoring import to_prediction
from evals.systems import SystemOutput, build_system, s2, s3, s4, s4h, withhold_unverified

from ledgerlens.extraction.llm import LlmExtractor
from ledgerlens.fields import FieldRecord
from ledgerlens.llm.base import LLMRequest, LLMResponse
from ledgerlens.parsing.model import Page, ParsedDocument, Token
from ledgerlens.schema import load_schema

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = load_schema("cord_receipt")


def reply(total: str = "10,000", rows: list[dict[str, str | None]] | None = None) -> str:
    return json.dumps(
        {"subtotal": None, "tax_amount": None, "total_amount": total, "line_items": rows or []}
    )


def document() -> ParsedDocument:
    rows = [["Tea", "10,000"], ["Total", "10,000"]]
    tokens = [
        Token(text=word, bbox=(10.0 + x * 60, 10.0 + y * 20, 60.0 + x * 60, 20.0 + y * 20))
        for y, row in enumerate(rows)
        for x, word in enumerate(row)
    ]
    page = Page(number=1, width=300, height=300, source="ocr", tokens=tokens)
    return ParsedDocument(parser="t", parser_version="0", pages=[page])


class Scripted:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self.replies.pop(0), model=request.model)


def extractor(*replies: str, mode: str = "a") -> LlmExtractor:
    return LlmExtractor(Scripted(*replies), "m", mode=mode)  # type: ignore[arg-type]


def value(output: SystemOutput, name: str) -> str | None:
    return next(r.value_raw for r in output.records if r.name == name)


def test_s2_keeps_a_value_missing_from_the_document() -> None:
    assert value(s2(document(), SCHEMA, extractor(reply("99,999"))), "total_amount") == "99,999"


def test_s3_withholds_a_value_missing_from_the_document() -> None:
    output = s3(document(), SCHEMA, extractor(reply("99,999")))
    assert value(output, "total_amount") is None
    assert output.withheld == 1


def test_s3_keeps_a_supported_value() -> None:
    output = s3(document(), SCHEMA, extractor(reply()))
    assert value(output, "total_amount") == "10,000"
    assert output.withheld == 0


def test_s3_withholds_a_value_that_does_not_parse() -> None:
    assert value(s3(document(), SCHEMA, extractor(reply("abc"))), "total_amount") is None


def test_withholding_never_blanks_self_sourced_values_for_lack_of_evidence() -> None:
    record = FieldRecord(
        name="total_amount", value_raw="1", value_normalized="1", source="deterministic",
        evidence_status="self_sourced",
    )  # fmt: skip
    assert withhold_unverified([record]) == 0
    assert record.value_raw == "1"


def test_s2_fallback_is_a_failed_document() -> None:
    output = s2(document(), SCHEMA, extractor("no", "no"))
    assert output.failed is True
    assert output.fallbacks == 1
    prediction = to_prediction("d", output.records, ("total_amount",), fell_back=output.failed)
    assert prediction.failed is True
    assert prediction.header == {"total_amount": None}


def test_s3_does_not_rescue_a_failed_extraction() -> None:
    assert s3(document(), SCHEMA, extractor("no", "no")).failed is True


def test_s4_rules_and_pass_b_outvote_a_wrong_pass_a() -> None:
    output = s4(document(), SCHEMA, extractor(reply("10,001")), extractor(reply(), mode="b"))
    assert value(output, "total_amount") == "10,000"


def test_s4_survives_one_failed_pass_and_counts_it() -> None:
    output = s4(document(), SCHEMA, extractor("x", "y"), extractor(reply(), mode="b"))
    assert output.failed is False
    assert output.fallbacks == 1


def test_s4_with_both_passes_failed_is_a_failed_document() -> None:
    output = s4(document(), SCHEMA, extractor("x", "y"), extractor("x", "y", mode="b"))
    assert output.failed is True
    assert output.fallbacks == 2


def test_s4h_takes_the_rule_value_when_a_pass_agrees() -> None:
    output = s4h(document(), SCHEMA, extractor(reply("10,001")), extractor(reply(), mode="b"))
    total = next(r for r in output.records if r.name == "total_amount")
    assert total.value_raw == "10,000"
    assert total.source == "deterministic"
    assert total.signals["s4h_choice"] == "rules"
    assert total.signals["agree_rules_llm"] is True


def test_s4h_takes_no_value_that_is_not_in_the_document() -> None:
    output = s4h(
        document(), SCHEMA, extractor(reply("99,999")), extractor(reply("88,888"), mode="b")
    )
    assert value(output, "total_amount") is None


def test_s4h_survives_one_failed_pass_and_fails_with_both() -> None:
    one = s4h(document(), SCHEMA, extractor("x", "y"), extractor(reply(), mode="b"))
    assert (one.failed, one.fallbacks, value(one, "total_amount")) == (False, 1, "10,000")
    both = s4h(document(), SCHEMA, extractor("x", "y"), extractor("x", "y", mode="b"))
    assert both.failed is True


def test_pass_b_uses_its_own_prompt_and_cache_key() -> None:
    seen: list[LLMRequest] = []

    class Recording(Scripted):
        def complete(self, request: LLMRequest) -> LLMResponse:
            seen.append(request)
            return super().complete(request)

    for mode in ("a", "b"):
        LlmExtractor(Recording(reply()), "m", mode=mode).run(document(), SCHEMA)  # type: ignore[arg-type]
    assert seen[0].cache_key() != seen[1].cache_key()
    assert seen[1].schema_version.endswith("b-1.0")
    assert "1: Tea 10,000" in seen[1].prompt


def test_unknown_system_and_missing_provider_are_refused() -> None:
    with pytest.raises(ValueError, match="provider"):
        build_system("S2", None, "m")
    with pytest.raises(ValueError, match="unknown"):
        build_system("S9", Scripted(), "m")


def test_llm_timing_removes_load_from_warm_latency() -> None:
    output = SystemOutput([])
    output.responses = [LLMResponse(text="", model="m", latency_seconds=72.0, load_seconds=70.0)]
    assert llm_timing(output) == (2.0, 70.0)


def row(load: float, llm: float) -> dict[str, float]:
    return {"load_seconds": load, "llm_seconds": llm, "ocr_seconds": 1.0, "local_seconds": 0.0}


def test_cold_documents_are_reported_apart_from_warm_ones() -> None:
    report = latency_report([row(70.0, 50.0), row(0.0, 2.0), row(0.0, 4.0)], replayed=False)
    assert report["warm_llm"]["n"] == 2
    assert report["warm_llm"]["p50"] == 3.0
    assert report["cold"]["documents"] == 1
    assert report["cold"]["model_load_seconds"] == [70.0]
    assert report["warm_total"]["p50"] == 4.0


def test_empty_percentiles_are_null() -> None:
    assert percentiles([]) == {"n": 0, "p50": None, "p95": None}


def run_module(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "evals.runners.run_cord", *arguments],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "backend" / "src"))),
            "SYSTEMROOT": "C:\\Windows",
            "PATH": "",
        },
        check=False,
    )


@pytest.mark.parametrize("system", ["S1", "S2", "S3", "S4", "S4h"])
def test_test_split_needs_final_for_every_system(system: str) -> None:
    completed = run_module("--system", system, "--split", "test")
    assert completed.returncode != 0
    assert "--final" in completed.stderr
