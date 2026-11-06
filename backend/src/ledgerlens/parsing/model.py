"""Parsed document model with provenance.

Bounding boxes are [x0, y0, x1, y1] in PDF points with a top-left origin, so y grows downward.
`confidence` is whatever the engine reported, or None when it reports nothing. It is never
estimated here.
"""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

COORDINATE_SYSTEM = "pdf_points_top_left"

ParserSource = Literal["native_pdf", "ocr"]


class Token(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    bbox: tuple[float, float, float, float]
    confidence: float | None = None


class Page(BaseModel):
    number: int
    width: float
    height: float
    coordinate_system: str = COORDINATE_SYSTEM
    source: ParserSource
    tokens: list[Token]


class ParsedDocument(BaseModel):
    parser: str
    parser_version: str
    pages: list[Page]


class Parser(Protocol):
    """Turns document bytes into pages of tokens with provenance."""

    def parse(self, data: bytes) -> ParsedDocument: ...
