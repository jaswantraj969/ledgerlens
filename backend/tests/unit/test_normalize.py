from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ledgerlens.verification.normalize import (
    normalize_amount,
    normalize_currency,
    normalize_date,
    normalize_identifier,
    normalize_text,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,234.56", "1234.56"),
        ("1.234,56", "1234.56"),
        ("Rp 45.000", "45000"),
        ("45,000", "45000"),
        ("1.250.000", "1250000"),
        ("12.50", "12.50"),
        ("12,5", "12.5"),
        ("$ 7.00", "7.00"),
        ("(15.00)", "-15.00"),
        ("-3.20", "-3.20"),
        ("3.20-", "-3.20"),
    ],
)
def test_amount_parsing(raw: str, expected: str) -> None:
    assert normalize_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["", "abc", "1.2.3", "1,23,45", "1.234,567,8", "12-34"])
def test_amount_rejects_non_amounts(raw: str) -> None:
    assert normalize_amount(raw) is None


def test_amount_returns_decimal_not_float() -> None:
    assert isinstance(normalize_amount("0.10"), Decimal)


@given(st.decimals(min_value=0, max_value=10**9, places=2, allow_nan=False))
def test_amount_round_trips_comma_grouped_format(value: Decimal) -> None:
    assert normalize_amount(f"{value:,.2f}") == value


@given(st.decimals(min_value=0, max_value=10**9, places=2, allow_nan=False))
def test_amount_round_trips_european_format(value: Decimal) -> None:
    european = f"{value:,.2f}".translate(str.maketrans(",.", ".,"))
    assert normalize_amount(european) == value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("usd", "USD"), (" eur ", "EUR"), ("€", "EUR"), ("Rp", "IDR"), ("£", "GBP")],
)
def test_currency_known(raw: str, expected: str) -> None:
    assert normalize_currency(raw) == expected


@pytest.mark.parametrize("raw", ["$", "¥", "XXX", "", "dollars"])
def test_currency_unknown_or_ambiguous_is_none(raw: str) -> None:
    assert normalize_currency(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-03-05", date(2024, 3, 5)),
        ("05/03/2024", date(2024, 3, 5)),
        ("05-03-24", date(2024, 3, 5)),
        ("5 March 2024", date(2024, 3, 5)),
        ("5th Mar, 2024", date(2024, 3, 5)),
        ("March 5, 2024", date(2024, 3, 5)),
    ],
)
def test_date_parsing(raw: str, expected: date) -> None:
    assert normalize_date(raw) == expected


def test_date_order_changes_numeric_reading() -> None:
    assert normalize_date("05/03/2024", order="mdy") == date(2024, 5, 3)


@pytest.mark.parametrize("raw", ["", "32/01/2024", "2024-13-01", "not a date", "5 Foo 2024"])
def test_date_rejects_invalid(raw: str) -> None:
    assert normalize_date(raw) is None


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)))
def test_date_round_trips_iso(value: date) -> None:
    assert normalize_date(value.isoformat()) == value


def test_text_folds_case_space_and_edges() -> None:
    assert normalize_text("  ACME   Corp. ") == "acme corp"


def test_identifier_ignores_separators() -> None:
    assert normalize_identifier("INV-2024 / 001") == normalize_identifier("inv2024001")


@given(st.text(max_size=40))
def test_text_normalisation_is_idempotent(value: str) -> None:
    once = normalize_text(value)
    assert normalize_text(once) == once
