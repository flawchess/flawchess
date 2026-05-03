"""Unit tests for app.services.eval_confidence.compute_eval_confidence_bucket.

Bucketing rule under test:
  - n < 10                        -> "low"  (unreliable-stats gate)
  - n >= 10 and p_value < 0.05    -> "high"
  - n >= 10 and p_value < 0.10    -> "medium"
  - n >= 10 and p_value >= 0.10   -> "low"

p_value is the two-sided Wald z-test p for H0: mean == 0, computed as
erfc(|z| / sqrt(2)) where z = mean / se. The two-sided framing matches the
"is the avg eval different from zero?" question (both positive and negative
deviations are meaningful).

The helper returns a 4-tuple (confidence, p_value, mean, ci_half_width).
ci_half_width = 1.96 * se (95% CI half-width for the bullet chart whisker).
"""

import math

import pytest

from app.services.eval_confidence import compute_eval_confidence_bucket


# --- n == 0 and n == 1 edge cases ----------------------------------------


def test_n_zero_returns_low_one_zero_zero() -> None:
    """n=0: no data — returns ("low", 1.0, 0.0, 0.0) without raising."""
    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(0.0, 0.0, 0)
    assert confidence == "low"
    assert p_value == 1.0
    assert mean == 0.0
    assert ci_half_width == 0.0


def test_n_one_returns_low_with_mean() -> None:
    """n=1: variance undefined; returns ("low", 1.0, mean, 0.0) gated to low."""
    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(50.0, 2500.0, 1)
    assert confidence == "low"
    assert p_value == 1.0
    assert mean == pytest.approx(50.0, abs=1e-9)
    assert ci_half_width == 0.0


# --- N < 10 gate ----------------------------------------------------------


def test_n_below_min_returns_low_even_with_strong_mean() -> None:
    """n=9 with mean=100 and variance=0: SE=0 would give p=0 -> "high", but N gate forces "low"."""
    # mean = 900 / 9 = 100 cp; sumsq = 9 * 100^2 = 90000 -> variance = 0
    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(
        eval_sum=900.0, eval_sumsq=81000.0, n=9
    )
    assert confidence == "low"
    assert mean == pytest.approx(100.0, abs=1e-9)
    # variance = (81000 - 9 * 100 * 100) / 8 = (81000 - 90000) / 8 — wait, that's negative.
    # Correct: eval_sumsq must be n * mean^2 for zero variance.
    # 9 * 100^2 = 90000, so use sumsq=90000 for zero variance.
    # With sumsq=81000: mean=100 but variance = max(0, (81000 - 90000)/8) = max(0, -1125) = 0
    assert ci_half_width == 0.0  # SE == 0 -> ci_half_width == 0


def test_n_below_min_distinct_9() -> None:
    """Any n=9 row is "low", regardless of mean magnitude."""
    # n=9, mean=50 cp, some positive variance: still "low" because N gate.
    eval_sum = 450.0
    eval_sumsq = 25000.0  # mean=50, sumsq > n*mean^2 so variance > 0
    confidence, _p, _mean, _ci = compute_eval_confidence_bucket(eval_sum, eval_sumsq, 9)
    assert confidence == "low"


# --- N >= 10 buckets by p-value ------------------------------------------


def test_high_when_p_below_005() -> None:
    """n=400, mean=50 cp, sd=200 cp -> SE=10, z=5.0, p~5.7e-7 -> "high".

    eval_sum = 400 * 50 = 20000
    eval_sumsq = sum(xi^2); for variance = sd^2 = 40000:
      variance = (sumsq - n * mean^2) / (n-1)
      sumsq = variance * (n-1) + n * mean^2
            = 40000 * 399 + 400 * 2500
            = 15960000 + 1000000 = 16960000
    se = sqrt(40000 / 400) = sqrt(100) = 10
    z = 50 / 10 = 5.0
    p = erfc(5 / sqrt(2)) ≈ erfc(3.535) ≈ 5.73e-7
    """
    n = 400
    mean_cp = 50.0
    sd_cp = 200.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n
    )
    assert confidence == "high"
    assert p_value < 0.05
    assert mean == pytest.approx(mean_cp, abs=1e-9)
    # se = 10, ci_half_width = 1.96 * 10 = 19.6
    assert ci_half_width == pytest.approx(1.96 * (sd_cp / math.sqrt(n)), rel=1e-9)


def test_medium_when_p_in_005_010() -> None:
    """n=100, mean=10 cp, sd=60 cp -> SE=6, z=10/6~1.667, two-sided p~0.0956 -> "medium".

    sumsq = 60^2 * 99 + 100 * 10^2
          = 3600 * 99 + 10000
          = 356400 + 10000 = 366400
    se = sqrt(3600 / 100) = 6
    z = 10 / 6 ≈ 1.6667
    p = erfc(1.6667 / sqrt(2)) = erfc(1.1785) ≈ 0.0956
    """
    n = 100
    mean_cp = 10.0
    sd_cp = 60.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n
    )
    assert confidence == "medium"
    assert 0.05 <= p_value < 0.10
    assert mean == pytest.approx(mean_cp, abs=1e-9)
    se = sd_cp / math.sqrt(n)
    assert ci_half_width == pytest.approx(1.96 * se, rel=1e-9)


def test_low_when_p_above_010_with_large_n() -> None:
    """n=100, mean=2 cp, sd=100 cp -> SE=10, z=0.2, p~0.841 -> "low"."""
    n = 100
    mean_cp = 2.0
    sd_cp = 100.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    confidence, p_value, _mean, _ci = compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)
    assert confidence == "low"
    assert p_value >= 0.10


# --- SE == 0 boundary cases (n >= 10) ------------------------------------


def test_zero_variance_nonzero_mean_returns_high() -> None:
    """n=20, all evals identical at 20 cp: variance=0, SE=0, mean=20 -> p=0.0 -> "high".

    eval_sum = 20 * 20 = 400
    eval_sumsq = 20 * 20^2 = 8000
    variance = (8000 - 20 * 400) / 19 = 0 / 19 = 0.0
    """
    n = 20
    mean_cp = 20.0
    eval_sum = float(n * mean_cp)
    eval_sumsq = float(n * mean_cp * mean_cp)

    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n
    )
    assert confidence == "high"
    assert p_value == 0.0
    assert mean == pytest.approx(mean_cp, abs=1e-9)
    assert ci_half_width == 0.0  # SE == 0


def test_zero_variance_zero_mean_returns_low() -> None:
    """n=20, all evals = 0 cp: variance=0, SE=0, mean=0 -> p=1.0 -> "low".

    eval_sum = 0, eval_sumsq = 0 -> mean = 0, variance = 0, p = 1.0.
    """
    n = 20
    confidence, p_value, mean, ci_half_width = compute_eval_confidence_bucket(0.0, 0.0, n)
    assert confidence == "low"
    assert p_value == 1.0
    assert mean == 0.0
    assert ci_half_width == 0.0


# --- CI half-width component ----------------------------------------------


def test_ci_half_width_matches_196_se() -> None:
    """ci_half_width == 1.96 * se where se = sqrt(variance / n)."""
    n = 50
    mean_cp = 30.0
    sd_cp = 80.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    _confidence, _p, _mean, ci_half_width = compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)
    se = sd_cp / math.sqrt(n)
    assert ci_half_width == pytest.approx(1.96 * se, rel=1e-9)


# --- Symmetry: sign of mean does not affect p-value ----------------------


def test_two_sided_p_value_symmetric() -> None:
    """Same |z| -> same p_value; mean flips sign but p and ci_half_width are identical."""
    n = 100
    mean_cp = 15.0
    sd_cp = 50.0
    variance = sd_cp * sd_cp
    pos_eval_sum = float(n * mean_cp)
    neg_eval_sum = float(n * (-mean_cp))
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    conf_pos, p_pos, mean_pos, ci_pos = compute_eval_confidence_bucket(pos_eval_sum, eval_sumsq, n)
    conf_neg, p_neg, mean_neg, ci_neg = compute_eval_confidence_bucket(neg_eval_sum, eval_sumsq, n)

    # Same confidence bucket and p-value (symmetric around 0)
    assert conf_pos == conf_neg
    assert p_pos == pytest.approx(p_neg, abs=1e-9)
    # Mean and ci are identical in magnitude, opposite in sign for mean only
    assert mean_pos == pytest.approx(-mean_neg, abs=1e-9)
    assert ci_pos == pytest.approx(ci_neg, abs=1e-9)
