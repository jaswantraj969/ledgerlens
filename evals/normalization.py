"""Frozen label normalisation for evaluation (version 1.0).

Defines when a prediction equals ground truth. Any change invalidates reported results, so
the fingerprint of this file and the shared value parsers is locked in normalization.lock,
and a test fails if either changes without a version bump.

Rules:
- money: `normalize_amount` to Decimal, compared numerically, so 1000 equals 1,000.00.
- date: `normalize_date` to an ISO date, day first for numeric dates.
- text: NFKC, casefold, collapsed whitespace, surrounding punctuation trimmed.
- identifier: as text, ignoring spaces and the separators - _ / . #
- currency: ISO 4217 code; ambiguous symbols such as "$" normalise to None.
- A gold value that does not normalise is excluded and counted, never guessed.
- A list-valued gold label uses its last value, the one printed lowest on the document.
"""

import hashlib
from decimal import Decimal
from pathlib import Path

from ledgerlens.verification import normalize as _values
from ledgerlens.verification.normalize import NORMALIZATION_VERSION

_SOURCES = (Path(__file__), Path(_values.__file__))
LOCK_FILE = Path(__file__).with_name("normalization.lock")


def fingerprint() -> str:
    digest = hashlib.sha256()
    for path in _SOURCES:
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def money(value: str | None) -> Decimal | None:
    return None if value is None else _values.normalize_amount(value)


def text(value: str | None) -> str | None:
    return None if value is None else (_values.normalize_text(value) or None)


__all__ = ["LOCK_FILE", "NORMALIZATION_VERSION", "fingerprint", "money", "text"]
