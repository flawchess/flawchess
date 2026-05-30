"""Unit tests for the Cohen's d collapse-verdict helpers (no DB).

These pin the deterministic replacement for the skill's hand-computed Cohen's d.
The §2.1 marginal aggregates (transcribed from the live benchmark DB) are used as a
realistic fixture and assert the corrected ELO pair (800 vs 1600), catching the prior
report's pair-selection error.
"""

from __future__ import annotations

import math

import pytest

from scripts.benchmarks import stats


def test_cohens_d_zero_when_means_equal() -> None:
    a = stats.LevelStat("a", 50, 10.0, 4.0)
    b = stats.LevelStat("b", 50, 10.0, 9.0)
    assert stats.cohens_d(a, b) == 0.0


def test_cohens_d_known_value() -> None:
    # Equal n and equal variance: pooled_sd == sqrt(var); d == diff / sqrt(var).
    a = stats.LevelStat("a", 100, 12.0, 16.0)
    b = stats.LevelStat("b", 100, 8.0, 16.0)
    assert stats.cohens_d(a, b) == pytest.approx(4.0 / 4.0)  # 1.0


def test_cohens_d_sign_follows_pair_order() -> None:
    a = stats.LevelStat("a", 30, 5.0, 10.0)
    b = stats.LevelStat("b", 30, 9.0, 10.0)
    assert stats.cohens_d(a, b) < 0
    assert stats.cohens_d(b, a) == -stats.cohens_d(a, b)


def test_max_abs_d_picks_largest_pair() -> None:
    levels = [
        stats.LevelStat("lo", 100, 0.0, 1.0),
        stats.LevelStat("mid", 100, 1.0, 1.0),
        stats.LevelStat("hi", 100, 3.0, 1.0),
    ]
    result = stats.max_abs_d(levels)
    assert result.pair == ("lo", "hi")
    assert result.max_abs_d == pytest.approx(3.0 / math.sqrt(1.0))


def test_max_abs_d_skips_levels_below_floor() -> None:
    levels = [
        stats.LevelStat("a", 100, 0.0, 1.0),
        stats.LevelStat("tiny", 5, 100.0, 1.0),  # n < 10, ignored despite huge mean
        stats.LevelStat("b", 100, 1.0, 1.0),
    ]
    result = stats.max_abs_d(levels)
    assert result.pair == ("a", "b")


def test_max_abs_d_raises_without_two_eligible_levels() -> None:
    with pytest.raises(ValueError):
        stats.max_abs_d([stats.LevelStat("only", 100, 0.0, 1.0)])


def test_mg_eval_elo_marginal_corrected_pair() -> None:
    """§2.1 ELO marginal (live DB values): max |d| is 800 vs 1600, not 800 vs 1200.

    The prior report labeled this pair (800, 1200); the deterministic max is (800, 1600).
    """
    elo = [
        stats.LevelStat("800", 1541, -0.83, 7722.5697442898318),
        stats.LevelStat("1200", 2140, 5.65, 4806.5778868513880),
        stats.LevelStat("1600", 2290, 5.02, 2455.6106226552682),
        stats.LevelStat("2000", 1988, 4.37, 1239.1997645421890),
        stats.LevelStat("2400", 1150, 1.97, 756.2127111630688),
    ]
    result = stats.max_abs_d(elo)
    assert result.pair == ("800", "1600")
    assert round(result.max_abs_d, 2) == 0.09


def test_mg_eval_tc_marginal_pair() -> None:
    """§2.1 TC marginal (live DB values): max |d| = 0.18 between bullet and rapid."""
    tc = [
        stats.LevelStat("bullet", 2674, -2.54, 5141.6672772370016),
        stats.LevelStat("blitz", 2665, 2.91, 2037.7950501037210),
        stats.LevelStat("rapid", 2628, 8.45, 2532.0285822219684),
        stats.LevelStat("classical", 1142, 8.83, 4518.0069800681290),
    ]
    result = stats.max_abs_d(tc)
    assert result.pair == ("bullet", "rapid")
    assert round(result.max_abs_d, 2) == 0.18
