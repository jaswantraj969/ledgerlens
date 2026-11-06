from decimal import Decimal

from evals import normalization


def test_version_is_frozen_at_one_point_zero() -> None:
    assert normalization.NORMALIZATION_VERSION == "1.0"


def test_fingerprint_matches_the_lock() -> None:
    """Failing here means normalisation changed: bump the version and rerun every result."""
    locked = normalization.LOCK_FILE.read_text(encoding="utf-8").split()
    assert locked == [normalization.NORMALIZATION_VERSION, normalization.fingerprint()]


def test_money_compares_numerically() -> None:
    assert normalization.money("Rp. 1.000") == normalization.money("1,000.00") == Decimal(1000)


def test_unparsable_values_are_none_not_guessed() -> None:
    assert normalization.money("-") is None
    assert normalization.money(None) is None
    assert normalization.text("  ") is None
