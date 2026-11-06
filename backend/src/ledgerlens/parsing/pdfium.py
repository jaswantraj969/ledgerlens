"""Native-text PDF parser built on pdfium.

Text embedded in a PDF has no recognition step, so token confidence is None. A page with no
embedded text yields no tokens; routing such pages to OCR is the caller's decision.
"""

from importlib.metadata import version

import pypdfium2 as pdfium

from ledgerlens.parsing.model import Page, ParsedDocument, Token


class PdfiumParser:
    name = "pdfium"

    def parse(self, data: bytes) -> ParsedDocument:
        document = pdfium.PdfDocument(data)
        try:
            pages = [self._parse_page(document, index) for index in range(len(document))]
        finally:
            document.close()
        return ParsedDocument(parser=self.name, parser_version=version("pypdfium2"), pages=pages)

    def _parse_page(self, document: pdfium.PdfDocument, index: int) -> Page:
        page = document[index]
        width, height = page.get_size()
        text_page = page.get_textpage()
        tokens = _words(text_page, height)
        text_page.close()
        page.close()
        return Page(
            number=index + 1, width=width, height=height, source="native_pdf", tokens=tokens
        )


def _words(text_page: pdfium.PdfTextPage, page_height: float) -> list[Token]:
    tokens: list[Token] = []
    chars: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        if chars:
            tokens.append(Token(text="".join(chars), bbox=_union(boxes, page_height)))
            chars.clear()
            boxes.clear()

    for index in range(text_page.count_chars()):
        char = text_page.get_text_range(index, 1)
        if not char or char.isspace():
            flush()
            continue
        chars.append(char)
        boxes.append(text_page.get_charbox(index))
    flush()
    return tokens


def _union(
    boxes: list[tuple[float, float, float, float]], page_height: float
) -> tuple[float, float, float, float]:
    """Merge pdfium (left, bottom, right, top) boxes and flip to a top-left origin."""
    left = min(box[0] for box in boxes)
    bottom = min(box[1] for box in boxes)
    right = max(box[2] for box in boxes)
    top = max(box[3] for box in boxes)
    return (left, page_height - top, right, page_height - bottom)
