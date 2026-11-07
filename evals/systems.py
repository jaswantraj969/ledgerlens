"""The evaluated systems. Definitions are in docs/evaluation.md and fixed before any run.

S1: deterministic rules on OCR tokens.
S2: LLM pass A, values as returned.
S3: S2 plus verification: a value is withheld if it does not parse or its independent
    evidence check finds nothing in the document.
S4: pass A, pass B and rules merged by normalised agreement, then the S3 check.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ledgerlens.extraction.deterministic import DeterministicExtractor
from ledgerlens.extraction.llm import ExtractionAttempts, LlmExtractor
from ledgerlens.extraction.merge import merge_sources
from ledgerlens.fields import FieldRecord
from ledgerlens.llm.base import LLMProvider, LLMResponse
from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.pipeline import PrecomputedExtractor, process
from ledgerlens.schema import Schema

LLM_SYSTEMS = ("S2", "S3", "S4")


@dataclass
class SystemOutput:
    records: list[FieldRecord]
    failed: bool = False
    fallbacks: int = 0
    attempts: int = 0
    retries: int = 0
    responses: list[LLMResponse] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    withheld: int = 0


def withhold_unverified(records: list[FieldRecord]) -> int:
    """Blank values that fail verification. Self-sourced values have no independent check."""
    withheld = 0
    for record in records:
        if record.value_raw is None:
            continue
        unparsable = record.value_normalized is None
        unsupported = record.evidence_independent and record.evidence_status == "not_found"
        if unparsable or unsupported:
            record.signals["withheld_value"] = record.value_raw
            record.value_raw = None
            record.value_normalized = None
            withheld += 1
    return withheld


def _count(output: SystemOutput, result: ExtractionAttempts) -> None:
    output.attempts += result.attempts
    output.retries += max(result.attempts - 1, 0)
    output.fallbacks += int(result.fell_back)
    output.responses.extend(result.responses)
    output.errors.extend(result.errors)


def s1(document: ParsedDocument, schema: Schema) -> SystemOutput:
    return SystemOutput(process(document, schema))


def s2(document: ParsedDocument, schema: Schema, pass_a: LlmExtractor) -> SystemOutput:
    result = pass_a.run(document, schema)
    output = SystemOutput(process(document, schema, PrecomputedExtractor(result.records)))
    output.failed = result.fell_back
    _count(output, result)
    return output


def s3(document: ParsedDocument, schema: Schema, pass_a: LlmExtractor) -> SystemOutput:
    output = s2(document, schema, pass_a)
    if not output.failed:
        output.withheld = withhold_unverified(output.records)
    return output


def s4(
    document: ParsedDocument, schema: Schema, pass_a: LlmExtractor, pass_b: LlmExtractor
) -> SystemOutput:
    """A failed pass is an empty source. The document fails only if both passes fail."""
    first, second = pass_a.run(document, schema), pass_b.run(document, schema)
    rules = DeterministicExtractor().extract(document, schema)
    merged = merge_sources(
        [] if first.fell_back else first.records,
        [] if second.fell_back else second.records,
        rules,
        schema,
    )
    output = SystemOutput(process(document, schema, PrecomputedExtractor(merged)))
    output.failed = first.fell_back and second.fell_back
    _count(output, first)
    _count(output, second)
    if not output.failed:
        output.withheld = withhold_unverified(output.records)
    return output


def build_system(
    name: str, provider: LLMProvider | None, model: str, params: dict[str, Any] | None = None
) -> Callable[[ParsedDocument, Schema], SystemOutput]:
    if name == "S1":
        return s1
    if provider is None:
        raise ValueError(f"{name} needs a provider")
    pass_a = LlmExtractor(provider, model, params)
    if name == "S2":
        return lambda document, schema: s2(document, schema, pass_a)
    if name == "S3":
        return lambda document, schema: s3(document, schema, pass_a)
    if name == "S4":
        pass_b = LlmExtractor(provider, model, params, mode="b")
        return lambda document, schema: s4(document, schema, pass_a, pass_b)
    raise ValueError(f"unknown system {name}")
