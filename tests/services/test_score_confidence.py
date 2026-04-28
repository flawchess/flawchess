"""Unit tests for app.services.score_confidence.compute_confidence_bucket.

Bucketing rule under test (replaces the prior Wald CI half-width buckets):
  - n < 10                        -> "low"  (unreliable-stats gate)
  - n >= 10 and p_value < 0.01    -> "high"
  - n >= 10 and p_value < 0.05    -> "medium"
  - n >= 10 and p_value >= 0.05   -> "low"

p_value is the two-sided p-value for H0: score == 0.50 from the Wald z-test;
the formula itself is unchanged. SE == 0 cases produce p_value = 1.0 if
score == 0.5 (all draws) or 0.0 otherwise (all wins / all losses).
"""

import pytest

from app.services.score_confidence import compute_confidence_bucket


# --- N < 10 gate ---------------------------------------------------------


def test_n_below_gate_returns_low_even_with_strong_evidence() -> None:
    # n=9 all wins: p_value would be 0.0 (SE=0) but n<10 forces "low".
    confidence, p_value = compute_confidence_bucket(w=9, d=0, losses=0, n=9)
    assert confidence == "low"
    assert p_value == 0.0


def test_n_below_gate_single_win_is_low() -> None:
    # n=1 single win used to produce "high, p=0.0" under the old rule. Now: "low".
    confidence, _p = compute_confidence_bucket(w=1, d=0, losses=0, n=1)
    assert confidence == "low"


def test_n_below_gate_balanced_is_low() -> None:
    confidence, _p = compute_confidence_bucket(w=2, d=2, losses=2, n=6)
    assert confidence == "low"


def test_n_zero_returns_low_one() -> None:
    """MD-02 guard: n<=0 returns ("low", 1.0) without raising."""
    confidence, p_value = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 1.0


# --- N >= 10 buckets by p-value ------------------------------------------


def test_high_at_strong_evidence() -> None:
    # n=400 with score = 0.40: SE small, |z| large, p << 0.01.
    confidence, p_value = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    assert confidence == "high"
    assert p_value < 0.01


def test_medium_at_moderate_evidence() -> None:
    # n=100, w=35, d=10, losses=55: score=0.40, p ≈ 0.031, lands in [0.01, 0.05) -> medium.
    confidence, p_value = compute_confidence_bucket(w=35, d=10, losses=55, n=100)
    assert confidence == "medium"
    assert 0.01 <= p_value < 0.05


def test_low_at_weak_evidence_with_large_n() -> None:
    # Score very close to 0.50 with n=100: |z| small, p large.
    # n=100, w=48, d=4, losses=48: score=0.50 exactly -> p=1.0 -> low.
    confidence, p_value = compute_confidence_bucket(w=48, d=4, losses=48, n=100)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


def test_low_at_n10_balanced() -> None:
    # n=10 score exactly 0.5: p=1.0, n>=10, falls into "else low".
    confidence, p_value = compute_confidence_bucket(w=2, d=6, losses=2, n=10)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


# --- SE == 0 boundary cases (n >= 10) -----------------------------------


def test_se_zero_all_wins_n10_is_high() -> None:
    """All wins at n=10: score=1.0, p=0.0 -> high (10+ identical outcomes is strong evidence)."""
    confidence, p_value = compute_confidence_bucket(w=10, d=0, losses=0, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_losses_n10_is_high() -> None:
    confidence, p_value = compute_confidence_bucket(w=0, d=0, losses=10, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_draws_n10_is_low() -> None:
    """All draws at n=10: score=0.5, p=1.0 -> low (no evidence of any direction)."""
    confidence, p_value = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert confidence == "low"
    assert p_value == 1.0
