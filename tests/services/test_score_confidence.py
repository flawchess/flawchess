"""Unit tests for app.services.score_confidence.compute_confidence_bucket.

Bucketing rule under test:
  - n < 10                        -> "low"  (unreliable-stats gate)
  - n >= 10 and p_value < 0.05    -> "high"
  - n >= 10 and p_value < 0.10    -> "medium"
  - n >= 10 and p_value >= 0.10   -> "low"

p_value is the one-sided p for the directional Wald z-test on H0: score == 0.50,
computed as 0.5 * erfc(|z| / sqrt(2)). SE == 0 cases produce p_value = 0.5 if
score == 0.5 (all draws — the one-sided null) or 0.0 otherwise (all wins / all
losses — extreme observation in the directional alternative).

The helper returns a 3-tuple (confidence, p_value, se) — SE is exposed so the
opening_insights ranking layer can build the Wald 95% CI bound for within-bucket
tiebreak (quick task 260428-tgg).
"""

import math

import pytest

from app.services.score_confidence import compute_confidence_bucket


# --- N < 10 gate ---------------------------------------------------------


def test_n_below_gate_returns_low_even_with_strong_evidence() -> None:
    # n=9 all wins: p_value would be 0.0 (SE=0) but n<10 forces "low".
    confidence, p_value, _se = compute_confidence_bucket(w=9, d=0, losses=0, n=9)
    assert confidence == "low"
    assert p_value == 0.0


def test_n_below_gate_single_win_is_low() -> None:
    # n=1 single win used to produce "high, p=0.0" under the old rule. Now: "low".
    confidence, _p, _se = compute_confidence_bucket(w=1, d=0, losses=0, n=1)
    assert confidence == "low"


def test_n_below_gate_balanced_is_low() -> None:
    confidence, _p, _se = compute_confidence_bucket(w=2, d=2, losses=2, n=6)
    assert confidence == "low"


def test_n_zero_returns_low_half() -> None:
    """MD-02 guard: n<=0 returns ("low", 0.5, 0.0) without raising — 0.5 is the
    one-sided null and SE is zero with no sample."""
    confidence, p_value, se = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 0.5
    assert se == 0.0


# --- N >= 10 buckets by p-value ------------------------------------------


def test_high_at_strong_evidence() -> None:
    # n=400 with score = 0.30: SE small, |z| large, one-sided p << 0.05.
    confidence, p_value, _se = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    assert confidence == "high"
    assert p_value < 0.05


def test_medium_at_moderate_evidence() -> None:
    # n=50, w=20, d=0, losses=30: score=0.40, |z|≈1.443, one-sided p ≈ 0.0745,
    # lands in [0.05, 0.10) -> medium.
    confidence, p_value, _se = compute_confidence_bucket(w=20, d=0, losses=30, n=50)
    assert confidence == "medium"
    assert 0.05 <= p_value < 0.10


def test_low_at_weak_evidence_with_large_n() -> None:
    # Score exactly 0.50 with n=100: |z| = 0, one-sided p = 0.5 -> low.
    confidence, p_value, _se = compute_confidence_bucket(w=48, d=4, losses=48, n=100)
    assert confidence == "low"
    assert p_value == pytest.approx(0.5, abs=1e-9)


def test_low_at_n10_balanced() -> None:
    # n=10 score exactly 0.5: one-sided p = 0.5, n>=10, falls into "else low".
    confidence, p_value, _se = compute_confidence_bucket(w=2, d=6, losses=2, n=10)
    assert confidence == "low"
    assert p_value == pytest.approx(0.5, abs=1e-9)


# --- SE == 0 boundary cases (n >= 10) -----------------------------------


def test_se_zero_all_wins_n10_is_high() -> None:
    """All wins at n=10: score=1.0, p=0.0 -> high (10+ identical outcomes is strong evidence)."""
    confidence, p_value, _se = compute_confidence_bucket(w=10, d=0, losses=0, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_losses_n10_is_high() -> None:
    confidence, p_value, _se = compute_confidence_bucket(w=0, d=0, losses=10, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_draws_n10_is_low() -> None:
    """All draws at n=10: score=0.5, one-sided p=0.5 -> low (no evidence of any direction)."""
    confidence, p_value, _se = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert confidence == "low"
    assert p_value == 0.5


# --- SE component (third tuple element) ----------------------------------


def test_se_returned_alongside_confidence_and_p() -> None:
    """SE matches the manual sqrt(((W + 0.25*D)/N - score**2) / N) closed form.

    For w=80, d=80, losses=240, n=400: score = (80 + 40)/400 = 0.30.
    variance = (80 + 20)/400 - 0.09 = 0.25 - 0.09 = 0.16.
    se = sqrt(0.16 / 400) = sqrt(0.0004) = 0.02.
    """
    _confidence, _p, se = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    n = 400
    score = (80 + 0.5 * 80) / n
    variance = (80 + 0.25 * 80) / n - score * score
    expected_se = math.sqrt(max(variance, 0.0) / n)
    assert se == pytest.approx(expected_se, abs=1e-9)


def test_se_zero_for_all_draws() -> None:
    """All draws: score=0.5 exactly, variance = (0 + 0.25*N)/N - 0.25 = 0, SE = 0."""
    _confidence, _p, se = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert se == 0.0


def test_se_zero_for_all_wins_n10() -> None:
    """All wins: variance is clamped to 0 (math: W/N - (W/N)^2 = 1 - 1 = 0), SE = 0."""
    _confidence, _p, se = compute_confidence_bucket(w=10, d=0, losses=0, n=10)
    assert se == 0.0


def test_se_zero_for_all_losses_n10() -> None:
    """All losses: score=0, variance = 0/N - 0 = 0, SE = 0."""
    _confidence, _p, se = compute_confidence_bucket(w=0, d=0, losses=10, n=10)
    assert se == 0.0


def test_se_positive_for_mixed_outcomes() -> None:
    """SE strictly positive whenever the row contains a mix of W/D/L outcomes."""
    _confidence, _p, se = compute_confidence_bucket(w=20, d=0, losses=30, n=50)
    assert se > 0.0
