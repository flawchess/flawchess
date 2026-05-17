"""Wave 0 unit tests for the Phase 87.5 additive K mapping (Endgame ELO).

Phase 87.5 replaces the Phase 87.4 affine-recenter + Phase 57 multiplicative formula
with a single additive formula::

    endgame_elo = round(actual_elo + K * eg_score_gap)

where ``eg_score_gap`` is the per-week windowed difference between endgame and
non-endgame outcome means (already produced by ``_compute_score_gap_timeline``).
At ``eg_score_gap == 0`` the result equals ``round(actual_elo)`` exactly — the
neutral case is literal zero, not a benchmark-derived constant.

K is calibrated against the Lichess benchmark §3.1.6 percentile table::

    p05 = -0.2272  → round(K * -0.2272)
    p25 = -0.1035  → round(K * -0.1035)
    p50 = -0.0140  → round(K * -0.0140)
    p75 = +0.0725  → round(K * +0.0725)
    p95 = +0.2016  → round(K * +0.2016)

At K=450: p95 ≈ +91 ELO, p05 ≈ -102 ELO, typical p25/p75 ≈ ±33-47 ELO.

These tests start RED (the helper does not exist yet) and turn GREEN in Task 3.
"""

from __future__ import annotations

import pytest

from app.services.endgame_service import (
    K,
    _endgame_elo_from_score_gap,
)

# §3.1.6 percentile reference values (reports/benchmarks-latest.md line 174).
_P05_GAP = -0.227
_P25_GAP = -0.104
_P75_GAP = +0.073
_P95_GAP = +0.202

# The locked K value. Bumping this test is intentional drift-detection — any future
# recalibration must visibly change this constant via a deliberate commit.
_LOCKED_K = 450.0


class TestEndgameEloFromScoreGap:
    """SC#3: additive K mapping correctness."""

    def test_zero_gap_preserves_actual_elo(self) -> None:
        # SC#3 invariant: gap = 0 ⇒ endgame_elo == actual_elo exactly.
        assert _endgame_elo_from_score_gap(1500.0, 0.0, K) == 1500

    @pytest.mark.parametrize("actual_elo", [800.0, 1200.0, 1500.0, 2000.0, 2400.0])
    def test_zero_gap_various_actual_elos(self, actual_elo: float) -> None:
        # Invariant must hold across the realistic rating range.
        assert _endgame_elo_from_score_gap(actual_elo, 0.0, K) == int(round(actual_elo))

    def test_positive_p95_gap(self) -> None:
        # p95 mapping: actual + round(K * +0.202).
        expected = round(1500.0 + K * _P95_GAP)
        assert _endgame_elo_from_score_gap(1500.0, _P95_GAP, K) == expected

    def test_negative_p05_gap(self) -> None:
        # p05 mapping: actual + round(K * -0.227).
        expected = round(1500.0 + K * _P05_GAP)
        assert _endgame_elo_from_score_gap(1500.0, _P05_GAP, K) == expected

    def test_rounds_to_int(self) -> None:
        # Output must be an int (rounding contract).
        result = _endgame_elo_from_score_gap(1500.0, 0.001, K)
        assert isinstance(result, int)

    def test_typical_band_p25_p75(self) -> None:
        # At p25/p75 the magnitude should sit in the "typical 30-60 ELO" band.
        # K=450 gives p25 ≈ -47, p75 ≈ +33 — both within ±50 of zero.
        delta_p25 = _endgame_elo_from_score_gap(1500.0, _P25_GAP, K) - 1500
        delta_p75 = _endgame_elo_from_score_gap(1500.0, _P75_GAP, K) - 1500
        assert -60 <= delta_p25 <= -20
        assert 20 <= delta_p75 <= 60

    def test_paired_diff_matches_formula(self) -> None:
        # Optional paired-diff test (per Q5 in RESEARCH.md): for a synthetic series
        # of pairs the produced series satisfies
        #   endgame_elo[i] - actual_elo[i] == round(K * eg_score_gap[i])
        # point-by-point. This is the load-bearing invariant for the LLM payload
        # (insights_service computes last.endgame_elo - last.actual_elo).
        pairs = [
            (800.0, -0.20),
            (1200.0, -0.05),
            (1500.0, 0.0),
            (1800.0, +0.10),
            (2200.0, +0.25),
        ]
        for actual_elo, gap in pairs:
            endgame_elo = _endgame_elo_from_score_gap(actual_elo, gap, K)
            # int(round(actual_elo + K*gap)) - int(round(actual_elo))
            # may differ from round(K*gap) by 1 only when actual_elo has a
            # fractional part; all test inputs are integral floats so the
            # identity is exact.
            assert endgame_elo - int(round(actual_elo)) == round(K * gap)

    def test_K_constant_locked(self) -> None:
        # Drift-detection: a future recalibration must visibly bump this test.
        assert K == _LOCKED_K
