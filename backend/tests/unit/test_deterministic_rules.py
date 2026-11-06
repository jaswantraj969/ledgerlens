from ledgerlens.extraction.deterministic import DeterministicExtractor
from ledgerlens.fields import FieldRecord
from ledgerlens.parsing.model import Page, ParsedDocument, Token
from ledgerlens.schema import load_schema


def document(*rows: list[str]) -> ParsedDocument:
    tokens = []
    for row_index, words in enumerate(rows):
        for word_index, word in enumerate(words):
            x = 10.0 + word_index * 60
            y = 10.0 + row_index * 20
            tokens.append(Token(text=word, bbox=(x, y, x + 50, y + 10), confidence=0.9))
    page = Page(number=1, width=400, height=800, source="ocr", tokens=tokens)
    return ParsedDocument(parser="test", parser_version="0", pages=[page])


def extract(*rows: list[str]) -> dict[str, FieldRecord]:
    records = DeterministicExtractor().extract(document(*rows), load_schema("cord_receipt"))
    return {record.name: record for record in records}


def test_value_glued_to_its_label_is_read() -> None:
    assert extract(["Subtotal:28,000"])["subtotal"].value_raw == "28,000"


def test_glued_value_keeps_the_token_box() -> None:
    evidence = extract(["Subtotal:28,000"])["subtotal"].evidence[0]
    assert evidence.bbox == (10.0, 10.0, 60.0, 20.0)
    assert evidence.confidence == 0.9


def test_trailing_punctuation_is_stripped_from_amounts() -> None:
    assert extract(["PB1:", "0."])["tax_amount"].value_raw == "0"


def test_value_on_the_next_line_is_read() -> None:
    assert extract(["TOTAL"], ["20,000"])["total_amount"].value_raw == "20,000"


def test_next_line_with_text_is_not_taken_as_the_value() -> None:
    assert extract(["TOTAL"], ["CASH", "20,000"])["total_amount"].value_raw is None


def test_joined_label_is_recognised() -> None:
    assert extract(["GRANDTOTAL", "20.000"])["total_amount"].value_raw == "20.000"


def test_count_lines_are_not_totals() -> None:
    fields = extract(["TOTAL", "20,000"], ["TOTAL", "ITEM", "3"])
    assert fields["total_amount"].value_raw == "20,000"


def test_subtotal_is_never_read_as_total() -> None:
    fields = extract(["Subtotal", "10,000"])
    assert fields["subtotal"].value_raw == "10,000"
    assert fields["total_amount"].value_raw is None


def test_headerless_row_with_leading_quantity_and_unit_price() -> None:
    fields = extract(["1X", "Black", "Tea", "@28,000", "28,000"], ["Total", "28,000"])
    assert fields["line_items[0].quantity"].value_raw == "1"
    assert fields["line_items[0].description"].value_raw == "Black Tea"
    assert fields["line_items[0].unit_price"].value_raw == "28,000"
    assert fields["line_items[0].amount"].value_raw == "28,000"


def test_headerless_row_with_quantity_before_the_amount() -> None:
    fields = extract(["Nasi", "Putih", "2", "10.000"], ["Total", "10.000"])
    assert fields["line_items[0].quantity"].value_raw == "2"
    assert fields["line_items[0].description"].value_raw == "Nasi Putih"


def test_rows_stop_at_the_first_summary_line() -> None:
    fields = extract(["Tea", "5,000"], ["Subtotal", "5,000"], ["Rice", "9,000"])
    assert "line_items[0].amount" in fields
    assert "line_items[1].amount" not in fields


def test_lines_without_a_name_or_price_are_not_rows() -> None:
    fields = extract(["12", "34"], ["Table", "7"], ["Total", "1,000"])
    assert not any(name.startswith("line_items") for name in fields)
