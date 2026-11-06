"""Reading-order lines built from positioned tokens."""

from dataclasses import dataclass
from statistics import median

from ledgerlens.parsing.model import ParsedDocument, Token


@dataclass(frozen=True)
class Line:
    page: int
    tokens: tuple[Token, ...]

    @property
    def text(self) -> str:
        return " ".join(token.text for token in self.tokens)

    def tokens_after(self, char_offset: int) -> tuple[Token, ...]:
        """Tokens starting at or after a character offset in `text`."""
        position = 0
        for index, token in enumerate(self.tokens):
            if position >= char_offset:
                return self.tokens[index:]
            position += len(token.text) + 1
        return ()


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
                lines.append(_line(page.number, group))
                group = []
            if not group:
                center = token_center
            group.append(token)
        lines.append(_line(page.number, group))
    return lines


def _line(page: int, tokens: list[Token]) -> Line:
    return Line(page=page, tokens=tuple(sorted(tokens, key=lambda token: token.bbox[0])))
