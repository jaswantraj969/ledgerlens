"""Reading-order lines built from positioned tokens."""

from dataclasses import dataclass
from statistics import median

from ledgerlens.parsing.model import ParsedDocument, Token


@dataclass(frozen=True)
class Line:
    page: int
    tokens: tuple[Token, ...]
    coordinate_system: str

    @property
    def text(self) -> str:
        return " ".join(token.text for token in self.tokens)

    def tokens_between(self, start: int, stop: int | None = None) -> tuple[Token, ...]:
        """Tokens starting in the character range [start, stop) of `text`."""
        selected: list[Token] = []
        position = 0
        for token in self.tokens:
            if position >= start and (stop is None or position < stop):
                selected.append(token)
            position += len(token.text) + 1
        return tuple(selected)


def build_lines(document: ParsedDocument) -> list[Line]:
    lines: list[Line] = []
    for page in document.pages:
        if not page.tokens:
            continue
        tolerance = 0.5 * median(token.bbox[3] - token.bbox[1] for token in page.tokens)
        ordered = sorted(page.tokens, key=lambda token: (token.bbox[1] + token.bbox[3]) / 2)
        group: list[Token] = []
        center = 0.0
        for token in ordered:
            token_center = (token.bbox[1] + token.bbox[3]) / 2
            if group and token_center - center > tolerance:
                lines.append(_line(page.number, group, page.coordinate_system))
                group = []
            if not group:
                center = token_center
            group.append(token)
        lines.append(_line(page.number, group, page.coordinate_system))
    return lines


def _line(page: int, tokens: list[Token], coordinate_system: str) -> Line:
    ordered = tuple(sorted(tokens, key=lambda token: token.bbox[0]))
    return Line(page=page, tokens=ordered, coordinate_system=coordinate_system)
