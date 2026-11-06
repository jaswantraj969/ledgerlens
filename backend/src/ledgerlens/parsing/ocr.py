"""OCR parser built on RapidOCR, and a parser that chooses per page.

Boxes, text and confidences come from the engine. A line the engine does not split stays a
single line-level token: dividing its box into words would invent coordinates. A score the
engine does not give stays None.
"""

from collections.abc import Sequence
from importlib.metadata import version
from io import BytesIO
from typing import Any, Protocol, cast

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

from ledgerlens.parsing.model import (
    COORDINATE_SYSTEM,
    IMAGE_COORDINATE_SYSTEM,
    Page,
    ParsedDocument,
    Token,
)
from ledgerlens.parsing.pdfium import PdfiumParser

PDF_RENDER_DPI = 200
PDF_POINTS_PER_INCH = 72
_PDF_MAGIC = b"%PDF-"


class OcrEngine(Protocol):
    """The part of RapidOCR used here, so tests can substitute a fake."""

    def __call__(self, image: np.ndarray, *, return_word_box: bool) -> Any: ...


def _default_engine() -> OcrEngine:
    from rapidocr import RapidOCR

    return cast(OcrEngine, RapidOCR(params={"Global.log_level": "error"}))


def _quad_bbox(quad: Sequence[Sequence[float]], scale: float) -> tuple[float, float, float, float]:
    xs = [float(point[0]) * scale for point in quad]
    ys = [float(point[1]) * scale for point in quad]
    return (min(xs), min(ys), max(xs), max(ys))


def _score(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _tokens(output: Any, scale: float) -> list[Token]:
    if output is None or output.txts is None or output.boxes is None:
        return []
    words = getattr(output, "word_results", None) or ()
    scores = output.scores if output.scores is not None else ()
    tokens: list[Token] = []
    for index, (text, box) in enumerate(zip(output.txts, output.boxes, strict=True)):
        line_words = words[index] if index < len(words) else ()
        if line_words:
            tokens.extend(
                Token(text=word, bbox=_quad_bbox(quad, scale), confidence=_score(score))
                for word, score, quad in line_words
                if word.strip()
            )
        elif text.strip():
            score = scores[index] if index < len(scores) else None
            tokens.append(Token(text=text, bbox=_quad_bbox(box, scale), confidence=_score(score)))
    return tokens


class RapidOcrParser:
    name = "rapidocr"

    def __init__(self, engine: OcrEngine | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> OcrEngine:
        if self._engine is None:
            self._engine = _default_engine()
        return self._engine

    def parse(self, data: bytes) -> ParsedDocument:
        if data.startswith(_PDF_MAGIC):
            document = pdfium.PdfDocument(data)
            try:
                pages = [self.ocr_pdf_page(document, index) for index in range(len(document))]
            finally:
                document.close()
        else:
            pages = [self._ocr_image(data)]
        return ParsedDocument(parser=self.name, parser_version=version("rapidocr"), pages=pages)

    def _ocr_image(self, data: bytes) -> Page:
        image = Image.open(BytesIO(data)).convert("RGB")
        tokens = _tokens(self.engine(np.array(image), return_word_box=True), 1.0)
        return Page(
            number=1,
            width=float(image.width),
            height=float(image.height),
            coordinate_system=IMAGE_COORDINATE_SYSTEM,
            source="ocr",
            tokens=tokens,
        )

    def ocr_pdf_page(self, document: pdfium.PdfDocument, index: int) -> Page:
        """Render one page, then report boxes in PDF points so the page has one system."""
        page = document[index]
        width, height = page.get_size()
        scale = PDF_RENDER_DPI / PDF_POINTS_PER_INCH
        image = page.render(scale=scale).to_pil().convert("RGB")
        page.close()
        tokens = _tokens(self.engine(np.array(image), return_word_box=True), 1 / scale)
        return Page(
            number=index + 1,
            width=width,
            height=height,
            coordinate_system=COORDINATE_SYSTEM,
            source="ocr",
            tokens=tokens,
        )


class AutoParser:
    """Native text where a PDF page has it, OCR for scanned pages and images."""

    name = "auto"

    def __init__(self, ocr: RapidOcrParser | None = None) -> None:
        self._native = PdfiumParser()
        self._ocr = ocr or RapidOcrParser()

    def parse(self, data: bytes) -> ParsedDocument:
        if not data.startswith(_PDF_MAGIC):
            return self._ocr.parse(data)
        parsed = self._native.parse(data)
        document = pdfium.PdfDocument(data)
        try:
            pages = [
                page if page.tokens else self._ocr.ocr_pdf_page(document, page.number - 1)
                for page in parsed.pages
            ]
        finally:
            document.close()
        return parsed.model_copy(update={"parser": self.name, "pages": pages})
