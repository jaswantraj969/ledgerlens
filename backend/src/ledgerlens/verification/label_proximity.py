"""Label proximity: is a monetary header value printed next to a label for its field?

A value is label-supported if a token window on some line normalises to the value, and a keyword
for the field appears on that line or on the line directly above or below it (same page), outside
the value's own tokens. Keywords come from label_keywords.yaml, per schema and field.

Only values from an independent source are checked. A rule-extracted value was found by looking
for its label, so checking it against labels would be circular; it gets no result.
"""

import re
from decimal import Decimal
from functools import cache
from pathlib import Path

import yaml

from ledgerlens.extraction.layout import Line
from ledgerlens.fields import FieldRecord, ValidationResult
from ledgerlens.verification.evidence import TOKEN_DERIVED_SOURCES
from ledgerlens.verification.normalize import normalize_amount

RULE_ID = "label_proximity"
KEYWORDS_FILE = Path(__file__).with_name("label_keywords.yaml")
_MAX_WINDOW = 4


@cache
def keyword_config() -> dict[str, object]:
    return dict(yaml.safe_load(KEYWORDS_FILE.read_text(encoding="utf-8")))


def keywords_for(schema_name: str) -> dict[str, tuple[str, ...]]:
    schemas = keyword_config()["schemas"]
    assert isinstance(schemas, dict)  # noqa: S101 - fixed file shipped with the code
    return {field: tuple(words) for field, words in (schemas.get(schema_name) or {}).items()}


@cache
def _pattern(keywords: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(word.casefold()) for word in sorted(keywords, key=len)[::-1])
    return re.compile(rf"(?<![a-z0-9])(?:{alternatives})(?![a-z0-9])")


def _value_spans(line: Line, target: Decimal) -> list[tuple[int, int]]:
    """Token index ranges [start, end) on `line` whose text normalises to `target`."""
    texts = [token.text for token in line.tokens]
    spans = []
    for start in range(len(texts)):
        for end in range(start + 1, min(start + _MAX_WINDOW, len(texts)) + 1):
            if normalize_amount(" ".join(texts[start:end])) == target:
                spans.append((start, end))
    return spans


def _text_without(line: Line, span: tuple[int, int] | None) -> str:
    texts = [token.text for token in line.tokens]
    if span is not None:
        texts = texts[: span[0]] + texts[span[1] :]
    return " ".join(texts).casefold()


def label_supported(value: str | None, lines: list[Line], keywords: tuple[str, ...]) -> bool | None:
    """True or False for a parsable amount; None when there is nothing to check."""
    if not value or not keywords:
        return None
    target = normalize_amount(value)
    if target is None:
        return None
    pattern = _pattern(keywords)
    for index, line in enumerate(lines):
        for span in _value_spans(line, target):
            if pattern.search(_text_without(line, span)):
                return True
            for neighbour in (index - 1, index + 1):
                beside = 0 <= neighbour < len(lines) and lines[neighbour].page == line.page
                if beside and pattern.search(_text_without(lines[neighbour], None)):
                    return True
    return False


def check_label_proximity(
    record: FieldRecord, lines: list[Line], keywords: tuple[str, ...]
) -> None:
    """Attach the result and the `label_supported` signal. Dependent sources get neither."""
    if record.source in TOKEN_DERIVED_SOURCES:
        record.signals["label_supported"] = None
        return
    supported = label_supported(record.value_raw, lines, keywords)
    record.signals["label_supported"] = supported
    if supported is not None:
        record.validation_results.append(
            ValidationResult(
                rule_id=RULE_ID,
                passed=supported,
                message="value is next to a label for this field"
                if supported
                else "no label for this field on the value's line or the lines beside it",
            )
        )
