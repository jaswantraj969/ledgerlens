import pytest
from evals.runners.make_s5_table import clopper_pearson, exact_interval


def test_clopper_pearson_matches_closed_forms() -> None:
    # All correct: the lower bound is (alpha/2) ** (1/n).
    for n in (3, 9, 14):
        low, high = clopper_pearson(n, n)
        assert low == pytest.approx(0.025 ** (1 / n), abs=1e-9)
        assert high == 1.0
    low, high = clopper_pearson(0, 10)
    assert low == 0.0
    assert high == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-9)


def test_exact_interval_only_below_thirty_accepted() -> None:
    assert exact_interval({"accepted": 14, "achieved_precision": 1.0}) is not None
    assert exact_interval({"accepted": 30, "achieved_precision": 1.0}) is None
    assert exact_interval({"accepted": 0, "achieved_precision": None}) is None
    correct, interval = exact_interval({"accepted": 4, "achieved_precision": 0.75})  # type: ignore[misc]
    assert correct == 3 and interval[0] < 0.75 < interval[1]


def test_a_precision_that_is_not_a_whole_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        exact_interval({"accepted": 3, "achieved_precision": 0.5})
