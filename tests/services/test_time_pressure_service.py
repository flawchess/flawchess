"""Service-level tests for _compute_time_pressure_cards (Phase 88, Plan 04).

Tests cover:
- TC card gating (MIN_GAMES_PER_TC_CARD threshold)
- Quintile bucketing boundary behaviour
- Per-quintile WDL accumulator
- Clock gap via compute_paired_difference_test
- cohort_score=None neutral-bullet path
- base_clock<=0 guard (T-88-04-02)
- Card ordering (bullet -> blitz -> rapid -> classical)
"""

from typing import Any

import pytest

from app.services.endgame_service import (
    MIN_GAMES_PER_TC_CARD,
    _compute_time_pressure_cards,
)
from app.services.score_confidence import compute_paired_difference_test


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _make_row(
    tc: str,
    user_clk_pct: float,
    opp_clk_pct: float,
    result: str = "1-0",
    user_color: str = "white",
    base_time_seconds: int = 300,
    game_id: int = 1,
) -> tuple[Any, ...]:
    """Build a minimal clock-stats row matching the shape consumed by _iterate_clock_rows.

    Row indices consumed:
        [1] time_control_bucket
        [2] base_time_seconds
        [4] result
        [5] user_color
        [6] ply_array
        [7] clock_array

    We use white-at-ply-0 (even) for user_clock, ply-1 (odd) for opp_clock.
    user_color="white" so _extract_entry_clocks extracts (ply-0, ply-1).
    """
    user_clock = user_clk_pct * base_time_seconds
    opp_clock = opp_clk_pct * base_time_seconds
    return (
        game_id,          # [0] game_id
        tc,               # [1] time_control_bucket
        base_time_seconds,  # [2] base_time_seconds
        None,             # [3] termination
        result,           # [4] result
        user_color,       # [5] user_color
        [0, 1],           # [6] ply_array (0=white's first move, 1=black's first move)
        [user_clock, opp_clock],  # [7] clock_array
    )


def _empty_cohort() -> dict[tuple[str, int], float]:
    """Return an empty cohort lookup (no cohort data for any TC+quintile)."""
    return {}


def _cohort_with(mapping: dict[tuple[str, int], float]) -> dict[tuple[str, int], float]:
    """Return cohort lookup with the specified (tc, quintile) -> score entries."""
    return mapping


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTcCardThreshold:
    def test_tc_card_hidden_below_threshold(self) -> None:
        """19 bullet games -> no bullet card in response (below MIN_GAMES_PER_TC_CARD=20)."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(MIN_GAMES_PER_TC_CARD - 1)]
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert result.cards == []

    def test_tc_card_visible_at_threshold(self) -> None:
        """Exactly 20 bullet games -> bullet card present."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)]
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1
        assert result.cards[0].tc == "bullet"

    def test_tc_card_visible_above_threshold(self) -> None:
        """25 bullet games -> bullet card present."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(25)]
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1
        assert result.cards[0].tc == "bullet"


class TestQuintileBucketing:
    """Quintile boundary behaviour tests.

    min(4, int(user_clk_pct * 5)) maps:
      0.00 -> int(0.0)   = 0  -> quintile 0
      0.19 -> int(0.95)  = 0  -> quintile 0
      0.20 -> int(1.0)   = 1  -> quintile 1
      0.50 -> int(2.5)   = 2  -> quintile 2
      0.99 -> int(4.95)  = 4  -> quintile 4
      1.00 -> int(5.0)   = 5  -> min(4,5) = 4  -> quintile 4
    """

    def _run_single_game(self, user_clk_pct: float, tc: str = "blitz") -> list[int]:
        """Run a single game and return the quintile indices that have n>0."""
        rows = [_make_row(tc, user_clk_pct, 0.5, game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)]
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1
        return [b.quintile_index for b in result.cards[0].quintiles if b.n > 0]

    def test_quintile_bucketing_correct(self) -> None:
        """user_clk_pct 0.0, 0.19, 0.20, 0.50, 0.99 map to quintiles 0, 0, 1, 2, 4."""
        # Use one game per clk_pct but pad to MIN_GAMES_PER_TC_CARD with neutral games
        tc = "blitz"
        base = 300

        # Build 20 games: 5 at distinct clk_pcts + 15 filler at 0.5 (quintile 2)
        test_cases: list[tuple[float, int]] = [
            (0.0, 0),
            (0.19, 0),
            (0.20, 1),
            (0.50, 2),
            (0.99, 4),
        ]
        rows: list[tuple[Any, ...]] = []
        for game_id, (clk_pct, _expected_q) in enumerate(test_cases):
            rows.append(_make_row(tc, clk_pct, 0.5, game_id=game_id, base_time_seconds=base))
        # Pad to threshold with quintile-2 games
        for i in range(len(test_cases), MIN_GAMES_PER_TC_CARD):
            rows.append(_make_row(tc, 0.5, 0.5, game_id=100 + i, base_time_seconds=base))

        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1
        card = result.cards[0]
        assert len(card.quintiles) == 5

        # Verify each quintile_label
        expected_labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
        for q_idx, q_bullet in enumerate(card.quintiles):
            assert q_bullet.quintile_index == q_idx
            assert q_bullet.quintile_label == expected_labels[q_idx]


class TestPerQuintileWdlAccumulator:
    def test_per_quintile_wdl_accumulator(self) -> None:
        """10 games in (bullet, quintile 2) with 6W 2D 2L.

        user_clk_pct=0.50 -> quintile 2 (mid-pressure).
        Expected user_score = (6 + 0.5*2) / 10 = 0.70.
        """
        tc = "bullet"
        base = 300
        cohort_score = 0.50
        cohort = _cohort_with({(tc, 2): cohort_score})

        rows: list[tuple[Any, ...]] = []
        for i in range(6):
            rows.append(_make_row(tc, 0.50, 0.50, result="1-0", user_color="white", game_id=i, base_time_seconds=base))
        for i in range(2):
            rows.append(_make_row(tc, 0.50, 0.50, result="1/2-1/2", user_color="white", game_id=100 + i, base_time_seconds=base))
        for i in range(2):
            rows.append(_make_row(tc, 0.50, 0.50, result="0-1", user_color="white", game_id=200 + i, base_time_seconds=base))
        # Pad to MIN_GAMES_PER_TC_CARD with quintile-0 games so the card is emitted
        for i in range(MIN_GAMES_PER_TC_CARD - 10):
            rows.append(_make_row(tc, 0.01, 0.01, game_id=300 + i, base_time_seconds=base))

        result = _compute_time_pressure_cards(rows, cohort)
        assert len(result.cards) == 1
        card = result.cards[0]

        q2 = card.quintiles[2]
        assert q2.n == 10
        assert q2.cohort_score == pytest.approx(cohort_score)
        expected_delta = 0.70 - cohort_score
        assert q2.delta == pytest.approx(expected_delta, abs=1e-9)


class TestClockGap:
    def test_clock_gap_uses_paired_diff_test(self) -> None:
        """Known clock_diff list yields mean and CI matching compute_paired_difference_test directly."""
        tc = "rapid"
        base = 600
        # 20 games: user at 60% clock, opp at 40% -> diff = (60-40)/100 * base = 0.20
        rows = [
            _make_row(tc, 0.60, 0.40, game_id=i, base_time_seconds=base)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1

        clock_gap = result.cards[0].clock_gap
        assert clock_gap.n == MIN_GAMES_PER_TC_CARD

        # Compute expected values via the same underlying function.
        expected_diffs = [0.20] * MIN_GAMES_PER_TC_CARD
        exp_mean, exp_p, exp_ci_low, exp_ci_high = compute_paired_difference_test(expected_diffs)

        assert clock_gap.mean_diff_pct == pytest.approx(exp_mean, abs=1e-9)
        assert clock_gap.p_value == pytest.approx(exp_p, abs=1e-6) if exp_p is not None else clock_gap.p_value is None
        assert clock_gap.ci_low == pytest.approx(exp_ci_low, abs=1e-9) if exp_ci_low is not None else clock_gap.ci_low is None
        assert clock_gap.ci_high == pytest.approx(exp_ci_high, abs=1e-9) if exp_ci_high is not None else clock_gap.ci_high is None


class TestCohortScoreNone:
    def test_cohort_score_none_emits_neutral_bullet(self) -> None:
        """When cohort_lookup has no entry for a quintile, that bullet has delta=0.0
        and all stats None, but n still reflects the bin count.
        """
        tc = "classical"
        base = 1800
        cohort: dict[tuple[str, int], float] = {}  # no cohort data

        # 20 games at quintile 2 (user_clk_pct=0.5)
        rows = [_make_row(tc, 0.50, 0.50, game_id=i, base_time_seconds=base) for i in range(MIN_GAMES_PER_TC_CARD)]
        result = _compute_time_pressure_cards(rows, cohort)
        assert len(result.cards) == 1

        q2 = result.cards[0].quintiles[2]
        assert q2.delta == pytest.approx(0.0)
        assert q2.p_value is None
        assert q2.ci_low is None
        assert q2.ci_high is None
        assert q2.cohort_score is None
        assert q2.n == MIN_GAMES_PER_TC_CARD


class TestBaseClockGuard:
    def test_base_clock_zero_or_missing_skipped(self) -> None:
        """Rows with base_time_seconds <= 0 are skipped.

        19 valid games + 10 games with base_clock=0 -> still below threshold (no card).
        """
        valid_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=i, base_time_seconds=300)
            for i in range(MIN_GAMES_PER_TC_CARD - 1)
        ]
        # Rows with base_time_seconds=0 should be skipped
        bad_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=100 + i, base_time_seconds=0)
            for i in range(10)
        ]
        rows = valid_rows + bad_rows
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        # Only 19 valid games counted -> below threshold -> no card
        assert result.cards == []

    def test_base_clock_zero_games_not_counted(self) -> None:
        """Exactly MIN_GAMES_PER_TC_CARD valid games plus base_clock=0 rows emit one card."""
        valid_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=i, base_time_seconds=300)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        bad_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=100 + i, base_time_seconds=0)
            for i in range(5)
        ]
        rows = valid_rows + bad_rows
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 1
        assert result.cards[0].tc == "blitz"
        assert result.cards[0].total == MIN_GAMES_PER_TC_CARD


class TestCardOrder:
    def test_card_order_bullet_blitz_rapid_classical(self) -> None:
        """When all four TCs pass the threshold, cards are ordered bullet->blitz->rapid->classical."""
        rows: list[tuple[Any, ...]] = []
        for tc in ["classical", "rapid", "blitz", "bullet"]:  # intentionally reversed
            for i in range(MIN_GAMES_PER_TC_CARD):
                rows.append(_make_row(tc, 0.5, 0.5, game_id=hash((tc, i)) % 10_000_000))
        result = _compute_time_pressure_cards(rows, _empty_cohort())
        assert len(result.cards) == 4
        assert [c.tc for c in result.cards] == ["bullet", "blitz", "rapid", "classical"]
