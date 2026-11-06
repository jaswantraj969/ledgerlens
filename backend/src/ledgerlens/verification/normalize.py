"""Value normalisation shared by verification and evaluation labels.

Changing any behaviour here changes what counts as a correct field, so it requires a
NORMALIZATION_VERSION bump and invalidates earlier results.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

NORMALIZATION_VERSION = "1.0.0"

DateOrder = Literal["dmy", "mdy"]

_ISO_CURRENCIES = frozenset(
    [
        "AED",
        "AUD",
        "BRL",
        "CAD",
        "CHF",
        "CNY",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "IDR",
        "INR",
        "JPY",
        "KRW",
        "MXN",
        "MYR",
        "NOK",
        "NZD",
        "PHP",
        "PLN",
        "SAR",
        "SEK",
        "SGD",
        "THB",
        "TRY",
        "TWD",
        "USD",
        "VND",
        "ZAR",
    ]
)
# Only symbols naming one currency. "$" and "¥" name several, so they normalise to None.
_CURRENCY_SYMBOLS = {"€": "EUR", "£": "GBP", "₹": "INR", "₩": "KRW", "RP": "IDR", "RM": "MYR"}

_MONTHS = {
    name: number
    for number, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}

_AMOUNT_CHARS = re.compile(r"[^\d.,\-()]")
_ISO_DATE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_NUMERIC_DATE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$")
_TEXT_DAY_FIRST = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)?[\s\-/.]+([a-z]+)[\s\-/.,]+(\d{2}|\d{4})$")
_TEXT_MONTH_FIRST = re.compile(r"^([a-z]+)[\s\-/.]+(\d{1,2})(?:st|nd|rd|th)?[\s,]+(\d{2}|\d{4})$")


def normalize_text(value: str) -> str:
    """NFKC, casefold, collapse whitespace, trim surrounding punctuation."""
    folded = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(folded.split()).strip(" .,:;-_")


def normalize_identifier(value: str) -> str:
    """Compare identifiers ignoring case, spaces and separators."""
    return re.sub(r"[\s\-_/.#]", "", unicodedata.normalize("NFKC", value)).casefold()


def normalize_amount(value: str) -> Decimal | None:
    """Parse an amount to Decimal, or None if it is not one.

    One separator followed by exactly three digits is read as grouping, so "45.000" is
    45000. This matches Indonesian receipts and is wrong for three-decimal currencies,
    which the default schema does not target.
    """
    text = _AMOUNT_CHARS.sub("", unicodedata.normalize("NFKC", value))
    negative = text.startswith("-") or text.endswith("-") or text.startswith("(")
    digits = text.strip("-()")
    if not digits or not digits[0].isdigit() or not digits[-1].isdigit():
        return None
    if "-" in digits or "(" in digits or ")" in digits:
        return None

    separators = [c for c in digits if c in ".,"]
    if not separators:
        canonical = digits
    elif len(set(separators)) == 2:
        decimal_mark = separators[-1]
        if separators.count(decimal_mark) != 1:
            return None
        group_mark = "," if decimal_mark == "." else "."
        canonical = digits.replace(group_mark, "").replace(decimal_mark, ".")
    elif len(separators) > 1:
        groups = digits.split(separators[0])
        if any(len(group) != 3 for group in groups[1:]):
            return None
        canonical = "".join(groups)
    else:
        whole, fraction = digits.split(separators[0])
        canonical = whole + fraction if len(fraction) == 3 else f"{whole}.{fraction}"

    try:
        amount = Decimal(canonical)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def normalize_currency(value: str) -> str | None:
    """Return an ISO 4217 code, or None for unknown or ambiguous input."""
    text = unicodedata.normalize("NFKC", value).strip().upper()
    if text in _ISO_CURRENCIES:
        return text
    return _CURRENCY_SYMBOLS.get(text)


def _make_date(year: int, month: int, day: int) -> date | None:
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def normalize_date(value: str, order: DateOrder = "dmy") -> date | None:
    """Parse a date, or None if it cannot be parsed. Numeric dates follow `order`."""
    text = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    if match := _ISO_DATE.match(text):
        return _make_date(int(match[1]), int(match[2]), int(match[3]))
    if match := _NUMERIC_DATE.match(text):
        first, second, year = int(match[1]), int(match[2]), int(match[3])
        day, month = (first, second) if order == "dmy" else (second, first)
        return _make_date(year, month, day)
    if (match := _TEXT_DAY_FIRST.match(text)) and match[2] in _MONTHS:
        return _make_date(int(match[3]), _MONTHS[match[2]], int(match[1]))
    if (match := _TEXT_MONTH_FIRST.match(text)) and match[1] in _MONTHS:
        return _make_date(int(match[3]), _MONTHS[match[1]], int(match[2]))
    return None
