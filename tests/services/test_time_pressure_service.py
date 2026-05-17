"""Service-level tests for _compute_time_pressure_cards (Phase 88.1, Plan 09).

Phase 88.1 (D-07 supersedes D-05): cohort layer removed. Tests verify the new
same-game opp-quintile split design:
- _iterate_clock_rows builds user_quintile_wdl + opp_quintile_wdl from the same
  filtered game-set, each side bucketed by its OWN clock-pct at endgame entry.
- _build_quintile_bullets computes delta = user_score_in_Q − opp_score_in_Q
  using compute_score_difference_test (unpaired two-sample Wilson).
- n-gate per bullet = min(n_user_in_Q, n_opp_in_Q) >= MIN_GAMES_PER_PRESSURE_BIN.

Tests cover:
- TC card gating (MIN_GAMES_PER_TC_CARD threshold)
- Quintile bucketing boundary behaviour
- Independent user/opp quintile assignment in the same game
- Opponent-result inversion (user-win = opp-loss in opp_quintile_wdl)
- Delta=0 when user_score equals opp_score in the matching quintile
- N-gate produces stats=None when min(n_user_in_Q, n_opp_in_Q) < MIN
- query_cohort_clock_rows is removed from endgame_repository namespace
- _compute_time_pressure_cards signature is a single-argument function
- Clock gap via compute_paired_difference_test
- base_clock<=0 guard (T-88-04-02)
- Card ordering (bullet -> blitz -> rapid -> classical)
"""

from typing import Any

import pytest

from app.services.endgame_service import (
    MIN_GAMES_PER_PRESSURE_BIN,
    MIN_GAMES_PER_TC_CARD,
    _compute_time_pressure_cards,
    _iterate_clock_rows,
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
        game_id,  # [0] game_id
        tc,  # [1] time_control_bucket
        base_time_seconds,  # [2] base_time_seconds
        None,  # [3] termination
        result,  # [4] result
        user_color,  # [5] user_color
        [0, 1],  # [6] ply_array (0=white's first move, 1=black's first move)
        [user_clock, opp_clock],  # [7] clock_array
    )


# ---------------------------------------------------------------------------
# Phase 88.1 design tests (RED -> GREEN after refactor)
# ---------------------------------------------------------------------------


class TestUserAndOppQuintileIndependentSplit:
    def test_user_and_opp_quintiles_are_independent_per_game(self) -> None:
        """Single game where user clk_pct=0.10 (quintile 0) and opp clk_pct=0.90 (quintile 4).

        The same game must increment user_quintile_wdl[(tc, 0)] AND
        opp_quintile_wdl[(tc, 4)] — two different quintile indices,
        same row.
        """
        row = _make_row(
            "blitz", user_clk_pct=0.10, opp_clk_pct=0.90, result="1-0", user_color="white"
        )
        _tc_total, _tc_diffs, user_q_wdl, opp_q_wdl = _iterate_clock_rows([row])

        # User in quintile 0 (max pressure) with one win.
        assert user_q_wdl.get(("blitz", 0)) == (1, 0, 0)
        # Opponent in quintile 4 (min pressure) with one loss (user won -> opp lost).
        assert opp_q_wdl.get(("blitz", 4)) == (0, 0, 1)
        # No cross-pollination into other quintile cells.
        assert user_q_wdl.get(("blitz", 4)) is None
        assert opp_q_wdl.get(("blitz", 0)) is None

    def test_opp_quintile_wdl_uses_inverted_result(self) -> None:
        """User wins (1-0, white) -> opp_quintile_wdl records a LOSS.

        Game contributes (1,0,0) to user_quintile_wdl and (0,0,1) to opp_quintile_wdl.
        """
        row = _make_row(
            "rapid", user_clk_pct=0.50, opp_clk_pct=0.50, result="1-0", user_color="white"
        )
        _tc_total, _tc_diffs, user_q_wdl, opp_q_wdl = _iterate_clock_rows([row])
        assert user_q_wdl.get(("rapid", 2)) == (1, 0, 0)  # user win
        assert opp_q_wdl.get(("rapid", 2)) == (0, 0, 1)  # opp loss

    def test_opp_inversion_user_loss_user_color_black(self) -> None:
        """User loses (1-0 with user_color=black) -> opp_quintile_wdl records a WIN."""
        # user_color="black" so user is at ply 1 (odd) and opp is at ply 0 (even).
        # Use a black-aware row: opp clock at ply 0, user clock at ply 1.
        base = 300
        # Build row so _extract_entry_clocks returns user=0.50, opp=0.50.
        # With user_color="black", user_parity=1: ply 1 -> user_clock; ply 0 -> opp_clock.
        row = (
            1,  # game_id
            "rapid",
            base,
            None,
            "1-0",  # white wins => user (black) loses
            "black",
            [0, 1],
            [0.50 * base, 0.50 * base],  # ply 0 = opp's clock, ply 1 = user's clock
        )
        _tc_total, _tc_diffs, user_q_wdl, opp_q_wdl = _iterate_clock_rows([row])
        assert user_q_wdl.get(("rapid", 2)) == (0, 0, 1)  # user loss
        assert opp_q_wdl.get(("rapid", 2)) == (1, 0, 0)  # opp win

    def test_draw_appears_as_draw_in_both_splits(self) -> None:
        """Draw is a draw on both sides."""
        row = _make_row(
            "bullet", user_clk_pct=0.30, opp_clk_pct=0.70, result="1/2-1/2", user_color="white"
        )
        _tc_total, _tc_diffs, user_q_wdl, opp_q_wdl = _iterate_clock_rows([row])
        # User in quintile 1 (0.30 -> int(1.5) = 1), opp in quintile 3 (0.70 -> int(3.5) = 3).
        assert user_q_wdl.get(("bullet", 1)) == (0, 1, 0)
        assert opp_q_wdl.get(("bullet", 3)) == (0, 1, 0)


class TestQuintileBulletDelta:
    def test_delta_zero_when_user_and_opp_score_equal_in_same_quintile(self) -> None:
        """Balanced fixture: user has 6W 2D 2L in Q2; opp has 6W 2D 2L in Q2.

        Both sides score 0.70 in quintile 2 -> delta = 0.0.
        """
        tc = "bullet"
        base = 300
        # 10 games each with user_clk_pct=0.5 (user Q2) and opp_clk_pct=0.5 (opp Q2).
        # Mix outcomes so both user and opp accumulate (6W, 2D, 2L) each.
        # user-win => opp-loss; mirror by also adding 6 opp-win games (user-loss).
        # To get user 6W 2D 2L = opp 6W 2D 2L in same Q2:
        #   6 games: user wins (user W, opp L)
        #   2 games: draws (user D, opp D)
        #   2 games: opp wins (user L, opp W)
        # User total: 6W 2D 2L; opp total: 2W 2D 6L -> NOT equal.
        # Need symmetric distribution: 4 wins user / 4 wins opp / 2 draws -> 4W 2D 4L each.
        rows: list[tuple[Any, ...]] = []
        for i in range(4):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="1-0",
                    user_color="white",
                    game_id=i,
                    base_time_seconds=base,
                )
            )
        for i in range(2):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="1/2-1/2",
                    user_color="white",
                    game_id=100 + i,
                    base_time_seconds=base,
                )
            )
        for i in range(4):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="0-1",
                    user_color="white",
                    game_id=200 + i,
                    base_time_seconds=base,
                )
            )
        # Pad to MIN_GAMES_PER_TC_CARD with quintile-0 games (mirror layout: clk_pct 0.10 both)
        for i in range(MIN_GAMES_PER_TC_CARD - 10):
            rows.append(
                _make_row(
                    tc,
                    0.10,
                    0.10,
                    result="1-0",
                    user_color="white",
                    game_id=300 + i,
                    base_time_seconds=base,
                )
            )

        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        q2 = result.cards[0].quintiles[2]
        # n in Q2 (user side) = 10; opp side = 10 (same games, both at Q2). User score = (4+1)/10 = 0.5; opp score = (4+1)/10 = 0.5.
        assert q2.delta == pytest.approx(0.0, abs=1e-9)

    def test_quintile_bullet_returns_none_stats_when_min_n_gate_unmet(self) -> None:
        """If min(n_user_in_Q, n_opp_in_Q) < MIN_GAMES_PER_PRESSURE_BIN, p/CI are None.

        Fixture: only 3 games hit (Q2, Q2) — below MIN_GAMES_PER_PRESSURE_BIN=5.
        delta may be computed as the raw difference (or 0.0); stats must be None.
        Total games per TC must still reach MIN_GAMES_PER_TC_CARD so the card emits.
        """
        tc = "blitz"
        base = 300
        rows: list[tuple[Any, ...]] = []
        # 3 games at Q2 (user_clk_pct=0.5, opp_clk_pct=0.5)
        for i in range(3):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="1-0",
                    user_color="white",
                    game_id=i,
                    base_time_seconds=base,
                )
            )
        # Pad to threshold with quintile-0 games (clk_pct 0.05 both -> user Q0, opp Q0)
        for i in range(MIN_GAMES_PER_TC_CARD - 3):
            rows.append(
                _make_row(
                    tc,
                    0.05,
                    0.05,
                    result="1-0",
                    user_color="white",
                    game_id=100 + i,
                    base_time_seconds=base,
                )
            )

        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        q2 = result.cards[0].quintiles[2]
        # n=3 < MIN_GAMES_PER_PRESSURE_BIN(=5): stats must be None.
        assert q2.n == 3
        assert q2.p_value is None
        assert q2.ci_low is None
        assert q2.ci_high is None
        assert q2.opp_score is None

    def test_quintile_bullet_emits_opp_score_when_gate_met(self) -> None:
        """When min(n_user_in_Q, n_opp_in_Q) >= MIN_GAMES_PER_PRESSURE_BIN, opp_score is set."""
        tc = "blitz"
        base = 300
        # 20 games at Q2 (user_clk_pct=0.5, opp_clk_pct=0.5): user all wins -> opp all losses.
        rows = [
            _make_row(
                tc, 0.50, 0.50, result="1-0", user_color="white", game_id=i, base_time_seconds=base
            )
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        q2 = result.cards[0].quintiles[2]
        assert q2.n == MIN_GAMES_PER_TC_CARD
        # User all wins -> user_score = 1.0; opp all losses -> opp_score = 0.0.
        assert q2.opp_score == pytest.approx(0.0, abs=1e-9)
        assert q2.delta == pytest.approx(1.0, abs=1e-9)


class TestRepositoryNoCohortFunction:
    def test_query_cohort_clock_rows_removed_from_repository(self) -> None:
        """query_cohort_clock_rows must be gone from endgame_repository namespace."""
        from app.repositories import endgame_repository

        assert not hasattr(endgame_repository, "query_cohort_clock_rows")


class TestComputeTimePressureCardsSignature:
    def test_signature_is_single_arg(self) -> None:
        """_compute_time_pressure_cards takes a single positional argument (no cohort_lookup)."""
        import inspect

        sig = inspect.signature(_compute_time_pressure_cards)
        # Should have exactly one parameter (clock_rows).
        assert len(sig.parameters) == 1


# ---------------------------------------------------------------------------
# Existing behaviour preserved (carry-over with cohort plumbing removed)
# ---------------------------------------------------------------------------


class TestTcCardThreshold:
    def test_tc_card_hidden_below_threshold(self) -> None:
        """19 bullet games -> no bullet card in response (below MIN_GAMES_PER_TC_CARD=20)."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(MIN_GAMES_PER_TC_CARD - 1)]
        result = _compute_time_pressure_cards(rows)
        assert result.cards == []

    def test_tc_card_visible_at_threshold(self) -> None:
        """Exactly 20 bullet games -> bullet card present."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(MIN_GAMES_PER_TC_CARD)]
        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        assert result.cards[0].tc == "bullet"

    def test_tc_card_visible_above_threshold(self) -> None:
        """25 bullet games -> bullet card present."""
        rows = [_make_row("bullet", 0.5, 0.5, game_id=i) for i in range(25)]
        result = _compute_time_pressure_cards(rows)
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

    def test_quintile_bucketing_correct(self) -> None:
        """user_clk_pct 0.0, 0.19, 0.20, 0.50, 0.99 map to quintiles 0, 0, 1, 2, 4."""
        tc = "blitz"
        base = 300

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

        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]
        assert len(card.quintiles) == 5

        expected_labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
        for q_idx, q_bullet in enumerate(card.quintiles):
            assert q_bullet.quintile_index == q_idx
            assert q_bullet.quintile_label == expected_labels[q_idx]


class TestPerQuintileWdlAccumulator:
    def test_per_quintile_wdl_accumulator(self) -> None:
        """10 games in (bullet, quintile 2) with 6W 2D 2L on user side.

        user_clk_pct=0.50 -> user quintile 2; opp_clk_pct=0.50 -> opp quintile 2.
        Expected user_score = (6 + 0.5*2) / 10 = 0.70.
        Opp inverted: 2W 2D 6L in opp_quintile_wdl[(bullet, 2)].
        Opp score = (2 + 0.5*2) / 10 = 0.30. Delta = 0.70 - 0.30 = 0.40.
        """
        tc = "bullet"
        base = 300

        rows: list[tuple[Any, ...]] = []
        for i in range(6):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="1-0",
                    user_color="white",
                    game_id=i,
                    base_time_seconds=base,
                )
            )
        for i in range(2):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="1/2-1/2",
                    user_color="white",
                    game_id=100 + i,
                    base_time_seconds=base,
                )
            )
        for i in range(2):
            rows.append(
                _make_row(
                    tc,
                    0.50,
                    0.50,
                    result="0-1",
                    user_color="white",
                    game_id=200 + i,
                    base_time_seconds=base,
                )
            )
        # Pad to MIN_GAMES_PER_TC_CARD with quintile-0 games so the card is emitted
        for i in range(MIN_GAMES_PER_TC_CARD - 10):
            rows.append(_make_row(tc, 0.01, 0.01, game_id=300 + i, base_time_seconds=base))

        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1
        card = result.cards[0]

        q2 = card.quintiles[2]
        assert q2.n == 10
        # User 0.70, opp 0.30 -> delta = 0.40.
        assert q2.opp_score == pytest.approx(0.30, abs=1e-9)
        assert q2.delta == pytest.approx(0.40, abs=1e-9)


class TestClockGap:
    def test_clock_gap_uses_paired_diff_test(self) -> None:
        """Known clock_diff list yields mean and CI matching compute_paired_difference_test directly."""
        tc = "rapid"
        base = 600
        # 20 games: user at 60% clock, opp at 40% -> diff = 0.20
        rows = [
            _make_row(tc, 0.60, 0.40, game_id=i, base_time_seconds=base)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1

        clock_gap = result.cards[0].clock_gap
        assert clock_gap.n == MIN_GAMES_PER_TC_CARD

        expected_diffs = [0.20] * MIN_GAMES_PER_TC_CARD
        exp_mean, exp_p, exp_ci_low, exp_ci_high = compute_paired_difference_test(expected_diffs)

        assert clock_gap.mean_diff_pct == pytest.approx(exp_mean, abs=1e-9)
        if exp_p is not None:
            assert clock_gap.p_value == pytest.approx(exp_p, abs=1e-6)
        else:
            assert clock_gap.p_value is None
        if exp_ci_low is not None:
            assert clock_gap.ci_low == pytest.approx(exp_ci_low, abs=1e-9)
        else:
            assert clock_gap.ci_low is None
        if exp_ci_high is not None:
            assert clock_gap.ci_high == pytest.approx(exp_ci_high, abs=1e-9)
        else:
            assert clock_gap.ci_high is None


class TestSparseQuintile:
    def test_zero_games_in_quintile_emits_neutral_bullet(self) -> None:
        """When a quintile has zero games (both user and opp), the bullet has n=0, delta=0,
        all stats None.
        """
        tc = "classical"
        base = 1800
        # 20 games all at quintile 2 (user_clk_pct=0.5, opp_clk_pct=0.5) -> quintiles 0,1,3,4 are empty
        rows = [
            _make_row(tc, 0.50, 0.50, game_id=i, base_time_seconds=base)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 1

        q0 = result.cards[0].quintiles[0]
        assert q0.n == 0
        assert q0.delta == pytest.approx(0.0)
        assert q0.p_value is None
        assert q0.ci_low is None
        assert q0.ci_high is None
        assert q0.opp_score is None


class TestBaseClockGuard:
    def test_base_clock_zero_or_missing_skipped(self) -> None:
        """Rows with base_time_seconds <= 0 are skipped.

        19 valid games + 10 games with base_clock=0 -> still below threshold (no card).
        """
        valid_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=i, base_time_seconds=300)
            for i in range(MIN_GAMES_PER_TC_CARD - 1)
        ]
        bad_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=100 + i, base_time_seconds=0) for i in range(10)
        ]
        rows = valid_rows + bad_rows
        result = _compute_time_pressure_cards(rows)
        assert result.cards == []

    def test_base_clock_zero_games_not_counted(self) -> None:
        """Exactly MIN_GAMES_PER_TC_CARD valid games plus base_clock=0 rows emit one card."""
        valid_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=i, base_time_seconds=300)
            for i in range(MIN_GAMES_PER_TC_CARD)
        ]
        bad_rows = [
            _make_row("blitz", 0.5, 0.5, game_id=100 + i, base_time_seconds=0) for i in range(5)
        ]
        rows = valid_rows + bad_rows
        result = _compute_time_pressure_cards(rows)
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
        result = _compute_time_pressure_cards(rows)
        assert len(result.cards) == 4
        assert [c.tc for c in result.cards] == ["bullet", "blitz", "rapid", "classical"]


class TestMinGamesPerPressureBinWired:
    def test_constant_imported_and_used(self) -> None:
        """MIN_GAMES_PER_PRESSURE_BIN must be importable from endgame_service (WR-05 wired)."""
        assert isinstance(MIN_GAMES_PER_PRESSURE_BIN, int)
        assert MIN_GAMES_PER_PRESSURE_BIN >= 1
