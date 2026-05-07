"""Unit tests for app.services.score_confidence.compute_confidence_bucket.

Bucketing rule under test (unified two-sided standard, 260505):
  - n < 10                        -> "low"  (unreliable-stats gate)
  - n >= 10 and p_value < 0.01    -> "high"
  - n >= 10 and p_value < 0.05    -> "medium"
  - n >= 10 and p_value >= 0.05   -> "low"

p_value is the two-sided Wilson score-test p on H0: score == 0.50, computed
as erfc(|z| / sqrt(2)) with z = (score - 0.5) / SE_null and
SE_null = sqrt(0.5 * 0.5 / n) = 0.5 / sqrt(n) (null variance, not empirical).

Wilson is well-defined at all boundaries: all-wins gives p ~ 0.00157 at n=10
(not 0.0 as under Wald's degenerate SE=0 case); all-losses likewise; all-draws
gives p = 1.0 (z = 0).

The helper returns a 3-tuple (confidence, p_value, se). The third element is
the *empirical* trinomial standard error, retained for backward compat and
informational only — not used in the Wilson p-value computation.
"""

import math

import pytest

from app.services.score_confidence import compute_confidence_bucket


# --- N < 10 gate ---------------------------------------------------------


def test_n_below_gate_returns_low_even_with_strong_evidence() -> None:
    # n=9 all wins under Wilson: z = sqrt(9) = 3.0, p ~ 0.0027 — but n<10 forces "low".
    confidence, p_value, _se = compute_confidence_bucket(w=9, d=0, losses=0, n=9)
    assert confidence == "low"
    assert p_value == pytest.approx(0.0026997961, abs=1e-6)


def test_n_below_gate_single_win_is_low() -> None:
    # n=1 single win: under Wilson z = 1/sqrt(1) = 1.0, p ~ 0.317 — well above any threshold.
    # The N gate would force "low" anyway; this test pins the gate behavior.
    confidence, _p, _se = compute_confidence_bucket(w=1, d=0, losses=0, n=1)
    assert confidence == "low"


def test_n_below_gate_balanced_is_low() -> None:
    confidence, _p, _se = compute_confidence_bucket(w=2, d=2, losses=2, n=6)
    assert confidence == "low"


def test_n_zero_returns_low_one() -> None:
    """MD-02 guard: n<=0 returns ("low", 1.0, 0.0) without raising — 1.0 is the
    two-sided null and SE is zero with no sample."""
    confidence, p_value, se = compute_confidence_bucket(w=0, d=0, losses=0, n=0)
    assert confidence == "low"
    assert p_value == 1.0
    assert se == 0.0


# --- N >= 10 buckets by p-value ------------------------------------------


def test_high_at_strong_evidence() -> None:
    # n=400, w=80, d=80, losses=240: score = 0.30, z = (0.30-0.5)/sqrt(0.25/400) = -8.0,
    # two-sided p ~ 1.2e-15, well below 0.01.
    confidence, p_value, _se = compute_confidence_bucket(w=80, d=80, losses=240, n=400)
    assert confidence == "high"
    assert p_value < 0.01


def test_medium_at_moderate_evidence() -> None:
    # n=200, w=85, d=0, losses=115: score=0.425, z = -0.075/sqrt(0.25/200) = -2.121,
    # two-sided p ~ 0.0339, lands in [0.01, 0.05) -> medium.
    confidence, p_value, _se = compute_confidence_bucket(w=85, d=0, losses=115, n=200)
    assert confidence == "medium"
    assert 0.01 <= p_value < 0.05


def test_low_at_weak_evidence_with_large_n() -> None:
    # Score exactly 0.50 with n=100: z = 0, two-sided p = 1.0 -> low.
    confidence, p_value, _se = compute_confidence_bucket(w=48, d=4, losses=48, n=100)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


def test_low_at_n10_balanced() -> None:
    # n=10 score exactly 0.5: z = 0, two-sided p = 1.0, n>=10, falls into "else low".
    confidence, p_value, _se = compute_confidence_bucket(w=2, d=6, losses=2, n=10)
    assert confidence == "low"
    assert p_value == pytest.approx(1.0, abs=1e-9)


# --- Boundary cases (Wilson is well-defined; no SE=0 degeneracy) ---------


def test_all_wins_n10_is_high() -> None:
    """All wins at n=10: z = sqrt(10) ~ 3.162, p ~ 0.00157 -> high.

    Under the previous Wald formula, this case had SE=0 and was special-cased
    to p=0.0. Wilson's null SE = 0.5/sqrt(n) is positive for any n>0, so the
    test is well-defined without a special case.
    """
    confidence, p_value, _se = compute_confidence_bucket(w=10, d=0, losses=0, n=10)
    assert confidence == "high"
    assert p_value == pytest.approx(0.0015654023, abs=1e-6)


def test_all_losses_n10_is_high() -> None:
    confidence, p_value, _se = compute_confidence_bucket(w=0, d=0, losses=10, n=10)
    assert confidence == "high"
    assert p_value == pytest.approx(0.0015654023, abs=1e-6)


def test_all_draws_n10_is_low() -> None:
    """All draws at n=10: score=0.5 -> z=0 -> two-sided p=1.0 -> low (no evidence)."""
    confidence, p_value, _se = compute_confidence_bucket(w=0, d=10, losses=0, n=10)
    assert confidence == "low"
    assert p_value == 1.0


# --- SE component (third tuple element) ----------------------------------
# The returned SE is the *empirical* trinomial SE, not the Wilson null SE
# used in the test. Retained for backward compat with callers that built Wald
# CI bounds — informational only since the score CI is now Wilson everywhere.


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
