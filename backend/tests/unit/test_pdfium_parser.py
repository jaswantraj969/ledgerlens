from io import BytesIO

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ledgerlens.parsing.pdfium import PdfiumParser


def make_pdf(*pages: list[tuple[float, float, str]]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for page in pages:
        for x, y, text in page:
            pdf.drawString(x, y, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_extracts_words_in_order() -> None:
    parsed = PdfiumParser().parse(make_pdf([(72, 700, "Invoice INV-001")]))
    assert [token.text for token in parsed.pages[0].tokens] == ["Invoice", "INV-001"]


def test_bbox_uses_top_left_origin() -> None:
    parsed = PdfiumParser().parse(make_pdf([(72, 700, "Near top"), (72, 100, "Near bottom")]))
    page = parsed.pages[0]
    top = next(token for token in page.tokens if token.text == "top")
    bottom = next(token for token in page.tokens if token.text == "bottom")
    assert top.bbox[1] < bottom.bbox[1]
    assert top.bbox[3] == pytest.approx(page.height - 700, abs=12)
    assert 72 <= top.bbox[0] < top.bbox[2] <= page.width


def test_native_text_confidence_is_none_not_invented() -> None:
    parsed = PdfiumParser().parse(make_pdf([(72, 700, "Total 10.00")]))
    assert all(token.confidence is None for token in parsed.pages[0].tokens)


def test_pages_are_numbered_from_one() -> None:
    parsed = PdfiumParser().parse(make_pdf([(72, 700, "first")], [(72, 700, "second")]))
    assert [page.number for page in parsed.pages] == [1, 2]
    assert parsed.pages[1].tokens[0].text == "second"


def test_page_without_text_yields_no_tokens() -> None:
    parsed = PdfiumParser().parse(make_pdf([]))
    assert parsed.pages[0].tokens == []
    assert parsed.pages[0].source == "native_pdf"
