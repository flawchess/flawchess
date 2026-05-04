"""Unit tests for app.services.eval_confidence.compute_eval_confidence_bucket.

Bucketing rule under test:
  - n < EVAL_CONFIDENCE_MIN_N (20) -> "low"  (unreliable-stats gate)
  - n >= 20 and p_value < 0.05     -> "high"
  - n >= 20 and p_value < 0.10     -> "medium"
  - n >= 20 and p_value >= 0.10    -> "low"

p_value is the two-sided Wald z-test p for H0: mean == baseline_cp, computed as
erfc(|z| / sqrt(2)) where z = (mean - baseline_cp) / se. baseline_cp defaults
to 0 (legacy framing); color-aware callers pass EVAL_BASELINE_CP_WHITE (+28)
for white-color cells and EVAL_BASELINE_CP_BLACK (-20) for black-color cells.

The helper returns a 4-tuple (confidence, p_value, mean, ci_half_width).
ci_half_width = 1.96 * se (95% CI half-width for the bullet chart whisker),
centered on the observed mean — independent of baseline_cp.
"""

import math

import pytest

from app.services.eval_confidence import compute_eval_confidence_bucket
from app.services.opening_insights_constants import (
    EVAL_BASELINE_CP_BLACK,
    EVAL_BASELINE_CP_WHITE,
    EVAL_CONFIDENCE_MIN_N,
)


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


# --- N < MIN gate (20) ----------------------------------------------------


def test_n_below_min_returns_low_even_with_strong_mean() -> None:
    """n=19 with mean=100 and variance=0: SE=0 would give p=0 -> "high", but N gate forces "low"."""
    # n=19 sits exactly one below the gate; the precise value of variance doesn't matter
    # because N < MIN forces "low" first.
    confidence, _p, mean, _ci = compute_eval_confidence_bucket(
        eval_sum=1900.0, eval_sumsq=190000.0, n=19
    )
    assert confidence == "low"
    assert mean == pytest.approx(100.0, abs=1e-9)


def test_n_below_min_distinct_19() -> None:
    """Any n < 20 row is "low", regardless of mean magnitude."""
    eval_sum = 950.0  # mean = 50 cp at n=19
    eval_sumsq = 60000.0  # variance > 0 (sumsq > n * mean^2 = 47500)
    confidence, _p, _mean, _ci = compute_eval_confidence_bucket(eval_sum, eval_sumsq, 19)
    assert confidence == "low"


def test_min_n_constant_is_20() -> None:
    """Belt-and-braces: the gate constant is 20 (verified to lock the value)."""
    assert EVAL_CONFIDENCE_MIN_N == 20


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


# --- Color-specific baseline (engine-asymmetry correction) ---------------


def test_baseline_cp_shifts_test_reference() -> None:
    """A mean equal to the baseline yields p=1.0 (no signal); same mean tested against
    baseline=0 would yield a low p-value."""
    n = 100
    mean_cp = float(EVAL_BASELINE_CP_WHITE)  # +28 cp
    sd_cp = 50.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    # Against baseline=0: z=28/5=5.6 -> p essentially 0 -> "high"
    conf_zero, p_zero, _m, _ci = compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)
    assert conf_zero == "high"
    assert p_zero < 0.001

    # Against the white baseline (+28): z=0 -> p=1.0 -> "low"
    conf_white, p_white, _m2, _ci2 = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n, baseline_cp=float(EVAL_BASELINE_CP_WHITE)
    )
    assert conf_white == "low"
    assert p_white == pytest.approx(1.0, abs=1e-9)


def test_baseline_cp_does_not_shift_displayed_mean_or_ci() -> None:
    """The CI is centered on the observed mean — baseline only affects p-value/bucket."""
    n = 100
    mean_cp = 40.0
    sd_cp = 100.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    _c1, _p1, mean_zero, ci_zero = compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)
    _c2, _p2, mean_white, ci_white = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n, baseline_cp=float(EVAL_BASELINE_CP_WHITE)
    )
    assert mean_zero == pytest.approx(mean_white, abs=1e-9)
    assert ci_zero == pytest.approx(ci_white, abs=1e-9)


def test_baseline_cp_zero_variance_uses_baseline_for_mean_compare() -> None:
    """SE==0 path: p=1.0 iff mean == baseline (not iff mean == 0)."""
    n = 30
    # All games at exactly +28 cp (white baseline) -> variance=0
    mean_cp = float(EVAL_BASELINE_CP_WHITE)
    eval_sum = float(n * mean_cp)
    eval_sumsq = float(n * mean_cp * mean_cp)

    # Against the white baseline: mean == baseline -> p=1.0 -> "low"
    conf, p, _m, ci = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n, baseline_cp=float(EVAL_BASELINE_CP_WHITE)
    )
    assert conf == "low"
    assert p == 1.0
    assert ci == 0.0

    # Against baseline=0: mean != 0 -> p=0.0 -> "high"
    conf2, p2, _m2, _ci2 = compute_eval_confidence_bucket(eval_sum, eval_sumsq, n)
    assert conf2 == "high"
    assert p2 == 0.0


def test_black_baseline_is_negative() -> None:
    """Sanity: a black-color cell with mean at the black baseline should not register signal."""
    n = 100
    mean_cp = float(EVAL_BASELINE_CP_BLACK)  # -20 cp
    sd_cp = 50.0
    variance = sd_cp * sd_cp
    eval_sum = float(n * mean_cp)
    eval_sumsq = variance * (n - 1) + n * mean_cp * mean_cp

    conf, p, _m, _ci = compute_eval_confidence_bucket(
        eval_sum, eval_sumsq, n, baseline_cp=float(EVAL_BASELINE_CP_BLACK)
    )
    assert conf == "low"
    assert p == pytest.approx(1.0, abs=1e-9)
