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


def test_n_zero_returns_low_half() -> None:
    """MD-02 guard: n<=0 returns ("low", 0.5) without raising — 0.5 is the
    one-sided null."""
    confidence, p_value = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 0.5


# --- N >= 10 buckets by p-value ------------------------------------------


def test_high_at_strong_evidence() -> None:
    # n=400 with score = 0.30: SE small, |z| large, one-sided p << 0.05.
    confidence, p_value = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    assert confidence == "high"
    assert p_value < 0.05


def test_medium_at_moderate_evidence() -> None:
    # n=50, w=20, d=0, losses=30: score=0.40, |z|≈1.443, one-sided p ≈ 0.0745,
    # lands in [0.05, 0.10) -> medium.
    confidence, p_value = compute_confidence_bucket(w=20, d=0, losses=30, n=50)
    assert confidence == "medium"
    assert 0.05 <= p_value < 0.10


def test_low_at_weak_evidence_with_large_n() -> None:
    # Score exactly 0.50 with n=100: |z| = 0, one-sided p = 0.5 -> low.
    confidence, p_value = compute_confidence_bucket(w=48, d=4, losses=48, n=100)
    assert confidence == "low"
    assert p_value == pytest.approx(0.5, abs=1e-9)


def test_low_at_n10_balanced() -> None:
    # n=10 score exactly 0.5: one-sided p = 0.5, n>=10, falls into "else low".
    confidence, p_value = compute_confidence_bucket(w=2, d=6, losses=2, n=10)
    assert confidence == "low"
    assert p_value == pytest.approx(0.5, abs=1e-9)


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
    """All draws at n=10: score=0.5, one-sided p=0.5 -> low (no evidence of any direction)."""
    confidence, p_value = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert confidence == "low"
    assert p_value == 0.5
