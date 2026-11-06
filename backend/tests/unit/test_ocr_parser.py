from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import Any

import numpy as np
import pytest
from evals.synthetic.generate import generate_invoice, render_image
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ledgerlens.parsing.model import ParsedDocument
from ledgerlens.parsing.ocr import AutoParser, RapidOcrParser
from ledgerlens.pipeline import process
from ledgerlens.schema import load_schema

BOX = [[10, 20], [60, 20], [60, 40], [10, 40]]


@dataclass
class FakeOutput:
    txts: Any
    boxes: Any
    scores: Any = None
    word_results: Any = None


class FakeEngine:
    def __init__(self, output: FakeOutput | None) -> None:
        self.output = output
        self.calls = 0

    def __call__(self, image: np.ndarray, *, return_word_box: bool) -> FakeOutput | None:
        assert return_word_box
        self.calls += 1
        return self.output


def png(width: int = 100, height: int = 80) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def scanned_pdf(image: bytes) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawImage(ImageReader(BytesIO(image)), 0, 0, width=A4[0], height=A4[1])
    pdf.save()
    return buffer.getvalue()


def test_missing_scores_stay_null() -> None:
    output = FakeOutput(txts=("Total",), boxes=[BOX], scores=None)
    parsed = RapidOcrParser(FakeEngine(output)).parse(png())
    assert parsed.pages[0].tokens[0].confidence is None


def test_engine_scores_are_kept_unchanged() -> None:
    output = FakeOutput(
        txts=("Total 5",), boxes=[BOX], scores=(0.5,), word_results=((("Total", 0.25, BOX),),)
    )
    token = RapidOcrParser(FakeEngine(output)).parse(png()).pages[0].tokens[0]
    assert token.text == "Total"
    assert token.confidence == 0.25


def test_unsplit_line_stays_one_token_with_the_engine_box() -> None:
    output = FakeOutput(txts=("Total 5",), boxes=[BOX], scores=(0.5,), word_results=((),))
    tokens = RapidOcrParser(FakeEngine(output)).parse(png()).pages[0].tokens
    assert [token.text for token in tokens] == ["Total 5"]
    assert tokens[0].bbox == (10, 20, 60, 40)
    assert tokens[0].confidence == 0.5


def test_empty_engine_result_yields_no_tokens() -> None:
    assert RapidOcrParser(FakeEngine(None)).parse(png()).pages[0].tokens == []


def test_image_page_declares_pixel_coordinates() -> None:
    page = RapidOcrParser(FakeEngine(None)).parse(png(100, 80)).pages[0]
    assert (page.width, page.height) == (100, 80)
    assert page.coordinate_system == "image_pixels_top_left"
    assert page.source == "ocr"


def test_auto_parser_uses_native_text_without_calling_ocr() -> None:
    engine = FakeEngine(None)
    parsed = AutoParser(RapidOcrParser(engine)).parse(generate_invoice(1, layout="classic").pdf)
    assert engine.calls == 0
    assert parsed.pages[0].source == "native_pdf"


def test_auto_parser_runs_ocr_on_scanned_pdf_and_scales_to_points() -> None:
    engine = FakeEngine(FakeOutput(txts=("Total",), boxes=[BOX], scores=(0.9,)))
    page = AutoParser(RapidOcrParser(engine)).parse(scanned_pdf(png())).pages[0]
    assert engine.calls == 1
    assert page.source == "ocr"
    assert page.coordinate_system == "pdf_points_top_left"
    assert page.tokens[0].bbox == pytest.approx((3.6, 7.2, 21.6, 14.4))


@pytest.fixture(scope="module")
def real_engine() -> RapidOcrParser:
    pytest.importorskip("rapidocr")
    return RapidOcrParser()


@pytest.fixture(scope="module")
def image_result(real_engine: RapidOcrParser) -> tuple[Any, ParsedDocument]:
    invoice = generate_invoice(3, layout="classic", items=3, tax=True)
    return invoice, real_engine.parse(render_image(invoice.pdf, dpi=150))


def test_real_ocr_reads_an_image_fixture(image_result: tuple[Any, ParsedDocument]) -> None:
    invoice, parsed = image_result
    text = " ".join(token.text for token in parsed.pages[0].tokens)
    assert invoice.truth["invoice_number"] in text


def test_real_ocr_boxes_lie_within_the_page(image_result: tuple[Any, ParsedDocument]) -> None:
    page = image_result[1].pages[0]
    assert page.tokens
    for x0, y0, x1, y1 in (token.bbox for token in page.tokens):
        assert 0 <= x0 < x1 <= page.width
        assert 0 <= y0 < y1 <= page.height


def test_real_ocr_confidence_is_null_or_a_unit_value(
    image_result: tuple[Any, ParsedDocument],
) -> None:
    for token in image_result[1].pages[0].tokens:
        assert token.confidence is None or 0 <= token.confidence <= 1


def test_ocr_evidence_carries_engine_confidence_and_pixel_coordinates(
    image_result: tuple[Any, ParsedDocument],
) -> None:
    invoice, parsed = image_result
    fields = {record.name: record for record in process(parsed, load_schema("default"))}
    total = fields["total_amount"]
    assert Decimal(total.value_normalized or "") == Decimal(invoice.truth["total_amount"])
    assert total.evidence[0].coordinate_system == "image_pixels_top_left"
    assert total.evidence[0].confidence is not None
    assert total.signals["ocr_confidence_available"] is True
