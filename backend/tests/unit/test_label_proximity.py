from ledgerlens.extraction.layout import Line, build_lines
from ledgerlens.fields import FieldRecord
from ledgerlens.parsing.model import Page, ParsedDocument, Token
from ledgerlens.pipeline import process
from ledgerlens.schema import load_schema
from ledgerlens.verification.label_proximity import (
    RULE_ID,
    check_label_proximity,
    keywords_for,
    label_supported,
)

TAX = keywords_for("cord_receipt")["tax_amount"]
TOTAL = keywords_for("cord_receipt")["total_amount"]


def lines(*rows: str, page: int = 1) -> list[Line]:
    tokens = [
        Token(text=word, bbox=(x * 60.0, y * 20.0, x * 60.0 + 50, y * 20.0 + 10), confidence=0.9)
        for y, row in enumerate(rows)
        for x, word in enumerate(row.split())
    ]
    document = ParsedDocument(
        parser="test", parser_version="0",
        pages=[Page(number=page, width=600, height=600, source="ocr", tokens=tokens)],
    )  # fmt: skip
    return build_lines(document)


def test_the_review_terms_are_configured() -> None:
    assert {"pb1", "ppn", "pajak", "service"} <= set(TAX)
    assert "total" in TOTAL
    assert "subtotal" in keywords_for("cord_receipt")["subtotal"]


def test_a_value_on_its_label_line_is_supported() -> None:
    assert label_supported("10.000", lines("Nasi 2 50.000", "PB1 10.000"), TAX) is True


def test_a_value_on_the_line_below_its_label_is_supported() -> None:
    assert label_supported("10,000", lines("Pajak", "10.000"), TAX) is True


def test_a_value_next_to_another_fields_label_is_not() -> None:
    assert label_supported("50.000", lines("Nasi 2 50.000", "Kembali 1.000"), TAX) is False


def test_a_value_two_lines_away_is_not_supported() -> None:
    assert label_supported("9.000", lines("Tax", "Cash 100.000", "9.000"), TAX) is False


def test_keywords_match_whole_words_only() -> None:
    assert label_supported("5.000", lines("Taxi 5.000"), TAX) is False


def test_known_limitation_total_also_matches_inside_sub_total() -> None:
    """Whole-word matching treats the hyphen as a boundary, so a subtotal line supports total."""
    assert label_supported("5.000", lines("Sub-Total 5.000"), TOTAL) is True


def test_the_value_cannot_be_its_own_label() -> None:
    assert label_supported("1", lines("PB1"), TAX) is False


def test_lines_on_another_page_do_not_count() -> None:
    first = lines("Tax")
    second = lines("9.000", page=2)
    assert label_supported("9.000", first + second, TAX) is False


def test_nothing_to_check_gives_none() -> None:
    assert label_supported(None, lines("Tax 1"), TAX) is None
    assert label_supported("abc", lines("Tax 1"), TAX) is None


def test_a_rule_value_gets_no_result_because_it_would_be_circular() -> None:
    record = FieldRecord(name="tax_amount", value_raw="9.000", value_normalized=None,
                         source="deterministic")  # fmt: skip
    check_label_proximity(record, lines("Tax 9.000"), TAX)
    assert record.signals["label_supported"] is None
    assert record.validation_results == []


def test_an_llm_value_gets_a_result_and_a_feature() -> None:
    record = FieldRecord(name="tax_amount", value_raw="9.000", value_normalized=None,
                         source="llm_pass_a")  # fmt: skip
    check_label_proximity(record, lines("Total 9.000"), TAX)
    assert record.signals["label_supported"] is False
    assert [(r.rule_id, r.passed) for r in record.validation_results] == [(RULE_ID, False)]


def test_the_pipeline_runs_the_check_without_changing_values() -> None:
    page = lines("Total 9.000")
    document = ParsedDocument(
        parser="t", parser_version="0",
        pages=[Page(number=1, width=600, height=600, source="ocr",
                    tokens=list(page[0].tokens))],
    )  # fmt: skip

    class Fixed:
        def extract(self, document: ParsedDocument, schema: object) -> list[FieldRecord]:
            return [FieldRecord(name="total_amount", value_raw="9.000", value_normalized=None,
                                source="llm_pass_a")]  # fmt: skip

    (record,) = process(document, load_schema("cord_receipt"), Fixed())
    assert record.value_raw == "9.000"
    assert record.signals["label_supported"] is True
