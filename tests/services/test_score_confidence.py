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

from app.services.opening_insights_constants import (
    OPENING_INSIGHTS_CI_Z_95 as CI_Z_95,
)
from app.services.score_confidence import (
    compute_confidence_bucket,
    compute_paired_difference_test,
    compute_per_bucket_diff_test,
    compute_score_confidence_from_mean,
    compute_score_difference_test,
    compute_skill_diff_test,
)


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


# --- Backward-compat regression after Wilson-math refactor ----------------
# Phase 83 Plan 2 Task 1: `_wilson_score_test_vs_half` is factored out as a
# private helper. `compute_confidence_bucket` is refactored to delegate to it,
# but its public signature and per-input output must be byte-for-byte
# preserved. Pin a single golden tuple so the refactor is detectable.


def test_compute_confidence_bucket_golden_after_refactor() -> None:
    """Pinned regression: (w=70, d=10, losses=20, n=100) yields the same triple
    as the pre-refactor Wilson implementation. If this changes, callers that
    persist or compare the tuple (e.g. opening_insights cache) will diverge."""
    confidence, p_value, se = compute_confidence_bucket(w=70, d=10, losses=20, n=100)
    assert confidence == "high"
    # score = (70 + 5) / 100 = 0.75; z = (0.75 - 0.5) / sqrt(0.25 / 100) = 5.0
    # two-sided p = erfc(5 / sqrt(2)) ~ 5.7e-7
    assert p_value == pytest.approx(5.733031e-7, rel=1e-5)
    # empirical variance = (70 + 0.25*10) / 100 - 0.75**2 = 0.725 - 0.5625 = 0.1625
    # se = sqrt(0.1625 / 100) ~ 0.040311
    assert se == pytest.approx(math.sqrt(0.1625 / 100), abs=1e-9)


# --- compute_score_confidence_from_mean (Phase 83 Plan 2 Task 1) ----------
# Sibling helper that accepts a float mean instead of (w, d, losses, n).
# Bucketing/gating must match `compute_confidence_bucket` exactly when given
# equivalent inputs (i.e. when (w + 0.5 * d) / n == score).


class TestComputeScoreConfidenceFromMean:
    """compute_score_confidence_from_mean(score, n) — Wilson sig test vs 0.5
    for a float mean. Same gates and thresholds as compute_confidence_bucket;
    single source of Wilson math via the new private helper."""

    def test_n_zero_returns_low_one_zero(self) -> None:
        """n <= 0 returns ("low", 1.0, 0.0) without raising."""
        confidence, p_value, se = compute_score_confidence_from_mean(score=0.7, n=0)
        assert confidence == "low"
        assert p_value == 1.0
        assert se == 0.0

    def test_n_below_gate_returns_low_with_real_p_value(self) -> None:
        """n=5 has real Wilson p-value (z = (score-0.5)/sqrt(0.25/5)), but the
        N>=10 sample-size gate forces confidence to "low" regardless."""
        confidence, p_value, _se = compute_score_confidence_from_mean(score=0.9, n=5)
        assert confidence == "low"
        # z = 0.4 / sqrt(0.05) = 1.7889; p = erfc(z / sqrt(2)) ~ 0.0736 — strong-ish
        # evidence but n < 10 gate fires.
        assert 0.0 < p_value < 1.0

    def test_centered_mean_returns_low_p_one(self) -> None:
        """score == 0.5 -> z = 0 -> two-sided p = 1.0 -> low (no evidence)."""
        confidence, p_value, _se = compute_score_confidence_from_mean(score=0.5, n=100)
        assert confidence == "low"
        assert p_value == pytest.approx(1.0, abs=1e-9)

    def test_strong_evidence_returns_high(self) -> None:
        """score=0.7, n=200 -> z = 0.2 / sqrt(0.25/200) = 5.657, p < 0.01 -> high."""
        confidence, p_value, _se = compute_score_confidence_from_mean(score=0.7, n=200)
        assert confidence == "high"
        assert p_value < 0.01

    def test_medium_evidence_returns_medium(self) -> None:
        """score=0.425, n=200 -> z = -2.121, p ~ 0.0339 -> medium (0.01 <= p < 0.05)."""
        confidence, p_value, _se = compute_score_confidence_from_mean(score=0.425, n=200)
        assert confidence == "medium"
        assert 0.01 <= p_value < 0.05

    def test_matches_compute_confidence_bucket_for_equivalent_inputs(self) -> None:
        """For (w + 0.5 * d) / n == score and the same n, the two helpers must
        return identical (confidence, p_value) pairs. SE differs by design
        (compute_confidence_bucket returns *empirical* SE; the from-mean variant
        has no W/D/L breakdown so SE is reported as 0.0 — see helper docstring)."""
        # 70 wins, 10 draws, 20 losses, n=100 -> score = 0.75
        bucket = compute_confidence_bucket(w=70, d=10, losses=20, n=100)
        from_mean = compute_score_confidence_from_mean(score=0.75, n=100)
        assert bucket[0] == from_mean[0]  # confidence
        assert bucket[1] == pytest.approx(from_mean[1], abs=1e-12)  # p_value

    def test_white_black_symmetry(self) -> None:
        """f(0.7, n) confidence/p == f(0.3, n) confidence/p — two-sided test is
        symmetric around 0.5."""
        up = compute_score_confidence_from_mean(score=0.7, n=200)
        down = compute_score_confidence_from_mean(score=0.3, n=200)
        assert up[0] == down[0]
        assert up[1] == pytest.approx(down[1], abs=1e-12)


# --- compute_score_difference_test (Phase 85.1 Plan 1 Task 1) -------------
# Independent two-sample z-test on chess-score difference between two WDL
# cohorts. Per SEC1-08/09: p_value gated to None when min(eg_n, ne_n) < 10
# (CONFIDENCE_MIN_N); CI bounds gated to None when min(eg_n, ne_n) < 2.
# Wald-on-difference (not Wilson) because the difference of two independent
# proportions does not reduce to a single-proportion problem. Variance-0
# trap follows the eval_confidence.py:116-119 pattern verbatim.


class TestComputeScoreDifferenceTest:
    """compute_score_difference_test(eg_w, eg_d, eg_l, eg_n, ne_w, ne_d, ne_l, ne_n)
    -> (p_value, ci_low, ci_high). Independent gates on p (n>=10) and CI (n>=2)."""

    # CONFIDENCE_MIN_N is 10; the bare 10/9 numbers below are gate boundaries.
    # Per existing test-file convention (see lines 35-39) we don't import the
    # constant — we assert against the literal value the test was written for.

    def test_n_zero_either_side_returns_all_none(self) -> None:
        """n=0 on either cohort gates both p and CI to None without raising."""
        p, lo, hi = compute_score_difference_test(
            eg_w=0,
            eg_d=0,
            eg_l=0,
            eg_n=0,
            ne_w=5,
            ne_d=5,
            ne_l=5,
            ne_n=15,
        )
        assert p is None
        assert lo is None
        assert hi is None

        p2, lo2, hi2 = compute_score_difference_test(
            eg_w=5,
            eg_d=5,
            eg_l=5,
            eg_n=15,
            ne_w=0,
            ne_d=0,
            ne_l=0,
            ne_n=0,
        )
        assert p2 is None
        assert lo2 is None
        assert hi2 is None

    def test_below_p_gate_returns_p_none_with_ci_present(self) -> None:
        """eg_n=9 (below CONFIDENCE_MIN_N=10) gates p_value but CI is still
        computed because eg_n >= 2."""
        p, lo, hi = compute_score_difference_test(
            eg_w=4,
            eg_d=2,
            eg_l=3,
            eg_n=9,
            ne_w=10,
            ne_d=5,
            ne_l=5,
            ne_n=20,
        )
        assert p is None
        assert lo is not None
        assert hi is not None
        assert lo <= hi

    def test_n_one_either_side_gates_ci_only(self) -> None:
        """ne_n=1 gates CI bounds (need n >= 2) and also gates p_value (n < 10)."""
        p, lo, hi = compute_score_difference_test(
            eg_w=8,
            eg_d=5,
            eg_l=2,
            eg_n=15,
            ne_w=1,
            ne_d=0,
            ne_l=0,
            ne_n=1,
        )
        assert p is None  # ne_n=1 < CONFIDENCE_MIN_N=10
        assert lo is None  # ne_n=1 < 2
        assert hi is None

    def test_identical_distributions_both_sides_give_p_one_ci_brackets_zero(self) -> None:
        """Same proportions both sides: score_eg == score_ne -> z=0 -> p=1.0.
        SE_diff > 0 (non-degenerate WDL spread) -> CI brackets 0 symmetrically."""
        p, lo, hi = compute_score_difference_test(
            eg_w=20,
            eg_d=10,
            eg_l=20,
            eg_n=50,
            ne_w=20,
            ne_d=10,
            ne_l=20,
            ne_n=50,
        )
        assert p == pytest.approx(1.0, abs=1e-9)
        assert lo is not None and hi is not None
        # score_eg - score_ne = 0, so CI is symmetric around 0.
        assert lo == pytest.approx(-hi, abs=1e-9)
        assert lo < 0.0 < hi

    def test_all_wins_vs_all_losses_collapses_to_point_estimate(self) -> None:
        """All-wins (10,0,0) vs all-losses (0,0,10): each side's variance is 0,
        so SE_diff = 0. score_eg - score_ne = 1.0 -> p_value=0.0 (perfectly
        determined), and CI collapses to ci_low == ci_high == 1.0."""
        p, lo, hi = compute_score_difference_test(
            eg_w=10,
            eg_d=0,
            eg_l=0,
            eg_n=10,
            ne_w=0,
            ne_d=0,
            ne_l=10,
            ne_n=10,
        )
        assert p == pytest.approx(0.0, abs=1e-9)
        assert lo == pytest.approx(1.0, abs=1e-9)
        assert hi == pytest.approx(1.0, abs=1e-9)

    def test_all_draws_both_sides_gives_p_one_zero_width_ci(self) -> None:
        """All-draws both sides: variance is 0 in each term (score=0.5,
        E[X^2] = 0.25*N/N = 0.25, var = 0.25 - 0.25 = 0). score_eg == score_ne
        -> p_value = 1.0. CI half-width = 0."""
        p, lo, hi = compute_score_difference_test(
            eg_w=0,
            eg_d=10,
            eg_l=0,
            eg_n=10,
            ne_w=0,
            ne_d=10,
            ne_l=0,
            ne_n=10,
        )
        assert p == pytest.approx(1.0, abs=1e-9)
        assert lo == pytest.approx(0.0, abs=1e-9)
        assert hi == pytest.approx(0.0, abs=1e-9)

    def test_ci_half_width_matches_wald_closed_form(self) -> None:
        """For known input (eg: w=60,d=20,l=20,n=100; ne: w=40,d=20,l=40,n=100),
        the CI half-width must equal CI_Z_95 * sqrt(var_eg/eg_n + var_ne/ne_n)
        where var_i = max(0, (w_i + 0.25*d_i)/n_i - score_i**2)."""
        eg_w, eg_d, eg_n = 60, 20, 100
        ne_w, ne_d, ne_n = 40, 20, 100
        score_eg = (eg_w + 0.5 * eg_d) / eg_n
        score_ne = (ne_w + 0.5 * ne_d) / ne_n
        var_eg = max(0.0, (eg_w + 0.25 * eg_d) / eg_n - score_eg * score_eg)
        var_ne = max(0.0, (ne_w + 0.25 * ne_d) / ne_n - score_ne * score_ne)
        se_diff = math.sqrt(var_eg / eg_n + var_ne / ne_n)
        # 1.96 is the constant CI_Z_95 already imported by the implementation.
        expected_half_width = 1.96 * se_diff
        expected_diff = score_eg - score_ne

        p, lo, hi = compute_score_difference_test(
            eg_w=eg_w,
            eg_d=eg_d,
            eg_l=20,
            eg_n=eg_n,
            ne_w=ne_w,
            ne_d=ne_d,
            ne_l=40,
            ne_n=ne_n,
        )
        assert p is not None
        assert lo is not None and hi is not None
        assert (hi - lo) / 2.0 == pytest.approx(expected_half_width, rel=1e-9)
        assert (lo + hi) / 2.0 == pytest.approx(expected_diff, rel=1e-9)

    def test_p_value_in_unit_interval_for_non_degenerate_input(self) -> None:
        """For any well-defined two-sample z-test, erfc(|z|/sqrt(2)) is in [0, 1]."""
        p, _lo, _hi = compute_score_difference_test(
            eg_w=70,
            eg_d=10,
            eg_l=20,
            eg_n=100,
            ne_w=30,
            ne_d=10,
            ne_l=60,
            ne_n=100,
        )
        assert p is not None
        assert 0.0 <= p <= 1.0


# --- compute_paired_difference_test (Phase 85.1 Plan 1 Task 2) ------------
# Paired one-sample z-test on per-game differences d_i = actual_i - expected_i.
# Per SEC1-10: mean_d always returned (0.0 when empty); p_value None when
# len(diffs) < 10 (CONFIDENCE_MIN_N); ci_* None when len(diffs) < 2. H0 is
# mean_d == 0. Variance uses Bessel correction (n-1 denominator).


class TestComputePairedDifferenceTest:
    """compute_paired_difference_test(diffs) -> (mean_d, p_value, ci_low, ci_high).

    H0: mean(diffs) == 0. p_value gated at n < 10; CI gated at n < 2.
    Bessel-corrected sample variance: var_d = max(0, (sumsq - n*mean^2) / (n-1)).
    """

    def test_empty_sequence_returns_zero_mean_all_none(self) -> None:
        """diffs=[] -> mean=0.0, p/ci all None. Must not raise."""
        mean_d, p, lo, hi = compute_paired_difference_test([])
        assert mean_d == 0.0
        assert p is None
        assert lo is None
        assert hi is None

    def test_n_one_returns_mean_but_no_p_no_ci(self) -> None:
        """diffs=[0.1] (n=1): Bessel correction divides by n-1 which is zero
        at n=1; the helper must short-circuit rather than divide-by-zero.
        mean is still computable and returned."""
        mean_d, p, lo, hi = compute_paired_difference_test([0.1])
        assert mean_d == pytest.approx(0.1, abs=1e-12)
        assert p is None
        assert lo is None
        assert hi is None

    def test_all_zeros_above_gate_gives_p_one_ci_collapses_to_zero(self) -> None:
        """diffs=[0.0]*15: SE=0, mean == H0=0 -> p=1.0, CI collapses to [0, 0]."""
        mean_d, p, lo, hi = compute_paired_difference_test([0.0] * 15)
        assert mean_d == pytest.approx(0.0, abs=1e-12)
        assert p == pytest.approx(1.0, abs=1e-9)
        assert lo == pytest.approx(0.0, abs=1e-9)
        assert hi == pytest.approx(0.0, abs=1e-9)

    def test_all_equal_nonzero_gives_p_zero_ci_collapses(self) -> None:
        """diffs=[0.25]*15: SE=0, mean != H0=0 -> p=0.0 (perfectly determined),
        CI collapses to [0.25, 0.25]."""
        mean_d, p, lo, hi = compute_paired_difference_test([0.25] * 15)
        assert mean_d == pytest.approx(0.25, abs=1e-12)
        assert p == pytest.approx(0.0, abs=1e-9)
        assert lo == pytest.approx(0.25, abs=1e-9)
        assert hi == pytest.approx(0.25, abs=1e-9)

    def test_below_p_gate_with_n_at_least_2_returns_ci(self) -> None:
        """diffs=[+0.1]*9 (n=9, below CONFIDENCE_MIN_N=10 but >=2): p is gated
        to None, but CI bounds are still returned (CI gate is n<2)."""
        mean_d, p, lo, hi = compute_paired_difference_test([0.1] * 9)
        assert mean_d == pytest.approx(0.1, abs=1e-12)
        assert p is None
        # All-equal nonzero -> SE=0, CI collapses to mean (still real floats).
        assert lo == pytest.approx(0.1, abs=1e-9)
        assert hi == pytest.approx(0.1, abs=1e-9)

    def test_known_mixed_dataset_matches_closed_form(self) -> None:
        """For diffs = [0.1, -0.1, 0.2, -0.2] * 5 (n=20):
        sum = 0; mean = 0; sumsq = (0.01 + 0.01 + 0.04 + 0.04) * 5 = 0.5;
        var_d = (0.5 - 20*0) / 19 = 0.5 / 19;
        se = sqrt(var_d / 20); ci_half = 1.96 * se;
        ci_high - ci_low = 2 * ci_half."""
        diffs = [0.1, -0.1, 0.2, -0.2] * 5
        n = len(diffs)
        expected_mean = sum(diffs) / n
        sumsq = sum(d * d for d in diffs)
        expected_var = max(0.0, (sumsq - n * expected_mean * expected_mean) / (n - 1))
        expected_se = math.sqrt(expected_var / n)
        expected_half_width = 1.96 * expected_se  # 1.96 == CI_Z_95

        mean_d, p, lo, hi = compute_paired_difference_test(diffs)
        assert mean_d == pytest.approx(expected_mean, abs=1e-12)
        assert p is not None
        assert lo is not None and hi is not None
        assert (hi - lo) / 2.0 == pytest.approx(expected_half_width, rel=1e-9)
        assert (lo + hi) / 2.0 == pytest.approx(expected_mean, abs=1e-9)

    def test_p_value_in_unit_interval_for_non_degenerate_input(self) -> None:
        """erfc(|z|/sqrt(2)) is in [0, 1] for any finite z."""
        diffs = [0.05 * i for i in range(-10, 10)]  # symmetric mean ~ -0.025
        _mean, p, _lo, _hi = compute_paired_difference_test(diffs)
        assert p is not None
        assert 0.0 <= p <= 1.0

    def test_bessel_correction_divides_by_n_minus_one(self) -> None:
        """Var must use Bessel correction. For diffs = [1.0, -1.0, 1.0, -1.0]*5
        (n=20), mean=0, sumsq=20. Bessel var = (20 - 0) / 19 = 1.0526...
        Naive var (/n) would be 1.0. Distinguish by checking the CI half-width."""
        diffs = [1.0, -1.0, 1.0, -1.0] * 5
        n = len(diffs)
        bessel_var = 20.0 / (n - 1)  # 20/19
        bessel_se = math.sqrt(bessel_var / n)
        bessel_half_width = 1.96 * bessel_se

        # Naive (/n) would yield a smaller half-width:
        naive_var = 20.0 / n  # 1.0
        naive_se = math.sqrt(naive_var / n)
        naive_half_width = 1.96 * naive_se
        assert bessel_half_width > naive_half_width  # sanity: they differ

        _mean, _p, lo, hi = compute_paired_difference_test(diffs)
        assert lo is not None and hi is not None
        assert (hi - lo) / 2.0 == pytest.approx(bessel_half_width, rel=1e-9)
        # Explicitly NOT the naive half-width:
        assert (hi - lo) / 2.0 != pytest.approx(naive_half_width, rel=1e-9)


# --- compute_skill_diff_test (Phase 86 Plan 1 Task 2) ---------------------
# Wald-z on the Skill composite (mean of Conv/Parity/Recov headline rates)
# vs the opponent's mirror composite. Variance per bucket is the HEADLINE-RATE
# variance (Conv Bernoulli win, Recov Bernoulli save, Parity trinomial
# chess-score) — NOT chess-score on all three (Phase 86 plan-checker BLOCKER 2).
# Mirror identity: opp_rate = 1 - userRate(opp_row), helper inverts internally.


class TestComputeSkillDiffTest:
    """compute_skill_diff_test(conv_row, parity_row, recov_row,
    opp_conv_row, opp_parity_row, opp_recov_row) -> (skill, opp_skill,
    p_value, ci_low, ci_high). Active bucket gate: user.N > 0 AND opp.N > 0.
    Sig fields None when n_active < 2 OR any active opp_row.N < 10."""

    def test_symmetric_50_50_gives_diff_near_zero(self) -> None:
        """Identical rows both sides (W=L on every bucket): skill ≈ opp_skill,
        diff ≈ 0, p_value ≈ 1.0, CI brackets 0. Both skills in [0, 1]."""
        row = (40, 20, 40, 100)
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=row,
            parity_row=row,
            recov_row=row,
            opp_conv_row=row,
            opp_parity_row=row,
            opp_recov_row=row,
        )
        assert skill is not None and opp_skill is not None
        assert 0.0 <= skill <= 1.0
        assert 0.0 <= opp_skill <= 1.0
        # Conv user_rate = 0.40; opp_rate = 1 - 0.40 = 0.60. Parity user = 0.50,
        # opp = 0.50. Recov user = 0.60, opp = 0.40. Mean diff = 0.
        assert skill == pytest.approx(opp_skill, abs=1e-12)
        assert p_value is not None
        assert p_value > 0.5
        assert ci_low is not None and ci_high is not None
        assert ci_low <= 0.0 <= ci_high

    def test_asymmetric_user_above_opp_is_significant(self) -> None:
        """User outperforms opp on every bucket -> skill > opp_skill, p < 0.05,
        ci_low > 0. Uses concrete WDL rows that produce a clean directional
        signal at n=100 per bucket.

        Opp-side rates use the W↔L swap identity (opp's W = user's L on the
        mirror row), NOT `1 - userRate(opp_row)`. For each opp row:
          - opp_conv_rate (in opp's conv bucket = user's recov bucket)
              = opp_row.L / opp_row.N
          - opp_recov_rate (in opp's recov bucket = user's conv bucket)
              = (opp_row.L + opp_row.D) / opp_row.N
          - opp_parity_rate                = (opp_row.L + 0.5 * opp_row.D) / opp_row.N
        """
        user_conv = (70, 0, 30, 100)  # Conv rate 0.70
        user_parity = (60, 20, 20, 100)  # Parity rate 0.70
        user_recov = (60, 20, 20, 100)  # Recov rate 0.80
        # Build mirror rows with concrete target opp rates after the W↔L swap.
        # Conv: target opp_rate = 0.50 -> opp_row.L/N = 0.50.
        opp_conv = (50, 0, 50, 100)  # L=50 -> opp_conv_rate = 0.50
        # Parity: target opp_rate = 0.55 -> (L + 0.5D)/N = 0.55.
        opp_parity = (40, 10, 50, 100)  # (50 + 5)/100 = 0.55
        # Recov: target opp_rate = 0.60 -> (L + D)/N = 0.60.
        opp_recov = (40, 10, 50, 100)  # (50 + 10)/100 = 0.60
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=user_conv,
            parity_row=user_parity,
            recov_row=user_recov,
            opp_conv_row=opp_conv,
            opp_parity_row=opp_parity,
            opp_recov_row=opp_recov,
        )
        assert skill is not None and opp_skill is not None
        # skill = mean(0.70, 0.70, 0.80) = 0.7333...
        assert skill == pytest.approx((0.70 + 0.70 + 0.80) / 3.0, abs=1e-9)
        # opp_skill = mean(0.50, 0.55, 0.60) = 0.55
        assert opp_skill == pytest.approx((0.50 + 0.55 + 0.60) / 3.0, abs=1e-9)
        assert skill > opp_skill
        assert p_value is not None and p_value < 0.05
        assert ci_low is not None and ci_high is not None
        assert ci_low > 0.0

    def test_one_active_bucket_gates_sig_but_returns_skills(self) -> None:
        """Only Conv has N > 0 on both sides. Skills are floats (single-bucket
        mean), but sig fields are all None (n_active < 2)."""
        conv = (60, 0, 40, 100)
        empty = (0, 0, 0, 0)
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=conv,
            parity_row=empty,
            recov_row=empty,
            opp_conv_row=(50, 0, 50, 100),
            opp_parity_row=empty,
            opp_recov_row=empty,
        )
        assert skill is not None and opp_skill is not None
        # Single-bucket mean = that bucket's rate.
        assert skill == pytest.approx(0.60, abs=1e-9)
        assert opp_skill == pytest.approx(0.50, abs=1e-9)  # 1 - 0.50
        assert p_value is None
        assert ci_low is None
        assert ci_high is None

    def test_sparse_opponent_gates_sig_but_returns_skills(self) -> None:
        """All 3 buckets active on user side (N=100), one opp bucket has N=8
        (< CONFIDENCE_MIN_N=10). Skills are floats; sig fields None."""
        user = (50, 0, 50, 100)
        sparse_opp_conv = (4, 0, 4, 8)  # N=8 < 10
        normal = (50, 0, 50, 100)
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=user,
            parity_row=user,
            recov_row=user,
            opp_conv_row=sparse_opp_conv,
            opp_parity_row=normal,
            opp_recov_row=normal,
        )
        assert skill is not None
        assert opp_skill is not None
        assert p_value is None
        assert ci_low is None
        assert ci_high is None

    def test_zero_active_buckets_returns_all_none(self) -> None:
        """Every row is (0, 0, 0, 0). No buckets active -> all five fields None."""
        empty = (0, 0, 0, 0)
        result = compute_skill_diff_test(
            conv_row=empty,
            parity_row=empty,
            recov_row=empty,
            opp_conv_row=empty,
            opp_parity_row=empty,
            opp_recov_row=empty,
        )
        assert result == (None, None, None, None, None)

    def test_variance_zero_trap_gives_p_zero_collapsed_ci(self) -> None:
        """Variance-0 trap: user all-wins (var=0 on every bucket) + opp_row
        also all-wins (so opp_rate = 1 - userRate(opp_row) = 1 - 1.0 = 0, var=0).
        SE_diff = 0; diff = 1.0 != 0 -> p_value = 0.0 (perfectly determined).
        CI collapses to ci_low == ci_high == 1.0.

        Mirrors the eval_confidence.py:116-119 pattern via
        compute_score_difference_test.
        """
        all_wins = (100, 0, 0, 100)
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=all_wins,
            parity_row=all_wins,
            recov_row=all_wins,
            opp_conv_row=all_wins,
            opp_parity_row=all_wins,
            opp_recov_row=all_wins,
        )
        assert skill == pytest.approx(1.0, abs=1e-12)
        assert opp_skill == pytest.approx(0.0, abs=1e-12)
        assert p_value == pytest.approx(0.0, abs=1e-12)
        assert ci_low is not None and ci_high is not None
        assert ci_low == pytest.approx(1.0, abs=1e-12)
        assert ci_high == pytest.approx(1.0, abs=1e-12)

    def test_skill_diff_uses_per_bucket_headline_variance_not_chess_score_variance(
        self,
    ) -> None:
        """Phase 86 plan-checker BLOCKER 2 regression. Conv variance under the
        win-rate Bernoulli formula (p*(1-p) with p=W/N) MUST differ from the
        chess-score variance ((W + 0.25*D)/N − score^2) for the same row.

        Fixture user_conv = (40, 20, 40, 100):
          - chess-score = (40 + 10) / 100 = 0.50
          - chess-score-variance = (40 + 5) / 100 − 0.25 = 0.20
          - headline-rate (win) variance = 0.40 * 0.60 = 0.24
        These differ by 0.04, which propagates into a measurably different
        SE_diff and CI half-width.

        Construct a 1-active-bucket-but-not-gated scenario? n_active < 2 gates
        the sig fields. Use a 2-active-bucket case (Conv + Recov; Parity empty
        on opp side so only Conv + Recov are active) and pin the CI half-width
        against the manually computed headline-rate-formula SE.
        """
        user_conv = (40, 20, 40, 100)  # Conv rate 0.40, win-var 0.24
        # opp_conv (40,20,40,100): W↔L swap is identity (W==L); new opp_rate
        # = 40/100 = 0.40, opp_var = 0.40*0.60 = 0.24.
        opp_conv = (40, 20, 40, 100)
        # Recov: user (60,20,20,100) -> rate 0.80, var = 0.80*0.20 = 0.16.
        user_recov = (60, 20, 20, 100)
        # opp_recov (60,20,20,100) -> swap to (20,20,60,100); new opp_recov_rate
        # = (20+20)/100 = 0.40; var = 0.40*0.60 = 0.24. (Old `1-X` formula would
        # have given 0.20 / 0.16 — the W↔L swap is the correct mirror-bucket
        # identity for asymmetric Conv/Recov rates whenever D > 0.)
        opp_recov = (60, 20, 20, 100)
        # Use empty parity rows so only Conv + Recov are active (n_active=2,
        # passes the n_active>=2 sig gate).
        empty = (0, 0, 0, 0)
        skill, opp_skill, p_value, ci_low, ci_high = compute_skill_diff_test(
            conv_row=user_conv,
            parity_row=empty,
            recov_row=user_recov,
            opp_conv_row=opp_conv,
            opp_parity_row=empty,
            opp_recov_row=opp_recov,
        )
        # Skill = (0.40 + 0.80) / 2 = 0.60. Opp_skill = (0.40 + 0.40) / 2 = 0.40.
        # Diff = 0.20. n_active = 2; opp Ns are 100 (>= 10) -> sig fields populated.
        assert skill == pytest.approx(0.60, abs=1e-9)
        assert opp_skill == pytest.approx(0.40, abs=1e-9)
        assert p_value is not None
        assert ci_low is not None and ci_high is not None

        # Expected SE under the HEADLINE-RATE formula with the W↔L swap on opp:
        # SE_user = sqrt(0.24/100 + 0.16/100) / 2
        # SE_opp  = sqrt(0.24/100 + 0.24/100) / 2  (opp_recov var 0.24, not 0.16)
        # SE_diff = sqrt(SE_user^2 + SE_opp^2)
        expected_se_user = math.sqrt(0.24 / 100 + 0.16 / 100) / 2
        expected_se_opp = math.sqrt(0.24 / 100 + 0.24 / 100) / 2
        expected_se_diff = math.sqrt(expected_se_user**2 + expected_se_opp**2)
        expected_half_width = CI_Z_95 * expected_se_diff
        observed_half_width = (ci_high - ci_low) / 2.0
        assert observed_half_width == pytest.approx(expected_half_width, rel=1e-9)

        # Sanity: had the implementation used chess-score variance on Conv
        # (0.20 instead of 0.24), SE_user would have been:
        #   SE_user_wrong = sqrt(0.20/100 + 0.16/100) / 2 = sqrt(0.0036) / 2
        # which is strictly smaller. Distinguish:
        wrong_se_user = math.sqrt(0.20 / 100 + 0.16 / 100) / 2
        wrong_se_opp = math.sqrt(0.20 / 100 + 0.24 / 100) / 2
        wrong_se_diff = math.sqrt(wrong_se_user**2 + wrong_se_opp**2)
        wrong_half_width = CI_Z_95 * wrong_se_diff
        # The two CI half-widths must NOT be equal — confirms the helper used
        # the headline-rate variance (not the chess-score variance) for Conv.
        assert observed_half_width != pytest.approx(wrong_half_width, rel=1e-6)


# --- compute_per_bucket_diff_test (Phase 86 Plan 1 Task 2) ----------------
# Wald-z on `userRate - opponentRate` for a single Conv/Parity/Recov bucket.
# Mirror identity: opp_rate = 1 - userRate(opp_row), inverted internally.
# Strict opp-side gate at opp_row.N < CONFIDENCE_MIN_N = 10 per D-05.


class TestComputePerBucketDiffTest:
    """compute_per_bucket_diff_test(bucket, user_row, opp_row) ->
    (p_value, ci_low, ci_high). Strict opp-side N>=10 gate (D-05).
    Parity self-mirror (opp_row IS the user parity row) MUST produce
    diff = 2*user_rate - 1, NOT 0 (Phase 86 plan-checker BLOCKER 1)."""

    def test_conversion_symmetric_diff_zero(self) -> None:
        """User Conv (W=L=10, D=0) vs symmetric opp (W=L=10, D=0):
        user_rate = 10/20 = 0.5; opp_rate = 1 - 10/20 = 0.5; diff = 0.
        SE_diff > 0 -> p_value ≈ 1 (z = 0)."""
        user_row = (10, 0, 10, 20)
        opp_row = (10, 0, 10, 20)
        p_value, ci_low, ci_high = compute_per_bucket_diff_test("conversion", user_row, opp_row)
        assert p_value is not None
        assert p_value == pytest.approx(1.0, abs=1e-9)
        assert ci_low is not None and ci_high is not None
        assert ci_low <= 0.0 <= ci_high

    def test_conversion_asymmetric_significant(self) -> None:
        """User Conv (70, 0, 30, 100) -> user_rate = 0.70. Opp_row mirror
        (50, 0, 50, 100) -> userRate(opp) = 0.50 -> opp_rate = 1 - 0.50 = 0.50.
        diff = 0.20, n=100 each -> p << 0.05."""
        p_value, ci_low, ci_high = compute_per_bucket_diff_test(
            "conversion",
            user_row=(70, 0, 30, 100),
            opp_row=(50, 0, 50, 100),
        )
        assert p_value is not None and p_value < 0.05
        assert ci_low is not None and ci_high is not None
        # CI midpoint = diff = 0.20.
        assert (ci_low + ci_high) / 2.0 == pytest.approx(0.20, abs=1e-9)
        assert ci_low > 0.0

    def test_parity_self_mirror_produces_nontrivial_diff(self) -> None:
        """Phase 86 plan-checker BLOCKER 1 regression: parity bucket's mirror
        is parity itself (MIRROR_BUCKET['parity'] = 'parity'). When opp_row IS
        the same parity row as user_row, diff = 2*user_rate - 1, NOT 0.

        Concretely: user_row = (60, 20, 20, 100) -> user_rate = 0.70.
        opp_row = SAME row -> userRate(opp_row) = 0.70 -> opp_rate = 1 - 0.70 = 0.30.
        diff = 0.40, NOT 0. p_value << 0.001 at n=100.

        Without the headline-rate identity (`oppRate = 1 - userRate(opp_row)`),
        a naive "chess-score on two independent cohorts" approach would have
        produced diff = (W+0.5D)/N − (W+0.5D)/N = 0 for self-mirror, hiding
        the signal entirely.
        """
        row = (60, 20, 20, 100)
        p_value, ci_low, ci_high = compute_per_bucket_diff_test("parity", user_row=row, opp_row=row)
        assert p_value is not None
        assert p_value < 0.001
        assert ci_low is not None and ci_high is not None
        # Diff is recoverable from CI midpoint = diff.
        observed_diff = (ci_low + ci_high) / 2.0
        assert observed_diff == pytest.approx(0.40, abs=1e-9)
        assert ci_low > 0.20

    def test_recovery_uses_w_l_swap_mirror_identity(self) -> None:
        """Recovery bucket diff with the correct W↔L swap on the mirror row
        (opp's W = user's L in user's conversion bucket).

        user_row in user's Recov bucket: (50, 30, 20, 100) -> save rate 0.80.
        opp_row is user's row in user's CONVERSION bucket: (50, 20, 30, 100).
        Opp's recov rate (in opp's recov bucket = user's conv bucket) =
        (opp_W + opp_D)/N = (user_L_in_conv + user_D_in_conv)/N =
        (30 + 20)/100 = 0.50.
        diff = 0.80 - 0.50 = 0.30; n=100 each -> p << 0.05; ci_low > 0.

        Regression for the Phase 86 close-out CI bug: the old code used
        `1 - _headline_rate('recov', opp_row)` = 1 - (50+20)/100 = 0.30 for
        opp_rate, giving diff = 0.50 — different from the frontend's
        `userRate - opponentRate` (which uses the mirror loss_pct directly),
        so the CI bar didn't even straddle the displayed diff."""
        p_value, ci_low, ci_high = compute_per_bucket_diff_test(
            "recovery",
            user_row=(50, 30, 20, 100),
            opp_row=(50, 20, 30, 100),
        )
        assert p_value is not None and p_value < 0.05
        assert ci_low is not None and ci_high is not None
        # CI midpoint = diff = 0.30.
        assert (ci_low + ci_high) / 2.0 == pytest.approx(0.30, abs=1e-9)
        assert ci_low > 0.0

    def test_conversion_uses_w_l_swap_with_draws_in_mirror(self) -> None:
        """Conversion-bucket regression for the Phase 86 close-out CI bug.

        When the mirror (Recov) row has D > 0, `1 - userRate(opp_row)`
        overstates the opponent's conversion rate by attributing opp draws to
        opp wins. The correct opp_conv_rate is `opp_row.L / opp_row.N`
        (= user's L in their recov bucket / N, via same-game W↔L swap).

        user_row in user's Conv bucket: (60, 0, 40, 100) -> win rate 0.60.
        opp_row is user's row in user's RECOV bucket: (40, 20, 40, 100).
        Opp's conv rate = opp_row.L / N = 40/100 = 0.40.
        diff = 0.60 - 0.40 = 0.20, NOT 0.

        Under the old (buggy) `1 - 40/100` formula, opp_rate would be 0.60
        and diff would be 0 — hiding a real 20pp gap."""
        p_value, ci_low, ci_high = compute_per_bucket_diff_test(
            "conversion",
            user_row=(60, 0, 40, 100),
            opp_row=(40, 20, 40, 100),
        )
        assert p_value is not None
        assert ci_low is not None and ci_high is not None
        # CI midpoint = diff = 0.20 (NOT 0, which the buggy formula would give).
        assert (ci_low + ci_high) / 2.0 == pytest.approx(0.20, abs=1e-9)
        assert ci_low > 0.0

    def test_sparse_opp_returns_none(self) -> None:
        """D-05 strict opp-side gate: opp_row.N=9 (< CONFIDENCE_MIN_N=10) ->
        all three fields None, even with user_row.N=100."""
        p_value, ci_low, ci_high = compute_per_bucket_diff_test(
            "conversion",
            user_row=(70, 0, 30, 100),
            opp_row=(5, 0, 4, 9),
        )
        assert p_value is None
        assert ci_low is None
        assert ci_high is None

    def test_user_n_zero_returns_none(self) -> None:
        """No user-side games -> all three None (early-return)."""
        p_value, ci_low, ci_high = compute_per_bucket_diff_test(
            "conversion",
            user_row=(0, 0, 0, 0),
            opp_row=(50, 0, 50, 100),
        )
        assert p_value is None
        assert ci_low is None
        assert ci_high is None
