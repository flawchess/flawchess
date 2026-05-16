"""Tests for endgame service: classify_endgame_class, _aggregate_endgame_stats, and service entry points.

Tests cover:
- classify_endgame_class: maps material_signature strings to endgame category names
- _aggregate_endgame_stats: aggregates raw per-(game, class) rows into EndgameCategoryStats list
- get_endgame_stats / get_endgame_games: smoke tests to catch wiring bugs (typos, import errors)
- get_endgame_performance: WDL comparison + gauge values
- get_endgame_timeline: rolling-window time series
- _extract_entry_clocks: ply-parity clock extraction (Phase 54)
- _compute_clock_pressure: time pressure aggregation by time control (Phase 54)
"""

import datetime
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import EndgameEloTimelinePoint, EndgameWDLSummary
from app.services.endgame_service import (
    CLOCK_PRESSURE_TIMELINE_WINDOW,
    ENDGAME_ELO_TIMELINE_WINDOW,
    SCORE_GAP_TIMELINE_WINDOW,
    _aggregate_endgame_stats,
    _build_bucket_series,
    _classify_endgame_bucket,
    _compute_clock_pressure,
    _compute_clock_pressure_timeline,
    _compute_endgame_elo_weekly_series,
    _compute_rolling_series,
    _compute_score_gap_material,
    _compute_score_gap_timeline,
    _compute_span_gap,
    _compute_time_pressure_chart,
    _compute_weekly_rolling_series,
    _conversion_elo_from_skill,
    _extract_entry_clocks,
    _get_endgame_performance_from_rows,
    _wdl_to_score,
    classify_endgame_class,
    get_endgame_games,
    get_endgame_overview,
    get_endgame_performance,
    get_endgame_stats,
    get_endgame_timeline,
)


class _FakeRow(NamedTuple):
    """Lightweight stand-in for a SQLAlchemy Row used by endgame service tests.

    Mirrors the labeled columns produced by query_endgame_entry_rows and
    query_endgame_bucket_rows so _compute_score_gap_material can access
    .game_id / .endgame_class / .result / .user_color / .eval_cp / .eval_mate
    directly (REFAC-02 cutover: eval replaces material_imbalance proxy).
    """

    game_id: int
    endgame_class: int
    result: str
    user_color: str
    eval_cp: Any
    eval_mate: Any


class TestClassifyEndgameClass:
    """Unit tests for endgame category classification from material_signature."""

    def test_rook_endgame(self):
        """KR vs KR — pure rook endgame, no minor pieces or pawns."""
        assert classify_endgame_class("KR_KR") == "rook"

    def test_rook_with_pawns(self):
        """KR+pawns vs KR+pawn — still rook endgame (rook present, no minor pieces)."""
        assert classify_endgame_class("KRPP_KRP") == "rook"

    def test_minor_piece_endgame(self):
        """KB vs KN — bishop vs knight, no rook or queen."""
        assert classify_endgame_class("KB_KN") == "minor_piece"

    def test_pawn_endgame(self):
        """KPP vs KP — pure pawn endgame, no pieces except kings."""
        assert classify_endgame_class("KPP_KP") == "pawn"

    def test_queen_endgame(self):
        """KQ vs KQ — pure queen endgame, no rook or minor pieces."""
        assert classify_endgame_class("KQ_KQ") == "queen"

    def test_mixed_rook_and_minor_with_pawns(self):
        """KRBP vs KRP — rook + minor + pawns = mixed."""
        assert classify_endgame_class("KRBP_KRP") == "mixed"

    def test_mixed_queen_and_rook_with_pawns(self):
        """KQRP vs KQP — queen + rook + pawns = mixed."""
        assert classify_endgame_class("KQRP_KQP") == "mixed"

    def test_pawnless_bare_kings(self):
        """K vs K — bare kings, pawnless endgame."""
        assert classify_endgame_class("K_K") == "pawnless"

    def test_pawnless_rook_and_minor(self):
        """KRB vs KR — rook + minor, no pawns = pawnless."""
        assert classify_endgame_class("KRB_KR") == "pawnless"

    def test_pawnless_queen_and_rook(self):
        """KQR vs KQ — queen + rook, no pawns = pawnless."""
        assert classify_endgame_class("KQR_KQ") == "pawnless"

    def test_pawnless_rook_and_minor_2(self):
        """KRN vs KR — two piece families, no pawns = pawnless."""
        assert classify_endgame_class("KRN_KR") == "pawnless"

    def test_minor_piece_with_pawns_is_minor(self):
        """KBPP vs KNP — minor piece + pawns = minor_piece (pawns don't create a mixed endgame)."""
        assert classify_endgame_class("KBPP_KNP") == "minor_piece"

    def test_rook_with_pawns_is_rook(self):
        """KRPP vs KRP — rook + pawns = rook (pawns alongside single piece family)."""
        assert classify_endgame_class("KRPP_KRP") == "rook"

    def test_queen_with_pawns_is_queen(self):
        """KQPP vs KQP — queen + pawns = queen."""
        assert classify_endgame_class("KQPP_KQP") == "queen"


class TestClassifyEndgameBucket:
    """Unit tests for _classify_endgame_bucket helper (REFAC-02).

    Covers the eval_cp threshold and eval_mate sign semantics, user-color sign flip,
    and NULL eval fallback to parity.
    """

    def test_white_positive_cp_above_threshold_is_conversion(self):
        """White user with eval_cp=150 (above +100 threshold) is conversion."""
        assert (
            _classify_endgame_bucket(eval_cp=150, eval_mate=None, user_color="white")
            == "conversion"
        )

    def test_black_user_with_white_negative_cp_is_conversion(self):
        """Black user with white-perspective eval_cp=-300 (black is +300) is conversion."""
        assert (
            _classify_endgame_bucket(eval_cp=-300, eval_mate=None, user_color="black")
            == "conversion"
        )

    def test_user_mate_for_white_is_conversion(self):
        """White user with eval_mate=3 (white mates in 3) is conversion."""
        assert (
            _classify_endgame_bucket(eval_cp=None, eval_mate=3, user_color="white") == "conversion"
        )

    def test_user_being_mated_is_recovery(self):
        """White user with eval_mate=-3 (white is being mated) is recovery."""
        assert (
            _classify_endgame_bucket(eval_cp=None, eval_mate=-3, user_color="white") == "recovery"
        )

    def test_below_threshold_is_parity(self):
        """White user with eval_cp=50 (below +100 threshold) is parity."""
        assert _classify_endgame_bucket(eval_cp=50, eval_mate=None, user_color="white") == "parity"

    def test_null_eval_is_parity(self):
        """NULL eval (engine error / not yet backfilled) defaults to parity."""
        assert (
            _classify_endgame_bucket(eval_cp=None, eval_mate=None, user_color="white") == "parity"
        )

    def test_white_negative_cp_is_recovery(self):
        """White user with eval_cp=-200 (below -100 threshold) is recovery."""
        assert (
            _classify_endgame_bucket(eval_cp=-200, eval_mate=None, user_color="white") == "recovery"
        )

    def test_threshold_boundary_inclusive_at_100(self):
        """eval_cp == +100 (exactly at threshold) is conversion (>= 100)."""
        assert (
            _classify_endgame_bucket(eval_cp=100, eval_mate=None, user_color="white")
            == "conversion"
        )

    def test_threshold_boundary_exclusive_at_99(self):
        """eval_cp == +99 (just below threshold) is parity (< 100)."""
        assert _classify_endgame_bucket(eval_cp=99, eval_mate=None, user_color="white") == "parity"

    def test_black_user_mate_for_black_is_conversion(self):
        """Black user with eval_mate=-2 (black mates in 2 from white POV) is conversion."""
        # eval_mate=-2 means white is being mated; from black's perspective this is a win
        assert (
            _classify_endgame_bucket(eval_cp=None, eval_mate=-2, user_color="black") == "conversion"
        )

    def test_black_user_being_mated_is_recovery(self):
        """Black user with eval_mate=5 (white mates in 5 from white POV) is recovery."""
        # eval_mate=5 means white mates in 5; from black's perspective this is a deficit
        assert _classify_endgame_bucket(eval_cp=None, eval_mate=5, user_color="black") == "recovery"


class TestAggregateEndgameStats:
    """Unit tests for endgame stats aggregation logic.

    Rows use the shape: (game_id, endgame_class_int, result, user_color, eval_cp, eval_mate)
    where endgame_class_int is 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    eval_cp and eval_mate are white-perspective Stockfish eval at the span-entry ply (REFAC-02);
    classification uses _classify_endgame_bucket(eval_cp, eval_mate, user_color).
    """

    def test_empty_input_returns_empty(self):
        """Empty row list produces empty output list."""
        result, _ = _aggregate_endgame_stats([])
        assert result == []

    def test_sorted_by_total_descending(self):
        """D-05: Categories sorted by game count descending."""
        # 1 rook game (endgame_class_int=1), 3 pawn games (endgame_class_int=3)
        rows = [
            # 1 rook game (win) — conversion eval
            (1, 1, "1-0", "white", 100, None),
            # 3 pawn games (2 wins, 1 loss)
            (2, 3, "1-0", "white", 50, None),
            (3, 3, "1-0", "white", 0, None),
            (4, 3, "0-1", "white", -100, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        # Pawn category has 3 games, rook has 1 — pawn should come first
        assert len(result) >= 2
        # Verify sorting is descending by total
        totals = [cat.total for cat in result]
        assert totals == sorted(totals, reverse=True)

    def test_win_draw_loss_percentages(self):
        """Percentages computed correctly for 1W/1D/1L split."""
        rows = [
            (1, 1, "1-0", "white", 0, None),  # rook win (endgame_class_int=1)
            (2, 1, "1/2-1/2", "white", 0, None),  # rook draw
            (3, 1, "0-1", "white", 0, None),  # rook loss
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.wins == 1
        assert rook.draws == 1
        assert rook.losses == 1
        assert rook.total == 3
        assert abs(rook.win_pct - 33.3) < 1

    def test_conversion_pct_per_category(self):
        """D-08: Conversion = win rate when user entered endgame with eval >= +100cp."""
        rows = [
            (1, 1, "1-0", "white", 500, None),  # rook, up 500cp, won → converted
            (2, 1, "0-1", "white", 350, None),  # rook, up 350cp, lost → failed conversion
            (
                3,
                1,
                "1/2-1/2",
                "white",
                100,
                None,
            ),  # rook, up 100cp (threshold), draw → draw conversion
            (4, 1, "1-0", "white", -400, None),  # rook, down, won → not a conversion game
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 3 games with eval >= 100cp: 1 win, 1 draw, 1 loss → 33.3% conversion
        assert rook.conversion.conversion_games == 3
        assert rook.conversion.conversion_wins == 1
        assert rook.conversion.conversion_draws == 1
        assert rook.conversion.conversion_losses == 1
        assert abs(rook.conversion.conversion_pct - 33.3) < 0.1

    def test_recovery_pct_per_category(self):
        """D-09: Recovery = draw+win rate when user entered endgame with eval <= -100cp."""
        rows = [
            (1, 1, "1-0", "white", -400, None),  # rook, down 400cp, won → recovery win
            (2, 1, "1/2-1/2", "white", -500, None),  # rook, down 500cp, draw → recovery draw
            (
                3,
                1,
                "0-1",
                "white",
                -100,
                None,
            ),  # rook, down 100cp (threshold), lost → not recovered
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 3 games with eval <= -100cp, 2 saves (win + draw) → 66.7%
        assert rook.conversion.recovery_games == 3
        assert rook.conversion.recovery_wins == 1
        assert rook.conversion.recovery_draws == 1
        assert rook.conversion.recovery_saves == 2
        assert abs(rook.conversion.recovery_pct - 66.7) < 0.1

    def test_no_game_phase_breakdown(self):
        """D-11: Single aggregate per endgame type, no opening/middlegame/endgame sub-breakdown."""
        rows = [
            (1, 1, "1-0", "white", 100, None),  # rook, endgame_class_int=1
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Verify flat structure: conversion/recovery are inline properties, not nested by phase
        assert hasattr(rook, "conversion")
        assert hasattr(rook.conversion, "conversion_pct")
        assert hasattr(rook.conversion, "recovery_pct")
        # No sub-grouping by phase — just one aggregate conversion object
        assert not isinstance(rook.conversion, list)

    def test_multiple_categories_aggregated_correctly(self):
        """Multiple categories are computed independently, not mixed together."""
        rows = [
            (1, 1, "1-0", "white", 0, None),  # rook win (endgame_class_int=1)
            (2, 1, "0-1", "white", 0, None),  # rook loss
            (3, 4, "1-0", "white", 0, None),  # queen win (endgame_class_int=4)
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        queen = next(c for c in result if c.endgame_class == "queen")
        assert rook.total == 2
        assert queen.total == 1
        assert rook.wins == 1
        assert rook.losses == 1
        assert queen.wins == 1

    def test_zero_conversion_games_returns_zero_pct(self):
        """When no games have eval advantage, conversion_pct should be 0 (not a divide-by-zero error)."""
        rows = [
            (1, 1, "1-0", "white", -100, None),  # rook, down, won → recovery only
            (2, 1, "0-1", "white", 0, None),  # rook, equal, lost → neither
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.conversion_pct == 0.0

    def test_zero_recovery_games_returns_zero_pct(self):
        """When no games have eval disadvantage, recovery_pct should be 0."""
        rows = [
            (1, 1, "1-0", "white", 200, None),  # rook, up, won → conversion only
            (2, 1, "0-1", "white", 0, None),  # rook, equal, lost → neither
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.recovery_games == 0
        assert rook.conversion.recovery_pct == 0.0

    def test_multi_class_per_game_in_aggregation(self):
        """A game_id appearing with two different endgame_class_int values contributes to both classes."""
        rows = [
            # Same game (game_id=1) in two classes: rook (1) and pawn (3)
            (1, 1, "1-0", "white", 100, None),  # rook class for game 1
            (1, 3, "1-0", "white", 50, None),  # pawn class for game 1
            # Another game in rook only
            (2, 1, "0-1", "white", 0, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        pawn = next(c for c in result if c.endgame_class == "pawn")
        # Rook class: 2 rows (game 1 + game 2), pawn class: 1 row (game 1)
        assert rook.total == 2
        assert pawn.total == 1
        # Rook: 1 win + 1 loss
        assert rook.wins == 1
        assert rook.losses == 1
        # Pawn: 1 win
        assert pawn.wins == 1

    def test_eval_below_threshold_is_parity_not_conversion(self):
        """eval_cp below +100 threshold is parity — no persistence requirement (REFAC-02 cutover)."""
        rows = [
            # eval_cp=50 → parity (below threshold); eval_cp=150 → conversion
            (1, 1, "1-0", "white", 50, None),
            (2, 1, "1-0", "white", 150, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Only game 2 qualifies for conversion
        assert rook.conversion.conversion_games == 1
        assert rook.conversion.conversion_wins == 1

    def test_null_eval_is_parity_not_counted_for_conv_recov(self):
        """NULL eval (engine not yet backfilled) is parity — not counted for conv/recov."""
        rows = [
            (1, 1, "1-0", "white", None, None),
            (2, 1, "0-1", "white", None, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.recovery_games == 0

    # --- Phase 84: per-type opponent baseline via same-game mirror identity ---

    def test_per_type_opponent_baseline_symmetric_60_40(self):
        """Rook conv 6W/0D/4L (60%) + recov 2W/2D/6L (40% save-rate).

        Mirror identities:
        - opp_conv == 60.0 == recov_losses(6) / recov_games(10) * 100
        - opp_recov == 40.0 == (conv_losses(4) + conv_draws(0)) / conv_games(10) * 100
        """
        rows = []
        game_id = 0
        # 10 conversion rows (eval +150, white): 6 wins, 4 losses, 0 draws.
        for _ in range(6):
            game_id += 1
            rows.append((game_id, 1, "1-0", "white", 150, None))
        for _ in range(4):
            game_id += 1
            rows.append((game_id, 1, "0-1", "white", 150, None))
        # 10 recovery rows (eval -150, white): 2 wins, 2 draws, 6 losses.
        for _ in range(2):
            game_id += 1
            rows.append((game_id, 1, "1-0", "white", -150, None))
        for _ in range(2):
            game_id += 1
            rows.append((game_id, 1, "1/2-1/2", "white", -150, None))
        for _ in range(6):
            game_id += 1
            rows.append((game_id, 1, "0-1", "white", -150, None))

        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 10
        assert rook.conversion.recovery_games == 10
        assert rook.conversion.opponent_conversion_pct == pytest.approx(60.0, abs=0.05)
        assert rook.conversion.opponent_conversion_games == 10
        assert rook.conversion.opponent_recovery_pct == pytest.approx(40.0, abs=0.05)
        assert rook.conversion.opponent_recovery_games == 10

    def test_per_type_opponent_baseline_below_threshold(self):
        """Mirror bucket size below _MIN_OPPONENT_SAMPLE (10) returns None pct, raw games count."""
        rows = []
        game_id = 0
        # 9 conversion rows (all losses).
        for _ in range(9):
            game_id += 1
            rows.append((game_id, 1, "0-1", "white", 200, None))
        # 9 recovery rows (all losses).
        for _ in range(9):
            game_id += 1
            rows.append((game_id, 1, "0-1", "white", -200, None))

        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # opponent_conversion_pct gates on recovery_games (= 9 < 10) → None.
        assert rook.conversion.opponent_conversion_pct is None
        assert rook.conversion.opponent_conversion_games == 9
        # opponent_recovery_pct gates on conversion_games (= 9 < 10) → None.
        assert rook.conversion.opponent_recovery_pct is None
        assert rook.conversion.opponent_recovery_games == 9

    def test_per_type_opponent_baseline_at_threshold_10(self):
        """Mirror bucket size at exactly 10 → pct is non-None (threshold boundary check)."""
        rows = []
        game_id = 0
        for _ in range(10):
            game_id += 1
            rows.append((game_id, 1, "1-0", "white", 200, None))
        for _ in range(10):
            game_id += 1
            rows.append((game_id, 1, "0-1", "white", -200, None))

        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.opponent_conversion_pct is not None
        assert rook.conversion.opponent_conversion_games == 10
        assert rook.conversion.opponent_recovery_pct is not None
        assert rook.conversion.opponent_recovery_games == 10

    def test_per_type_opponent_baseline_zero_sample(self):
        """Zero-sample mirror buckets emit None pct + 0 games and raise no ZeroDivisionError."""
        # Parity-only rows: eval in (-100, +100) → neither conversion nor recovery bucket.
        rows = [
            (1, 1, "1-0", "white", 0, None),
            (2, 1, "0-1", "white", 50, None),
            (3, 1, "1/2-1/2", "white", -50, None),
        ]
        # Must not raise.
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.recovery_games == 0
        assert rook.conversion.opponent_conversion_pct is None
        assert rook.conversion.opponent_recovery_pct is None
        assert rook.conversion.opponent_conversion_games == 0
        assert rook.conversion.opponent_recovery_games == 0

    def test_per_type_opponent_baseline_schema_shape(self):
        """ConversionRecoveryStats exposes the four new fields as REQUIRED."""
        from app.schemas.endgames import ConversionRecoveryStats

        fields = ConversionRecoveryStats.model_fields
        for name in (
            "opponent_conversion_pct",
            "opponent_conversion_games",
            "opponent_recovery_pct",
            "opponent_recovery_games",
        ):
            assert name in fields, f"missing field: {name}"
            assert fields[name].is_required(), f"field {name} must be required"


class TestPerClassScorePValue:
    """Phase 87 follow-up: per-class Wilson score-test p_value vs 50%.

    Drives the per-card Score bullet sig-gating triple in EndgameTypeCard,
    replacing the previous Conv/Recov peer-diff bullets.
    """

    @staticmethod
    def _class_rows(class_int: int, wins: int, draws: int, losses: int) -> list[tuple]:
        """Build parity-bucket rows so they only contribute to WDL (not conv/recov)."""
        rows: list[tuple] = []
        for _ in range(wins):
            rows.append((0, class_int, "1-0", "white", 0, None))
        for _ in range(draws):
            rows.append((0, class_int, "1/2-1/2", "white", 0, None))
        for _ in range(losses):
            rows.append((0, class_int, "0-1", "white", 0, None))
        return [(i + 1, r[1], r[2], r[3], r[4], r[5]) for i, r in enumerate(rows)]

    def test_score_p_value_significant_on_strong_class(self):
        """High-skill synthetic fixture: 30W/5D/5L on rook -> score_p_value < 0.05 and not None."""
        rows = self._class_rows(1, wins=30, draws=5, losses=5)
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.total == 40
        assert rook.score_p_value is not None
        assert rook.score_p_value < 0.05

    def test_score_p_value_gated_below_n_ten(self):
        """total < PVALUE_RELIABILITY_MIN_N=10 -> score_p_value is None."""
        # 5 games total — well below the n=10 gate.
        rows = self._class_rows(1, wins=3, draws=1, losses=1)
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.total == 5
        assert rook.score_p_value is None


class TestComputeSpanGap:
    """Phase 87.1 (SEED-016 D-07): per-span gap helper unit tests.

    Verifies the math contract:
      gap_span = exit_score - ES_sigmoid(entry_eval, user_color)
    Positive = user outperformed Stockfish baseline.
    """

    def test_null_entry_eval_returns_none(self):
        """Both entry eval fields NULL → span excluded from cohort (D-07)."""
        gap = _compute_span_gap(
            entry_eval_cp=None,
            entry_eval_mate=None,
            next_entry_eval_cp=50,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is None

    def test_pure_transitory_span_white(self):
        """Transitory span: exit = ES_sigmoid(next_entry_eval). Hand-computed reference."""
        from app.services.eval_utils import eval_cp_to_expected_score

        entry_cp = 0  # ES_entry ~ 0.5 white perspective
        next_cp = 400  # large white advantage
        es_entry = eval_cp_to_expected_score(entry_cp, "white")
        exit_score = eval_cp_to_expected_score(next_cp, "white")
        expected_gap = exit_score - es_entry  # ~ +0.4 (positive — outperformed)

        gap = _compute_span_gap(
            entry_eval_cp=entry_cp,
            entry_eval_mate=None,
            next_entry_eval_cp=next_cp,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        assert gap == pytest.approx(expected_gap, abs=1e-9)
        # Sign convention: positive = outperformed.
        assert gap > 0

    def test_pure_terminal_span_win(self):
        """Terminal span (both next-evals NULL): exit_score = game-result score (1.0 for win)."""
        from app.services.eval_utils import eval_cp_to_expected_score

        entry_cp = 0
        es_entry = eval_cp_to_expected_score(entry_cp, "white")
        # Terminal win → exit_score = 1.0, gap = 1.0 - 0.5 ≈ +0.5.
        gap = _compute_span_gap(
            entry_eval_cp=entry_cp,
            entry_eval_mate=None,
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        assert gap == pytest.approx(1.0 - es_entry, abs=1e-9)

    def test_pure_terminal_span_draw(self):
        """Terminal draw → exit_score = 0.5 regardless of user_color."""
        gap = _compute_span_gap(
            entry_eval_cp=0,
            entry_eval_mate=None,
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            result="1/2-1/2",
            user_color="black",
        )
        assert gap is not None
        # ES_entry at cp=0 from black perspective is 0.5 — gap ≈ 0.
        assert gap == pytest.approx(0.0, abs=1e-9)

    def test_pure_terminal_span_loss(self):
        """Terminal loss → exit_score = 0.0, gap = -ES_entry (negative — gave back score)."""
        from app.services.eval_utils import eval_cp_to_expected_score

        entry_cp = 300  # white user up
        es_entry = eval_cp_to_expected_score(entry_cp, "white")  # ~ 0.75
        gap = _compute_span_gap(
            entry_eval_cp=entry_cp,
            entry_eval_mate=None,
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            result="0-1",  # white lost
            user_color="white",
        )
        assert gap is not None
        # Expected gap = 0.0 - es_entry (negative).
        assert gap == pytest.approx(-es_entry, abs=1e-9)
        assert gap < 0  # underperformed

    def test_mate_at_entry_uses_mate_helper(self):
        """entry_eval_mate non-NULL → uses eval_mate_to_expected_score (saturates to 1.0/0.0)."""
        # White has forced mate → ES_entry = 1.0 (saturated). Terminal win → exit = 1.0.
        # Gap = 0.0 (already winning, converted as expected).
        gap = _compute_span_gap(
            entry_eval_cp=None,
            entry_eval_mate=5,  # mate in 5, positive = white wins
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        assert gap == pytest.approx(0.0, abs=1e-9)

    def test_mate_at_next_entry_uses_mate_helper(self):
        """Transitory span where next-span eval is mate → uses eval_mate_to_expected_score."""
        from app.services.eval_utils import eval_cp_to_expected_score

        entry_cp = 0  # parity at entry
        es_entry = eval_cp_to_expected_score(entry_cp, "white")
        # Transitory: next eval is mate for white → exit = 1.0.
        gap = _compute_span_gap(
            entry_eval_cp=entry_cp,
            entry_eval_mate=None,
            next_entry_eval_cp=None,
            next_entry_eval_mate=3,  # mate in 3 for white
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        assert gap == pytest.approx(1.0 - es_entry, abs=1e-9)
        assert gap > 0

    def test_mate_takes_precedence_over_cp_at_entry(self):
        """When entry_eval_mate is non-None, it is used even if entry_eval_cp is also set."""
        # Mate-in-2 for white (saturates ES_entry to 1.0) even if cp=50 would say ~0.55.
        # Terminal win → exit=1.0 → gap=0.
        gap = _compute_span_gap(
            entry_eval_cp=50,
            entry_eval_mate=2,
            next_entry_eval_cp=None,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        assert gap == pytest.approx(0.0, abs=1e-9)

    def test_sign_convention_positive_equals_outperformed(self):
        """Anchor test: ES_entry ≈ 0.4 (slight disadvantage), exit ≈ 0.7 → gap ≈ +0.3 NOT −0.3."""
        from app.services.eval_utils import eval_cp_to_expected_score

        # cp values picked so ES_entry < 0.5 < exit_score from white perspective.
        entry_cp = -110  # white slightly worse
        next_cp = 230  # white better at next span entry
        es_entry = eval_cp_to_expected_score(entry_cp, "white")
        exit_score = eval_cp_to_expected_score(next_cp, "white")
        assert es_entry < 0.5
        assert exit_score > 0.5

        gap = _compute_span_gap(
            entry_eval_cp=entry_cp,
            entry_eval_mate=None,
            next_entry_eval_cp=next_cp,
            next_entry_eval_mate=None,
            result="1-0",
            user_color="white",
        )
        assert gap is not None
        # Positive — user outperformed. The plan's acceptance criterion: a
        # synthetic span where ES_entry ~ 0.4 and exit ~ 0.7 yields gap ~ +0.3.
        assert gap > 0
        assert gap == pytest.approx(exit_score - es_entry, abs=1e-9)


class TestAggregateEndgameStatsTypeScoreGap:
    """Phase 87.1 (SEED-016 D-05): integration coverage on the per-class gap fields.

    Builds 8-tuple rows (full prod shape) and asserts the 5 new
    type_achievable_score_gap_* fields are populated according to the helper's
    n-gates and the math contract.
    """

    @staticmethod
    def _gap_row(
        game_id: int,
        endgame_class_int: int,
        result: str,
        user_color: str,
        eval_cp: int | None,
        eval_mate: int | None,
        next_entry_eval_cp: int | None = None,
        next_entry_eval_mate: int | None = None,
    ) -> tuple[Any, ...]:
        """Build an 8-tuple row matching the post-Phase-87.1 repo shape."""
        return (
            game_id,
            endgame_class_int,
            result,
            user_color,
            eval_cp,
            eval_mate,
            next_entry_eval_cp,
            next_entry_eval_mate,
        )

    def test_legacy_6_tuple_rows_still_aggregate(self):
        """6-tuple legacy test fixtures continue to aggregate WDL — gap fields gracefully
        report n=0 / mean=None (no next-span data so all spans look terminal, no NULL-eval).

        Regression guard: confirms the loop-body branch absorbing 6-tuples.
        """
        rows = [
            (1, 1, "1-0", "white", 0, None),  # rook, parity entry
            (2, 1, "0-1", "white", 0, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Aggregation still works.
        assert rook.total == 2
        # Gap fields are populated (terminal-span path: exit_score from game
        # result, ES_entry from cp=0 ≈ 0.5).
        assert rook.type_achievable_score_gap_n == 2
        assert rook.type_achievable_score_gap_mean is not None
        # n < CONFIDENCE_MIN_N=10 → p-value gated to None.
        assert rook.type_achievable_score_gap_p_value is None
        # n >= 2 → CI populated.
        assert rook.type_achievable_score_gap_ci_low is not None
        assert rook.type_achievable_score_gap_ci_high is not None

    def test_all_five_fields_present_on_category(self):
        """The 5 new fields are populated on EndgameCategoryStats per class."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", 0, None, next_entry_eval_cp=400),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert hasattr(rook, "type_achievable_score_gap_mean")
        assert hasattr(rook, "type_achievable_score_gap_n")
        assert hasattr(rook, "type_achievable_score_gap_p_value")
        assert hasattr(rook, "type_achievable_score_gap_ci_low")
        assert hasattr(rook, "type_achievable_score_gap_ci_high")
        # n=1 → mean populated, p/CI all None.
        assert rook.type_achievable_score_gap_n == 1
        assert rook.type_achievable_score_gap_mean is not None
        assert rook.type_achievable_score_gap_p_value is None
        assert rook.type_achievable_score_gap_ci_low is None
        assert rook.type_achievable_score_gap_ci_high is None

    def test_n_zero_when_all_spans_have_null_eval(self):
        """All spans have NULL entry eval → n_gap = 0; mean/p/CI all None."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", None, None, next_entry_eval_cp=100),
            self._gap_row(2, 1, "0-1", "white", None, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.total == 2  # WDL still counts
        assert rook.type_achievable_score_gap_n == 0
        assert rook.type_achievable_score_gap_mean is None
        assert rook.type_achievable_score_gap_p_value is None
        assert rook.type_achievable_score_gap_ci_low is None
        assert rook.type_achievable_score_gap_ci_high is None

    def test_null_eval_spans_excluded_but_others_counted(self):
        """Mixed cohort: 2 spans with NULL entry eval, 3 with real eval → n_gap == 3."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", 0, None),  # terminal, real eval
            self._gap_row(2, 1, "1/2-1/2", "white", 100, None),  # terminal, real eval
            self._gap_row(3, 1, "0-1", "white", -50, None),  # terminal, real eval
            self._gap_row(4, 1, "1-0", "white", None, None),  # NULL eval — excluded
            self._gap_row(5, 1, "0-1", "white", None, None),  # NULL eval — excluded
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.total == 5  # WDL counts all 5
        assert rook.type_achievable_score_gap_n == 3  # only non-NULL-eval spans

    def test_p_value_gated_below_n_ten(self):
        """n < CONFIDENCE_MIN_N=10 → p_value is None even though mean and CI are populated."""
        rows = [self._gap_row(i + 1, 1, "1-0", "white", 0, None) for i in range(5)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.type_achievable_score_gap_n == 5
        assert rook.type_achievable_score_gap_mean is not None
        # Sub-gate cohort: p_value None, but CI populated (n >= 2).
        assert rook.type_achievable_score_gap_p_value is None
        assert rook.type_achievable_score_gap_ci_low is not None
        assert rook.type_achievable_score_gap_ci_high is not None

    def test_p_value_populated_at_n_ten(self):
        """n >= CONFIDENCE_MIN_N=10 → p_value populated; CI populated; mean populated."""
        # 10 spans of mixed outcomes for varied gap values (non-zero variance so se != 0).
        rows = []
        for i in range(5):
            rows.append(self._gap_row(i + 1, 1, "1-0", "white", 50 + 10 * i, None))
        for i in range(5):
            rows.append(self._gap_row(i + 6, 1, "0-1", "white", -50 - 10 * i, None))
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.type_achievable_score_gap_n == 10
        assert rook.type_achievable_score_gap_mean is not None
        assert rook.type_achievable_score_gap_p_value is not None
        assert rook.type_achievable_score_gap_ci_low is not None
        assert rook.type_achievable_score_gap_ci_high is not None

    def test_hand_computed_reference_matches_to_1e_minus_6(self):
        """3-game fixture: mean of per-span gaps matches hand-computed reference."""
        from app.services.eval_utils import eval_cp_to_expected_score

        # Game 1, rook span only: terminal, entry cp=100, result=win.
        # gap1 = 1.0 - ES(100, white)
        # Game 2, rook span only: terminal, entry cp=-200, result=draw.
        # gap2 = 0.5 - ES(-200, white)
        # Game 3, rook span only: transitory followed by terminal next-span eval=300.
        # gap3 = ES(300, white) - ES(0, white)
        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),
            self._gap_row(2, 1, "1/2-1/2", "white", -200, None),
            self._gap_row(3, 1, "1-0", "white", 0, None, next_entry_eval_cp=300),
        ]
        expected_gaps = [
            1.0 - eval_cp_to_expected_score(100, "white"),
            0.5 - eval_cp_to_expected_score(-200, "white"),
            eval_cp_to_expected_score(300, "white") - eval_cp_to_expected_score(0, "white"),
        ]
        expected_mean = sum(expected_gaps) / 3

        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.type_achievable_score_gap_n == 3
        assert rook.type_achievable_score_gap_mean is not None
        assert rook.type_achievable_score_gap_mean == pytest.approx(expected_mean, abs=1e-6)

    def test_per_class_independent_accumulation(self):
        """Two classes accumulate gap vectors independently."""
        rows = [
            # Rook: 2 spans, one transitory + one terminal-win.
            self._gap_row(1, 1, "1-0", "white", 0, None, next_entry_eval_cp=200),
            self._gap_row(2, 1, "1-0", "white", 50, None),
            # Queen: 1 span, terminal-loss.
            self._gap_row(3, 4, "0-1", "white", 100, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        queen = next(c for c in result if c.endgame_class == "queen")
        assert rook.type_achievable_score_gap_n == 2
        assert queen.type_achievable_score_gap_n == 1
        # Queen lost from white-up position → gap is negative (gave back score).
        assert queen.type_achievable_score_gap_mean is not None
        assert queen.type_achievable_score_gap_mean < 0

    def test_mate_at_endpoint_handled_via_helper(self):
        """Mate at next-span entry uses the mate helper (saturates to 1.0)."""
        # Terminal mate-in-N at next-span entry → exit_score = 1.0 (saturated).
        rows = [
            self._gap_row(
                1, 1, "1-0", "white", 0, None, next_entry_eval_cp=None, next_entry_eval_mate=4
            ),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.type_achievable_score_gap_n == 1
        assert rook.type_achievable_score_gap_mean is not None
        # ES_entry at cp=0 ≈ 0.5; exit_score (mate for white) = 1.0; gap ≈ +0.5.
        assert rook.type_achievable_score_gap_mean == pytest.approx(0.5, abs=1e-9)


class TestGetEndgameStatsSmoke:
    """Smoke tests for service entry points — catch wiring bugs like typos and broken imports."""

    @pytest.mark.asyncio
    async def test_get_endgame_stats_returns_empty_for_nonexistent_user(
        self, db_session: AsyncSession
    ):
        """Calling get_endgame_stats with a user that has no games should return empty categories."""
        result = await get_endgame_stats(
            db_session,
            user_id=999999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency=None,
        )
        assert result.categories == []

    @pytest.mark.asyncio
    async def test_get_endgame_games_returns_empty_for_nonexistent_user(
        self, db_session: AsyncSession
    ):
        """Calling get_endgame_games with a user that has no games should return empty."""
        result = await get_endgame_games(
            db_session,
            user_id=999999,
            endgame_class="rook",
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency=None,
            offset=0,
            limit=20,
        )
        assert result.games == []
        assert result.matched_count == 0


# --- Helpers ---


def _dt(days_offset: int) -> datetime.datetime:
    """Return a UTC datetime N days from epoch for use in test rows."""
    return datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(
        days=days_offset
    )


def _row(result: str, user_color: str, days: int = 0):
    """Build a (played_at, result, user_color) row for test use."""
    return (_dt(days), result, user_color)


# --- Phase 32 tests ---


class TestComputeRollingSeries:
    """Unit tests for _compute_rolling_series helper."""

    def test_empty_input_returns_empty(self):
        """Empty rows produce empty series."""
        assert _compute_rolling_series([], window=10) == []

    def test_few_games_filtered_by_min_threshold(self):
        """Games below MIN_GAMES_FOR_TIMELINE produce no data points."""
        rows = [_row("1-0", "white", 0)]
        result = _compute_rolling_series(rows, window=10)
        assert len(result) == 0

    def test_threshold_game_emits_first_point(self):
        """Exactly MIN_GAMES_FOR_TIMELINE games produce one data point."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        rows = [_row("1-0", "white", i) for i in range(n)]
        result = _compute_rolling_series(rows, window=50)
        assert len(result) == 1
        assert result[0]["game_count"] == n
        assert result[0]["win_rate"] == 1.0

    def test_rolling_drops_old_games(self):
        """Window fills up and oldest games drop off, changing win rate."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        # n wins followed by n losses = 2n games with window=n
        # At game n: window is all wins → 100%
        # At game 2n: window is all losses → 0%
        rows = [_row("1-0", "white", i) for i in range(n)]
        rows += [_row("0-1", "white", n + i) for i in range(n)]
        result = _compute_rolling_series(rows, window=n)
        # First emitted point (game n): all wins
        assert result[0]["win_rate"] == 1.0
        assert result[0]["game_count"] == n
        # Last point (game 2n): all losses, old wins dropped
        assert result[-1]["win_rate"] == 0.0
        assert result[-1]["game_count"] == n

    def test_date_formatting(self):
        """Date field is formatted as YYYY-MM-DD string."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        rows = [_row("1-0", "white", i) for i in range(n)]
        result = _compute_rolling_series(rows, window=50)
        # Last date: 2024-01-01 + (n-1) days
        expected = (datetime.datetime(2024, 1, 1) + datetime.timedelta(days=n - 1)).strftime(
            "%Y-%m-%d"
        )
        assert result[-1]["date"] == expected

    def test_draw_does_not_count_as_win(self):
        """Draw games do not count toward win_rate."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        rows = [_row("1/2-1/2", "white", i) for i in range(n)]
        result = _compute_rolling_series(rows, window=50)
        assert result[-1]["win_rate"] == 0.0

    def test_black_win_counted_correctly(self):
        """Black player winning (0-1) should be a win for black."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        # Alternating black wins and losses
        rows = []
        for i in range(n):
            result_str = "0-1" if i % 2 == 0 else "1-0"
            rows.append(_row(result_str, "black", i))
        result = _compute_rolling_series(rows, window=50)
        assert abs(result[-1]["win_rate"] - 0.5) < 1e-4


def _weekly_row(played_at: datetime.datetime, result: str, user_color: str):
    """Build a (played_at, result, user_color) row for weekly-series tests.

    Unannotated return mirrors `_row()` so ty treats the tuple as a structural
    match for `list[Row[Any]]` in the helper signature.
    """
    return (played_at, result, user_color)


class TestComputeWeeklyRollingSeries:
    """Unit tests for _compute_weekly_rolling_series (rolling window sampled weekly)."""

    def test_empty_rows_returns_empty(self):
        assert _compute_weekly_rolling_series([], window=50) == []

    def test_below_min_games_for_timeline_returns_empty(self):
        # Fewer games than MIN_GAMES_FOR_TIMELINE (10) -> no points emitted
        # even though each week's final window has game_count == len(rows).
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        rows = [
            _weekly_row(datetime.datetime(2026, 4, 13) + datetime.timedelta(days=i), "1-0", "white")
            for i in range(MIN_GAMES_FOR_TIMELINE - 1)
        ]
        assert _compute_weekly_rolling_series(rows, window=50) == []

    def test_one_point_per_iso_week_dated_to_monday(self):
        # 15 games across 3 ISO weeks (5 per week). Week 1 only has 5 cumulative
        # games (< MIN_GAMES_FOR_TIMELINE=10) and is dropped. Week 2 reaches 10
        # cumulative, week 3 reaches 15.
        rows = []
        for week_start in (
            datetime.datetime(2026, 4, 6),
            datetime.datetime(2026, 4, 13),
            datetime.datetime(2026, 4, 20),
        ):
            for day in range(5):  # Mon..Fri
                rows.append(_weekly_row(week_start + datetime.timedelta(days=day), "1-0", "white"))

        result = _compute_weekly_rolling_series(rows, window=50)
        assert [pt["date"] for pt in result] == ["2026-04-13", "2026-04-20"]
        assert [pt["game_count"] for pt in result] == [10, 15]

    def test_window_caps_game_count(self):
        # 60 wins spread one-per-day across ~9 ISO weeks; window=50 caps the
        # game_count at 50 once the window fills.
        rows = [
            _weekly_row(datetime.datetime(2026, 3, 2) + datetime.timedelta(days=i), "1-0", "white")
            for i in range(60)
        ]
        result = _compute_weekly_rolling_series(rows, window=50)
        # Last few weeks should report a full window.
        assert result[-1]["game_count"] == 50
        assert result[-1]["win_rate"] == 1.0

    def test_smoothing_across_sparse_weeks(self):
        # This is the regression: a week with 1 loss in isolation should NOT
        # snap win_rate to 0. With a rolling 50-game window, the 49 prior wins
        # keep the rate high even if the current week had only one game.
        rows = [
            _weekly_row(datetime.datetime(2026, 2, 2) + datetime.timedelta(days=i), "1-0", "white")
            for i in range(49)
        ]
        # One isolated loss in a later, otherwise-empty ISO week.
        rows.append(_weekly_row(datetime.datetime(2026, 4, 13), "0-1", "white"))

        result = _compute_weekly_rolling_series(rows, window=50)
        last = result[-1]
        assert last["date"] == "2026-04-13"
        # 49 wins + 1 loss in window -> 0.98, not 0.0.
        assert last["win_rate"] == 0.98
        assert last["game_count"] == 50

    def test_multiple_games_same_week_keep_final_state(self):
        # Week with multiple games only emits the window state after its
        # last game.
        rows = [
            _weekly_row(datetime.datetime(2026, 4, 13), "1-0", "white"),  # win
            _weekly_row(datetime.datetime(2026, 4, 14), "0-1", "white"),  # loss
            _weekly_row(datetime.datetime(2026, 4, 15), "1-0", "white"),  # win
        ]
        # Below MIN_GAMES_FOR_TIMELINE, so no point actually emitted; verify
        # with a lower window that the logic keeps per-week final state via
        # direct inspection at the higher level is not possible here. Instead
        # pad with enough prior wins to clear the threshold.
        prior = [
            _weekly_row(datetime.datetime(2026, 3, 2) + datetime.timedelta(days=i), "1-0", "white")
            for i in range(10)
        ]
        result = _compute_weekly_rolling_series(prior + rows, window=50)
        # Final week entry = after the Wed win -> 12 wins + 1 loss in window.
        last = result[-1]
        assert last["date"] == "2026-04-13"
        assert last["game_count"] == 13
        assert last["win_rate"] == round(12 / 13, 4)


class TestGetEndgamePerformance:
    """Tests for get_endgame_performance service function."""

    def _make_wdl_rows(self, wins: int, draws: int, losses: int, days_start: int = 0):
        """Build rows for a given W/D/L count, white player."""
        rows = []
        d = days_start
        for _ in range(wins):
            rows.append(_row("1-0", "white", d))
            d += 1
        for _ in range(draws):
            rows.append(_row("1/2-1/2", "white", d))
            d += 1
        for _ in range(losses):
            rows.append(_row("0-1", "white", d))
            d += 1
        return rows

    @pytest.mark.asyncio
    async def test_zero_games_returns_all_zeros(self):
        """With no games, all fields should be 0.0 without ZeroDivisionError."""
        with (
            patch(
                "app.services.endgame_service.query_endgame_performance_rows",
                new_callable=AsyncMock,
            ) as mock_perf,
            patch(
                "app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock
            ) as mock_bucket,
        ):
            mock_perf.return_value = ([], [])
            mock_bucket.return_value = []

            result = await get_endgame_performance(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
            )

        assert result.endgame_wdl.total == 0
        assert result.non_endgame_wdl.total == 0
        assert result.endgame_win_rate == 0.0

    @pytest.mark.asyncio
    async def test_wdl_counts_and_percentages(self):
        """3 endgame wins, 1 draw, 1 loss + 2 non-endgame wins, 3 draws, 5 losses."""
        endgame_rows = self._make_wdl_rows(wins=3, draws=1, losses=1)
        non_endgame_rows = self._make_wdl_rows(wins=2, draws=3, losses=5)

        with (
            patch(
                "app.services.endgame_service.query_endgame_performance_rows",
                new_callable=AsyncMock,
            ) as mock_perf,
            patch(
                "app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock
            ) as mock_bucket,
        ):
            mock_perf.return_value = (endgame_rows, non_endgame_rows)
            mock_bucket.return_value = []

            result = await get_endgame_performance(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
            )

        # Endgame WDL
        assert result.endgame_wdl.wins == 3
        assert result.endgame_wdl.draws == 1
        assert result.endgame_wdl.losses == 1
        assert result.endgame_wdl.total == 5
        assert abs(result.endgame_wdl.win_pct - 60.0) < 0.2

        # Non-endgame WDL
        assert result.non_endgame_wdl.wins == 2
        assert result.non_endgame_wdl.draws == 3
        assert result.non_endgame_wdl.losses == 5
        assert result.non_endgame_wdl.total == 10


class TestGetEndgameTimeline:
    """Tests for get_endgame_timeline service function."""

    @pytest.mark.asyncio
    async def test_empty_rows_returns_empty_series(self):
        """With no games, overall and per_type should be empty."""
        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=50,
            )

        assert result.overall == []
        assert result.window == 50
        # All 6 per-type series should exist but be empty
        assert len(result.per_type) == 6
        for series in result.per_type.values():
            assert series == []

    @pytest.mark.asyncio
    async def test_rolling_window_with_known_sequence(self):
        """With window=n and 2n games (n wins then n losses), rolling window drops old games."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        # n wins followed by n losses
        endgame_rows = [_row("1-0", "white", i) for i in range(n)]
        endgame_rows += [_row("0-1", "white", n + i) for i in range(n)]
        non_endgame_rows = [_row("1-0", "white", i) for i in range(n)]

        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = (
                endgame_rows,
                non_endgame_rows,
                {1: [], 2: [], 3: [], 4: [], 5: [], 6: []},
            )

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=n,
            )

        # Find the last endgame point in overall that has endgame data
        endgame_points = [p for p in result.overall if p.endgame_win_rate is not None]
        last = endgame_points[-1]
        assert last.endgame_win_rate is not None
        # Last window is all losses → 0%
        assert last.endgame_win_rate == 0.0
        assert last.endgame_game_count == n

    @pytest.mark.asyncio
    async def test_partial_window_below_threshold_filtered(self):
        """Partial windows below MIN_GAMES_FOR_TIMELINE produce no data points."""
        endgame_rows = [_row("1-0", "white", 0), _row("1-0", "white", 1)]

        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = (
                endgame_rows,
                [],
                {1: [], 2: [], 3: [], 4: [], 5: [], 6: []},
            )

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=50,
            )

        # 2 games < MIN_GAMES_FOR_TIMELINE → no data points emitted
        assert result.overall == []

    @pytest.mark.asyncio
    async def test_date_merge_both_series_present(self):
        """Overall series merges dates from both endgame and non-endgame rows."""
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE

        n = MIN_GAMES_FOR_TIMELINE
        # Seed n endgame games and n non-endgame games on distinct date ranges
        endgame_rows = [_row("1-0", "white", i) for i in range(n)]
        non_endgame_rows = [_row("0-1", "white", n + i) for i in range(n)]

        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = (
                endgame_rows,
                non_endgame_rows,
                {1: [], 2: [], 3: [], 4: [], 5: [], 6: []},
            )

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=50,
            )

        # Both series emit points starting at game n
        assert len(result.overall) >= 2
        # First overall point should have endgame data
        first = result.overall[0]
        assert first.endgame_win_rate is not None

        # Last overall point should have non-endgame data
        last = result.overall[-1]
        assert last.non_endgame_win_rate is not None
        assert last.endgame_win_rate is not None  # carries forward

    @pytest.mark.asyncio
    async def test_per_type_keys_are_endgame_class_strings(self):
        """per_type keys should be EndgameClass strings (rook, minor_piece, etc.), not integers."""
        # Rolling-window-sampled-weekly per-type: need MIN_GAMES_FOR_TIMELINE (10)
        # games in the rolling window before a weekly point is emitted. 10 rook
        # wins in a single ISO week (Mon 2026-04-13) clears the threshold.
        rook_rows = [
            (
                datetime.datetime(2026, 4, 13, hour=h, tzinfo=datetime.timezone.utc),
                "1-0",
                "white",
            )
            for h in range(10)
        ]

        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: rook_rows, 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=50,
            )

        assert "rook" in result.per_type
        assert "minor_piece" in result.per_type
        assert "pawn" in result.per_type
        assert "queen" in result.per_type
        assert "mixed" in result.per_type
        assert "pawnless" in result.per_type
        # Rook series should have one weekly point (10 games clear MIN_GAMES_FOR_TIMELINE).
        assert len(result.per_type["rook"]) == 1
        assert result.per_type["rook"][0].win_rate == 1.0
        assert result.per_type["rook"][0].date == "2026-04-13"  # Monday of the ISO week
        assert result.per_type["rook"][0].game_count == 10

    @pytest.mark.asyncio
    async def test_window_parameter_reflected_in_response(self):
        """window field in response matches the requested window parameter."""
        with patch(
            "app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock
        ) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                recency=None,
                rated=None,
                opponent_type="human",
                window=25,
            )

        assert result.window == 25


class TestGetEndgamePerformanceSmoke:
    """Smoke tests for performance/timeline service entry points with real DB."""

    @pytest.mark.asyncio
    async def test_get_endgame_performance_returns_zeros_for_nonexistent_user(
        self, db_session: AsyncSession
    ):
        """Calling get_endgame_performance with no data should return all-zero response."""
        result = await get_endgame_performance(
            db_session,
            user_id=999999,
            time_control=None,
            platform=None,
            recency=None,
            rated=None,
            opponent_type="human",
        )
        assert result.endgame_wdl.total == 0
        assert result.non_endgame_wdl.total == 0

    @pytest.mark.asyncio
    async def test_get_endgame_timeline_returns_empty_for_nonexistent_user(
        self, db_session: AsyncSession
    ):
        """Calling get_endgame_timeline with no data should return empty series."""
        result = await get_endgame_timeline(
            db_session,
            user_id=999999,
            time_control=None,
            platform=None,
            recency=None,
            rated=None,
            opponent_type="human",
        )
        assert result.overall == []
        assert result.window == 50


class TestGetEndgameOverview:
    """Tests for get_endgame_overview service function.

    get_endgame_overview was refactored in Phase 53 to fetch entry_rows once and
    call repository functions directly (query_endgame_entry_rows, query_endgame_performance_rows,
    count_filtered_games) instead of delegating to get_endgame_stats and get_endgame_performance.
    The timeline functions are still called as before.
    """

    @pytest.mark.asyncio
    async def test_overview_composes_all_five_payloads(self):
        """get_endgame_overview assembles stats, performance, timeline, score_gap_material, clock_pressure."""
        from app.schemas.endgames import EndgameEloTimelineResponse, EndgameTimelineResponse

        with (
            patch(
                "app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock
            ) as mock_entry,
            patch(
                "app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock
            ) as mock_bucket,
            patch(
                "app.services.endgame_service.query_endgame_performance_rows",
                new_callable=AsyncMock,
            ) as mock_perf_rows,
            patch(
                "app.services.endgame_service.count_filtered_games", new_callable=AsyncMock
            ) as mock_count,
            patch(
                "app.services.endgame_service.count_endgame_games", new_callable=AsyncMock
            ) as mock_eg_count,
            patch(
                "app.services.endgame_service.get_endgame_timeline", new_callable=AsyncMock
            ) as mock_timeline,
            patch(
                "app.services.endgame_service.query_clock_stats_rows", new_callable=AsyncMock
            ) as mock_clock,
            patch(
                "app.services.endgame_service.get_endgame_elo_timeline", new_callable=AsyncMock
            ) as mock_elo_timeline,
        ):
            mock_entry.return_value = []
            mock_bucket.return_value = []
            mock_perf_rows.return_value = ([], [])
            mock_count.return_value = 0
            mock_eg_count.return_value = 0
            mock_timeline.return_value = EndgameTimelineResponse(overall=[], per_type={}, window=50)
            mock_clock.return_value = []
            mock_elo_timeline.return_value = EndgameEloTimelineResponse(
                combos=[], timeline_window=100
            )

            result = await get_endgame_overview(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                rated=None,
                opponent_type="human",
                recency=None,
                window=50,
            )

        # Repository functions called once each
        mock_entry.assert_called_once()
        mock_bucket.assert_called_once()
        mock_perf_rows.assert_called_once()
        mock_count.assert_called_once()
        mock_eg_count.assert_called_once()
        mock_timeline.assert_called_once()
        mock_clock.assert_called_once()
        mock_elo_timeline.assert_called_once()

        # All sub-payloads must be present
        assert result.stats is not None
        assert result.performance is not None
        assert result.timeline is not None
        assert result.score_gap_material is not None
        assert result.clock_pressure is not None
        assert result.clock_pressure.rows == []
        assert result.conversion_elo_timeline is not None
        assert result.conversion_elo_timeline.combos == []
        assert result.conversion_elo_timeline.timeline_window == 100

    @pytest.mark.asyncio
    async def test_overview_passes_window_to_timeline(self):
        """The window parameter must be forwarded to get_endgame_timeline."""
        from app.schemas.endgames import EndgameEloTimelineResponse, EndgameTimelineResponse

        with (
            patch(
                "app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock
            ) as mock_entry,
            patch(
                "app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock
            ) as mock_bucket,
            patch(
                "app.services.endgame_service.query_endgame_performance_rows",
                new_callable=AsyncMock,
            ) as mock_perf_rows,
            patch(
                "app.services.endgame_service.count_filtered_games", new_callable=AsyncMock
            ) as mock_count,
            patch("app.services.endgame_service.count_endgame_games", new_callable=AsyncMock),
            patch(
                "app.services.endgame_service.get_endgame_timeline", new_callable=AsyncMock
            ) as mock_timeline,
            patch(
                "app.services.endgame_service.query_clock_stats_rows", new_callable=AsyncMock
            ) as mock_clock,
            patch(
                "app.services.endgame_service.get_endgame_elo_timeline", new_callable=AsyncMock
            ) as mock_elo_timeline,
        ):
            mock_entry.return_value = []
            mock_bucket.return_value = []
            mock_perf_rows.return_value = ([], [])
            mock_count.return_value = 0
            mock_timeline.return_value = EndgameTimelineResponse(overall=[], per_type={}, window=75)
            mock_clock.return_value = []
            mock_elo_timeline.return_value = EndgameEloTimelineResponse(
                combos=[], timeline_window=100
            )

            await get_endgame_overview(
                AsyncMock(),
                user_id=1,
                time_control=None,
                platform=None,
                rated=None,
                opponent_type="human",
                recency=None,
                window=75,
            )

        # Timeline function must receive window=75
        _, timeline_kwargs = mock_timeline.call_args
        assert timeline_kwargs.get("window") == 75 or mock_timeline.call_args[0][4] == 75  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_overview_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """get_endgame_overview with a user that has no games returns all empty/zero payloads."""
        result = await get_endgame_overview(
            db_session,
            user_id=999999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            recency=None,
            window=50,
        )
        # All sub-payloads must be present
        assert result.stats.categories == []
        assert result.performance.endgame_wdl.total == 0
        assert result.timeline.overall == []
        assert result.score_gap_material is not None


class TestScoreGapMaterial:
    """Unit tests for _wdl_to_score and _compute_score_gap_material."""

    def _make_wdl(self, wins: int, draws: int, losses: int) -> EndgameWDLSummary:
        total = wins + draws + losses
        if total > 0:
            win_pct = round(wins / total * 100, 1)
            draw_pct = round(draws / total * 100, 1)
            loss_pct = round(losses / total * 100, 1)
        else:
            win_pct = draw_pct = loss_pct = 0.0
        return EndgameWDLSummary(
            wins=wins,
            draws=draws,
            losses=losses,
            total=total,
            win_pct=win_pct,
            draw_pct=draw_pct,
            loss_pct=loss_pct,
        )

    def _make_wdl_pct(
        self, win_pct: float, draw_pct: float, loss_pct: float, total: int = 100
    ) -> EndgameWDLSummary:
        wins = round(win_pct * total / 100)
        draws = round(draw_pct * total / 100)
        losses = total - wins - draws
        return EndgameWDLSummary(
            wins=wins,
            draws=draws,
            losses=losses,
            total=total,
            win_pct=win_pct,
            draw_pct=draw_pct,
            loss_pct=loss_pct,
        )

    # --- _wdl_to_score tests ---

    def test_wdl_to_score_standard_case(self):
        """Score for 45/10/45 WDL (100 total) should be 0.5."""
        wdl = self._make_wdl(45, 10, 45)
        assert _wdl_to_score(wdl) == 0.5

    def test_wdl_to_score_zero_total(self):
        """Score for 0-total WDL should be 0.0."""
        wdl = self._make_wdl(0, 0, 0)
        assert _wdl_to_score(wdl) == 0.0

    def test_wdl_to_score_all_wins(self):
        """Score for 100 wins / 0 draws / 0 losses should be 1.0."""
        wdl = self._make_wdl(100, 0, 0)
        assert _wdl_to_score(wdl) == 1.0

    # --- _compute_score_gap_material tests ---

    def test_score_gap_material_conversion_bucket(self):
        """Entry row with eval_cp=150 goes into 'conversion' bucket."""
        # entry_rows: (game_id, endgame_class_int, result, user_color, eval_cp, eval_mate)
        entry_rows = [_FakeRow(1, 1, "1-0", "white", 150, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        conversion = result.material_rows[0]
        assert conversion.bucket == "conversion"
        assert conversion.games == 1
        assert conversion.win_pct == 100.0

    def test_score_gap_material_even_bucket(self):
        """Entry row with eval_cp=50 (below threshold) goes into 'parity' bucket."""
        entry_rows = [_FakeRow(1, 1, "1-0", "white", 50, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        even = result.material_rows[1]
        assert even.bucket == "parity"
        assert even.games == 1

    def test_score_gap_material_recovery_bucket(self):
        """Entry row with eval_cp=-200 goes into 'recovery' bucket."""
        entry_rows = [_FakeRow(1, 1, "0-1", "white", -200, None)]
        endgame_wdl = self._make_wdl(0, 0, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        recovery = result.material_rows[2]
        assert recovery.bucket == "recovery"
        assert recovery.games == 1
        assert recovery.loss_pct == 100.0

    def test_score_gap_material_deduplication(self):
        """Two rows with same game_id but different endgame_class -> only 1 game in material table."""
        entry_rows = [
            _FakeRow(1, 1, "1-0", "white", 150, None),  # game_id=1, class rook
            _FakeRow(1, 3, "1-0", "white", 150, None),  # game_id=1, class pawn — duplicate
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        conversion = result.material_rows[0]
        assert conversion.bucket == "conversion"
        assert conversion.games == 1  # not 2

    def test_score_gap_material_none_eval_bucketed_as_even(self):
        """Entry row with eval_cp=None and eval_mate=None goes into the 'parity' bucket."""
        entry_rows = [_FakeRow(1, 1, "1-0", "white", None, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].games == 0  # conversion
        assert result.material_rows[1].bucket == "parity"
        assert result.material_rows[1].games == 1  # even — NULL rows land here
        assert result.material_rows[2].games == 0  # recovery

    def test_score_gap_material_empty_rows(self):
        """Empty entry_rows -> 3 material_rows all with games=0, score_difference=0.0."""
        endgame_wdl = self._make_wdl(0, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        assert len(result.material_rows) == 3
        assert all(row.games == 0 for row in result.material_rows)
        assert result.score_difference == 0.0

    def test_score_gap_material_score_difference_negative(self):
        """score_difference = endgame_score - non_endgame_score (signed, can be negative)."""
        # endgame score: win_pct=40, draw_pct=10 -> (40 + 5) / 100 = 0.45
        endgame_wdl = self._make_wdl_pct(40.0, 10.0, 50.0, total=100)
        # non_endgame score: win_pct=55, draw_pct=10 -> (55 + 5) / 100 = 0.60
        non_endgame_wdl = self._make_wdl_pct(55.0, 10.0, 35.0, total=100)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        assert result.score_difference == pytest.approx(-0.15, abs=1e-9)

    def test_score_gap_material_eval_mate_conversion(self):
        """Entry row with eval_mate=3 (white mates in 3) goes into 'conversion' bucket."""
        entry_rows = [_FakeRow(1, 1, "1-0", "white", None, 3)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].games == 1  # conversion: mate is conversion
        assert result.material_rows[0].bucket == "conversion"

    def test_score_gap_material_all_three_rows_always_present(self):
        """All three material_rows (conversion, even, recovery) present even when games=0."""
        endgame_wdl = self._make_wdl(0, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        buckets = [r.bucket for r in result.material_rows]
        assert buckets == ["conversion", "parity", "recovery"]

    def test_score_gap_material_boundary_conversion(self):
        """eval_cp exactly == +100 (at threshold) -> 'conversion' bucket (>= 100)."""
        entry_rows = [_FakeRow(1, 1, "1-0", "white", 100, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].bucket == "conversion"
        assert result.material_rows[0].games == 1

    def test_score_gap_material_boundary_recovery(self):
        """eval_cp exactly == -100 (at threshold) -> 'recovery' bucket (<= -100)."""
        entry_rows = [_FakeRow(1, 1, "0-1", "white", -100, None)]
        endgame_wdl = self._make_wdl(0, 0, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[2].bucket == "recovery"
        assert result.material_rows[2].games == 1


class TestScoreGapMaterialInvariant(TestScoreGapMaterial):
    """Phase 59 (Decision 4): assert sum(material_rows[i].games) == endgame_wdl.total.

    Inherits _make_wdl and _make_wdl_pct helpers from TestScoreGapMaterial.
    Updated for REFAC-02: rows now use (eval_cp, eval_mate) instead of
    (user_material_imbalance, user_material_imbalance_after) — persistence is gone.
    """

    def test_invariant_single_span_each_bucket(self):
        entry_rows = [
            _FakeRow(1, 1, "1-0", "white", 150, None),  # conversion
            _FakeRow(2, 1, "0-1", "white", -150, None),  # recovery
            _FakeRow(3, 1, "1/2-1/2", "white", 50, None),  # parity
        ]
        endgame_wdl = self._make_wdl(1, 1, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        total = sum(row.games for row in result.material_rows)
        assert total == endgame_wdl.total == 3
        assert result.material_rows[0].games == 1  # conversion
        assert result.material_rows[1].games == 1  # parity
        assert result.material_rows[2].games == 1  # recovery

    def test_invariant_multi_span_conversion_over_recovery(self):
        """Decision 2 tiebreak: when a game has both conversion and recovery spans, pick conversion."""
        entry_rows = [
            _FakeRow(1, 1, "1-0", "white", 150, None),  # conversion span (rook)
            _FakeRow(1, 3, "1-0", "white", -150, None),  # recovery span (pawn) — same game
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[0].bucket == "conversion"
        assert result.material_rows[0].games == 1

    def test_invariant_multi_span_null_then_qualifying(self):
        """Decision 1+2: first-seen NULL row must not drop the game if another span qualifies."""
        entry_rows = [
            _FakeRow(
                1, 1, "1-0", "white", None, None
            ),  # NULL first (would have been dropped pre-Phase 59)
            _FakeRow(1, 3, "1-0", "white", 150, None),  # qualifying conversion span
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[0].bucket == "conversion"
        assert result.material_rows[0].games == 1

    def test_invariant_null_eval_lands_in_even(self):
        """NULL eval -> 'parity' bucket (not dropped)."""
        entry_rows = [_FakeRow(1, 1, "1/2-1/2", "white", None, None)]
        endgame_wdl = self._make_wdl(0, 1, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[1].games == 1  # parity
        assert result.material_rows[1].draw_pct == 100.0

    def test_invariant_cp_above_threshold_is_conversion(self):
        """eval_cp=150 with no eval_mate -> 'conversion' bucket."""
        entry_rows = [_FakeRow(1, 1, "1-0", "white", 150, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[0].games == 1  # conversion

    def test_invariant_empty_input_no_divide_by_zero(self):
        endgame_wdl = self._make_wdl(0, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 0
        for row in result.material_rows:
            assert row.win_pct == 0.0
            assert row.draw_pct == 0.0
            assert row.loss_pct == 0.0
            assert row.score == 0.0

    def test_invariant_mixed_10_games(self):
        """10 distinct games across all decision cases; sum must equal endgame_wdl.total=10."""
        entry_rows = [
            # 3 pure conversion
            _FakeRow(1, 1, "1-0", "white", 150, None),
            _FakeRow(2, 1, "1-0", "white", 200, None),
            _FakeRow(3, 1, "0-1", "white", 150, None),
            # 2 pure recovery
            _FakeRow(4, 1, "1/2-1/2", "white", -150, None),
            _FakeRow(5, 1, "0-1", "white", -200, None),
            # 2 pure parity (below threshold)
            _FakeRow(6, 1, "1-0", "white", 50, None),
            _FakeRow(7, 1, "0-1", "white", -50, None),
            # 1 multi-span conversion-over-recovery
            _FakeRow(8, 1, "1-0", "white", 150, None),
            _FakeRow(8, 3, "1-0", "white", -150, None),
            # 1 NULL-first but conversion-qualifying second
            _FakeRow(9, 1, "1-0", "white", None, None),
            _FakeRow(9, 3, "1-0", "white", 150, None),
            # 1 all-NULL (lands in parity)
            _FakeRow(10, 1, "1/2-1/2", "white", None, None),
        ]
        endgame_wdl = self._make_wdl(6, 2, 2)  # total=10
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 10

    def test_invariant_deterministic_ordering(self):
        """Decision 2: within the 'parity' fallback, lowest endgame_class_int wins for reproducibility."""
        rows_order_a = [
            _FakeRow(1, 1, "1-0", "white", 50, None),
            _FakeRow(1, 3, "0-1", "white", 40, None),
        ]
        rows_order_b = [
            _FakeRow(1, 3, "0-1", "white", 40, None),
            _FakeRow(1, 1, "1-0", "white", 50, None),
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result_a = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, rows_order_a)
        result_b = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, rows_order_b)
        # Lowest endgame_class_int = 1 (result "1-0") should win — outcome is "win"
        assert result_a.material_rows[1].games == 1
        assert result_a.material_rows[1].win_pct == 100.0
        # Same across both orderings
        for i in range(3):
            assert result_a.material_rows[i].bucket == result_b.material_rows[i].bucket
            assert result_a.material_rows[i].games == result_b.material_rows[i].games
            assert result_a.material_rows[i].win_pct == result_b.material_rows[i].win_pct
            assert result_a.material_rows[i].draw_pct == result_b.material_rows[i].draw_pct
            assert result_a.material_rows[i].loss_pct == result_b.material_rows[i].loss_pct


class TestScoreGapMaterialOpponentBaseline(TestScoreGapMaterial):
    """Phase 60 opponent-baseline tests deleted in Phase 87.2 (D-05).

    The mirror-bucket rate-diff peer-bullet (opponent_score, opponent_games,
    diff_p_value, diff_ci_low, diff_ci_high on MaterialRow) was removed because
    the Wald-z test was mathematically degenerate: Conv-Gap == Recov-Gap by
    symmetry, and Parity-Gap is an affine transformation of the gauge.
    Replaced by the eval-baseline Delta-ES Score Gap family on
    ScoreGapMaterialResponse (section2_score_gap_* — Phase 87.2 D-06).

    Retained as a class to avoid renumbering downstream test IDs; its bucket-
    classification + score logic is preserved in TestScoreGapMaterial and
    TestScoreGapMaterialInvariant.
    """

    @staticmethod
    def _conversion_row(game_id: int, result: str) -> _FakeRow:
        # eval_cp >= +100 -> conversion
        return _FakeRow(game_id, 1, result, "white", 150, None)

    @staticmethod
    def _recovery_row(game_id: int, result: str) -> _FakeRow:
        # eval_cp <= -100 -> recovery
        return _FakeRow(game_id, 1, result, "white", -150, None)

    def test_material_row_scores_still_correct_after_field_deletion(self) -> None:
        """Sanity check: bucket scores + WDL counts still correct after the
        deletion of the 5 opponent/diff fields (Phase 87.2 D-05)."""
        conv_rows = [self._conversion_row(i, "1-0") for i in range(60)] + [
            self._conversion_row(i + 60, "0-1") for i in range(40)
        ]
        rec_rows = [self._recovery_row(i + 100, "1-0") for i in range(40)] + [
            self._recovery_row(i + 140, "0-1") for i in range(60)
        ]
        entry_rows = conv_rows + rec_rows
        endgame_wdl = self._make_wdl(100, 0, 100)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        conv = result.material_rows[0]
        rec = result.material_rows[2]
        assert conv.bucket == "conversion"
        assert conv.games == 100
        assert conv.score == pytest.approx(0.60, abs=1e-9)
        assert rec.bucket == "recovery"
        assert rec.games == 100
        assert rec.score == pytest.approx(0.40, abs=1e-9)
        # Deleted fields must not exist on the row
        assert not hasattr(conv, "opponent_score")
        assert not hasattr(conv, "opponent_games")
        assert not hasattr(conv, "diff_p_value")


# ---------------------------------------------------------------------------
# Phase 54: _extract_entry_clocks and _compute_clock_pressure tests
# ---------------------------------------------------------------------------


def _make_clock_row(
    game_id: int,
    time_control_bucket: str | None,
    base_time_seconds: int | None,
    termination: str | None,
    result: str,
    user_color: str,
    ply_array: list[int],
    clock_array: list[float | None],
    played_at: Any = None,
) -> tuple:
    """Build a tuple matching the query_clock_stats_rows output shape.

    Shape: (game_id, time_control_bucket, base_time_seconds, termination,
            result, user_color, ply_array, clock_array, played_at)

    base_time_seconds is the per-game starting clock (e.g. 600 for 600+0, 900
    for 900+10). Used as the denominator for % computation (quick-260414-smt).

    played_at was appended in quick-260416-w3q so the clock-diff timeline can
    bucket games by ISO week. Legacy tests that only exercise the table/chart
    consumers leave it as None — those consumers ignore the trailing column.

    Since quick-260414-pv4, query_clock_stats_rows emits one row per qualifying
    game (whole-game 6-ply rule), so test rows should use distinct game_ids
    unless the test is specifically guarding against duplicate handling.
    """
    return (
        game_id,
        time_control_bucket,
        base_time_seconds,
        termination,
        result,
        user_color,
        ply_array,
        clock_array,
        played_at,
    )


class TestExtractEntryClocks:
    """Unit tests for _extract_entry_clocks helper (Phase 54).

    Verifies ply-parity logic: white player's clocks are at even plies (0,2,4,...),
    black player's clocks are at odd plies (1,3,5,...).
    """

    def test_white_user_even_plies(self):
        """White user: first even-ply clock is user clock, first odd-ply clock is opp clock."""
        result = _extract_entry_clocks([0, 1, 2, 3], [10.0, 8.0, 9.0, 7.0], "white")
        assert result == (10.0, 8.0)

    def test_black_user_odd_plies(self):
        """Black user: first odd-ply clock is user clock, first even-ply clock is opp clock."""
        result = _extract_entry_clocks([0, 1, 2, 3], [10.0, 8.0, 9.0, 7.0], "black")
        assert result == (8.0, 10.0)

    def test_all_none_clocks(self):
        """All None clocks return (None, None)."""
        result = _extract_entry_clocks([0, 1, 2, 3], [None, None, None, None], "white")
        assert result == (None, None)

    def test_user_clock_only(self):
        """User clock present, opp clock None -> (value, None)."""
        result = _extract_entry_clocks([0, 1], [10.0, None], "white")
        assert result == (10.0, None)

    def test_opp_clock_only(self):
        """Opp clock present, user clock None -> (None, value)."""
        result = _extract_entry_clocks([0, 1], [None, 8.0], "white")
        assert result == (None, 8.0)

    def test_skips_none_finds_later(self):
        """Skips None entries; finds first non-None for each parity.

        plies=[0,1,2,3], clocks=[None,8.0,9.0,7.0], user=white:
        - first user ply (even): ply 0 -> None; next even ply 2 -> 9.0
        - first opp ply (odd): ply 1 -> 8.0
        -> (9.0, 8.0)
        """
        result = _extract_entry_clocks([0, 1, 2, 3], [None, 8.0, 9.0, 7.0], "white")
        assert result == (9.0, 8.0)

    def test_empty_plies(self):
        """Empty ply array returns (None, None)."""
        result = _extract_entry_clocks([], [], "white")
        assert result == (None, None)

    def test_single_ply_user_parity(self):
        """Single ply matching user parity -> (value, None)."""
        result = _extract_entry_clocks([0], [5.0], "white")
        assert result == (5.0, None)

    def test_single_ply_opp_parity(self):
        """Single ply matching opp parity -> (None, value)."""
        result = _extract_entry_clocks([1], [5.0], "white")
        assert result == (None, 5.0)


class TestComputeClockPressure:
    """Unit tests for _compute_clock_pressure (Phase 54).

    Verifies grouping by time control, deduplication, row filtering, and net timeout rate.
    """

    def _make_blitz_rows(
        self,
        count: int,
        user_clock: float = 50.0,
        opp_clock: float = 60.0,
        base_time_seconds: int | None = 180,
        termination: str = "checkmate",
        result: str = "1-0",
        user_color: str = "white",
        start_id: int = 1,
    ) -> list[tuple]:
        """Build `count` blitz rows, each with a distinct game_id."""
        rows = []
        for i in range(count):
            game_id = start_id + i
            # White even ply 0 = user_clock, odd ply 1 = opp_clock
            rows.append(
                _make_clock_row(
                    game_id=game_id,
                    time_control_bucket="blitz",
                    base_time_seconds=base_time_seconds,
                    termination=termination,
                    result=result,
                    user_color=user_color,
                    ply_array=[0, 1],
                    clock_array=[user_clock, opp_clock],
                )
            )
        return rows

    def test_basic_single_bucket(self):
        """12 blitz games with clock data produce one ClockStatsRow for blitz with correct averages."""
        rows = self._make_blitz_rows(12, user_clock=50.0, opp_clock=60.0, base_time_seconds=180)
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.time_control == "blitz"
        assert row.label == "Blitz"
        assert row.total_endgame_games == 12
        assert row.clock_games == 12
        assert row.user_avg_seconds == pytest.approx(50.0)
        assert row.opp_avg_seconds == pytest.approx(60.0)
        assert row.avg_clock_diff_seconds == pytest.approx(-10.0)
        # Pct: 50/180*100 and 60/180*100
        assert row.user_avg_pct == pytest.approx(50.0 / 180 * 100, abs=0.01)
        assert row.opp_avg_pct == pytest.approx(60.0 / 180 * 100, abs=0.01)

    def test_hides_below_threshold(self):
        """5 games for bullet -> bullet row not in output (below MIN_GAMES_FOR_CLOCK_STATS=10)."""
        rows = []
        for i in range(5):
            rows.append(
                _make_clock_row(
                    game_id=i + 1,
                    time_control_bucket="bullet",
                    base_time_seconds=60,
                    termination="checkmate",
                    result="1-0",
                    user_color="white",
                    ply_array=[0, 1],
                    clock_array=[5.0, 4.0],
                )
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 0

    def test_net_timeout_rate_single_row_per_game(self):
        """One row per game (post-pv4 SQL contract) -> timeout rate computed over unique games.

        Under the whole-game rule (_any_endgame_ply_subquery), query_clock_stats_rows
        emits one row per qualifying game. 10 rows -> 10 unique games. One timeout win
        gives net_timeout_rate = 1/10 * 100 = 10.0.

        Regression guard (quick-260414-pv4): even if a future change accidentally
        reintroduced duplicate game_ids, the set-based dedup in _compute_clock_pressure
        still prevents double-counting.
        """
        # 10 distinct games; game_id=1 is the single timeout win.
        rows = [_make_clock_row(1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [5.0, 3.0])]
        for i in range(2, 11):
            rows.append(
                _make_clock_row(i, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [5.0, 3.0])
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.total_endgame_games == 10
        assert row.net_timeout_rate == pytest.approx(10.0)

    def test_split_class_game_included_via_whole_game_rule(self):
        """Service trusts repo contract: a row representing a split-class game is accepted.

        Regression guard for quick-260414-pv4: under the whole-game rule the repo
        passes through games whose endgame plies were split across multiple classes
        (e.g. 3 in KP_KP + 3 in KR_KR). The service must treat such a row exactly
        like any other row — no per-class logic remains at the service layer.
        """
        # Game 1 is the split-class game; its ply_array represents plies pooled across
        # multiple endgame classes. The service does not know or care about class.
        rows = [
            _make_clock_row(
                1,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1, 2, 3, 4, 5],
                [90.0, 60.0, 85.0, 55.0, 80.0, 50.0],
            ),
        ]
        # Filler rows to clear MIN_GAMES_FOR_CLOCK_STATS
        for i in range(2, 11):
            rows.append(
                _make_clock_row(i, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0])
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        assert result.rows[0].total_endgame_games == 10

    def test_net_timeout_rate_computation(self):
        """20 games, 3 timeout wins, 1 timeout loss -> rate = (3-1)/20*100 = 10.0."""
        rows = []
        for i in range(3):
            rows.append(
                _make_clock_row(i + 1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [3.0, 10.0])
            )
        rows.append(
            _make_clock_row(4, "blitz", 180, "timeout", "0-1", "white", [0, 1], [3.0, 10.0])
        )
        for i in range(16):
            rows.append(
                _make_clock_row(
                    i + 5, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [50.0, 60.0]
                )
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        assert result.rows[0].net_timeout_rate == pytest.approx(10.0)

    def test_base_time_seconds_none_row_hidden(self):
        """Buckets where every game has base_time_seconds=None -> row hidden entirely.

        Without a base clock we can't compute pct or apply the 2x clamp, so these
        games (daily/correspondence) are excluded from every clock accumulator.
        The row-inclusion gate is on clock_games (not total_endgame_games), so a
        bucket with zero usable clock data is dropped from the table instead of
        showing a row full of "—" placeholders.
        """
        rows = self._make_blitz_rows(10, user_clock=50.0, opp_clock=60.0, base_time_seconds=None)
        result = _compute_clock_pressure(rows)
        assert result.rows == []
        # Pre-filter total is still tracked for the section-level total
        assert result.total_endgame_games == 10
        assert result.total_clock_games == 0

    def test_both_clocks_none_excluded_from_clock_games(self):
        """Spans where both user and opp clocks are None -> clock_games=0, averages=None."""
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    game_id=i + 1,
                    time_control_bucket="rapid",
                    base_time_seconds=600,
                    termination="checkmate",
                    result="1-0",
                    user_color="white",
                    ply_array=[0, 1],
                    clock_array=[None, None],
                )
            )
        result = _compute_clock_pressure(rows)
        # Row-inclusion gate is on clock_games (post-fix); bucket with zero
        # usable clock data is hidden from the table entirely.
        assert result.rows == []
        assert result.total_endgame_games == 10
        assert result.total_clock_games == 0

    def test_fixed_row_order(self):
        """Rows returned in bullet, blitz, rapid, classical order."""
        rows = []
        for tc, tc_secs in [("rapid", 600), ("bullet", 60), ("classical", 1800), ("blitz", 180)]:
            for i in range(10):
                rows.append(
                    _make_clock_row(
                        game_id=len(rows) + 1,
                        time_control_bucket=tc,
                        base_time_seconds=tc_secs,
                        termination="checkmate",
                        result="1-0",
                        user_color="white",
                        ply_array=[0, 1],
                        clock_array=[20.0, 25.0],
                    )
                )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 4
        assert [r.time_control for r in result.rows] == ["bullet", "blitz", "rapid", "classical"]

    def test_response_totals_include_hidden_rows(self):
        """total_clock_games and total_endgame_games include all time controls, even hidden rows."""
        # 5 bullet games (hidden — below threshold) + 10 blitz games (visible)
        rows = []
        for i in range(5):
            rows.append(
                _make_clock_row(
                    i + 1, "bullet", 60, "checkmate", "1-0", "white", [0, 1], [5.0, 4.0]
                )
            )
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 6, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [50.0, 60.0]
                )
            )
        result = _compute_clock_pressure(rows)
        # Only blitz row visible
        assert len(result.rows) == 1
        # But totals include bullet games too
        assert result.total_endgame_games == 15
        assert result.total_clock_games == 15

    def test_none_time_control_bucket_skipped(self):
        """Rows with time_control_bucket=None are skipped entirely."""
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(i + 1, None, None, "checkmate", "1-0", "white", [0, 1], [5.0, 4.0])
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 0
        assert result.total_endgame_games == 0


class TestComputeTimePressureChart:
    """Unit tests for _compute_time_pressure_chart (Phase 55).

    Verifies bucket assignment, score averaging, exclusion rules,
    and the minimum games threshold.
    """

    def test_no_double_count_when_repo_returns_one_row_per_game(self):
        """Regression guard for quick-260414-pv4: no double counting at the chart layer.

        query_clock_stats_rows now emits exactly one row per qualifying game under
        the whole-game rule. With 10 distinct game_ids, total_endgame_games must be
        10 (not 20, as the previous per-span SQL could produce for games that
        cycled through two endgame classes). Bucket game_counts must also sum to
        the number of unique games, not spans.
        """
        rows = [
            _make_clock_row(i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0])
            for i in range(10)
        ]
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10
        # User/opp series are now pooled across all qualifying time controls.
        assert len(result.user_series) == 10
        assert len(result.opp_series) == 10
        # User bucket sum equals unique games (not spans).
        assert sum(p.game_count for p in result.user_series) == 10
        assert sum(p.game_count for p in result.opp_series) == 10

    def test_split_class_game_included_via_whole_game_rule(self):
        """Chart accepts a row whose ply_array reflects plies pooled across classes.

        Regression guard for quick-260414-pv4: the service does not inspect
        endgame_class, so a split-class qualifying game (passed through by the repo
        under the whole-game rule) is counted the same as any other row.
        """
        rows = [
            _make_clock_row(
                1,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1, 2, 3, 4, 5],
                [90.0, 60.0, 85.0, 55.0, 80.0, 50.0],
            ),
        ]
        for i in range(2, 11):
            rows.append(
                _make_clock_row(i, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0])
            )
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10

    def test_single_game_win_user_bucket_populated(self):
        """Test 1: 10 bullet wins, user 50% time -> user_score=1.0 -> user bucket 5 (50-60%) populated."""
        # base_time_seconds=60, user_clock=30 -> 50% -> bucket index 5
        # opp_clock=20 -> 33% -> bucket index 3
        rows = [
            _make_clock_row(
                game_id=i + 1,
                time_control_bucket="bullet",
                base_time_seconds=60,
                termination="checkmate",
                result="1-0",
                user_color="white",
                ply_array=[0, 1],
                clock_array=[30.0, 20.0],
            )
            for i in range(10)
        ]
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10
        assert len(result.user_series) == 10
        assert len(result.opp_series) == 10
        # User bucket 5 (50-60%) should have score 1.0
        user_bucket5 = result.user_series[5]
        assert user_bucket5.bucket_index == 5
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(1.0)
        # Opp bucket 3 (30-40%) should have score 0.0 (1 - 1.0)
        opp_bucket3 = result.opp_series[3]
        assert opp_bucket3.game_count == 10
        assert opp_bucket3.score == pytest.approx(0.0)

    def test_two_games_same_bucket_scores_averaged(self):
        """Test 2: Two games, same user bucket -> scores averaged correctly."""
        # game 1: win -> score=1.0; game 2: loss -> score=0.0; both at 50% -> bucket 5
        # Add 8 draws at same bucket to reach MIN_GAMES threshold
        rows = [
            _make_clock_row(1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]),
            _make_clock_row(2, "blitz", 180, "checkmate", "0-1", "white", [0, 1], [90.0, 60.0]),
        ]
        for i in range(3, 11):
            rows.append(
                _make_clock_row(
                    i, "blitz", 180, "checkmate", "1/2-1/2", "white", [0, 1], [90.0, 60.0]
                )
            )
        result = _compute_time_pressure_chart(rows)
        # All games in user bucket 5 (90/180=50%) -> average of 1.0 + 0.0 + 8*0.5 = 5.0 / 10 = 0.5
        user_bucket5 = result.user_series[5]
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(0.5)

    def test_game_without_both_clocks_excluded(self):
        """Test 3: Game without both clocks is excluded from both series."""
        rows = []
        # 9 games with clocks (ply=[0,1] clock=[90,60])
        for i in range(9):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        # This game has only user ply/clock (no opp) -> opp_clock=None -> excluded from series
        rows.append(_make_clock_row(10, "blitz", 180, "checkmate", "1-0", "white", [0], [90.0]))
        # Total = 10 games -> threshold met; only 9 contribute to series
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10
        # Only 9 games with both clocks contribute to series
        total_user = sum(p.game_count for p in result.user_series)
        assert total_user == 9

    def test_game_without_base_time_seconds_excluded(self):
        """Test 4: Game without base_time_seconds is excluded from chart series."""
        rows = []
        for i in range(10):
            # base_time_seconds=None -> excluded from bucket computation (no denominator)
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", None, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        result = _compute_time_pressure_chart(rows)
        # 10 games with valid TC bucket -> TC passes threshold; but no base_time_seconds
        # means no game contributes to any bucket, so all counts are 0.
        assert result.total_endgame_games == 10
        for p in result.user_series:
            assert p.game_count == 0
            assert p.score is None
        for p in result.opp_series:
            assert p.game_count == 0
            assert p.score is None

    def test_time_control_below_min_games_excluded(self):
        """Test 5: Time control with fewer than MIN_GAMES_FOR_CLOCK_STATS=10 games excluded.

        The only TC (rapid, 9 games) fails the threshold and is dropped from the pool.
        With no TC contributing, total_endgame_games is 0 and all buckets are empty.
        """
        rows = [
            _make_clock_row(
                i + 1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
            )
            for i in range(9)
        ]
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 0
        for p in result.user_series:
            assert p.game_count == 0
            assert p.score is None
        for p in result.opp_series:
            assert p.game_count == 0
            assert p.score is None

    def test_bucket_clamping_100_percent_time(self):
        """Test 6: 100% time remaining -> clamped to bucket index 9 (not 10)."""
        rows = [
            _make_clock_row(
                i + 1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [600.0, 300.0]
            )
            for i in range(10)
        ]
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10
        # 100% time -> int(100/10)=10, clamped to 9
        user_bucket9 = result.user_series[9]
        assert user_bucket9.bucket_index == 9
        assert user_bucket9.bucket_label == "90-100%"
        assert user_bucket9.game_count == 10

    def test_empty_clock_rows_returns_empty_response(self):
        """Test 7: Empty clock_rows produces a response with 10 empty bucket points per series."""
        result = _compute_time_pressure_chart([])
        assert result.total_endgame_games == 0
        assert len(result.user_series) == 10
        assert len(result.opp_series) == 10
        for p in result.user_series:
            assert p.game_count == 0
            assert p.score is None
        for p in result.opp_series:
            assert p.game_count == 0
            assert p.score is None

    def test_multiple_time_controls_pool_into_single_series(self):
        """Test 8: Multiple time controls pool into a single user/opp series (no per-TC rows).

        10 blitz games (90/180=50% -> user bucket 5) + 10 rapid games (300/600=50% -> user bucket 5)
        land in the same pooled bucket, summing to 20 games at bucket 5.
        """
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 11, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
                )
            )
        result = _compute_time_pressure_chart(rows)
        # Both TCs passed the threshold (10 games each) -> pooled total = 20
        assert result.total_endgame_games == 20
        # Pooled bucket game counts sum to 20 as well
        assert sum(p.game_count for p in result.user_series) == 20
        assert sum(p.game_count for p in result.opp_series) == 20
        # All 20 games sit at user bucket 5 (50%)
        assert result.user_series[5].game_count == 20

    def test_user_score_derivation_win_draw_loss(self):
        """Test 9: win=1.0, draw=0.5, loss=0.0 for user_score; opp gets 1-user_score."""
        # 10 games: 4 wins, 3 draws, 3 losses — all at same bucket (50%) so we check the average
        # user_score avg = (4*1.0 + 3*0.5 + 3*0.0) / 10 = 5.5/10 = 0.55
        # opp_score avg = 1 - 0.55 = 0.45
        rows = []
        for i in range(4):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        for i in range(3):
            rows.append(
                _make_clock_row(
                    i + 5, "blitz", 180, "checkmate", "1/2-1/2", "white", [0, 1], [90.0, 60.0]
                )
            )
        for i in range(3):
            rows.append(
                _make_clock_row(
                    i + 8, "blitz", 180, "checkmate", "0-1", "white", [0, 1], [90.0, 60.0]
                )
            )
        result = _compute_time_pressure_chart(rows)
        # 90/180 = 50% -> bucket index 5
        user_bucket5 = result.user_series[5]
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(0.55)
        # opp: 60/180 = 33% -> bucket index 3
        opp_bucket3 = result.opp_series[3]
        assert opp_bucket3.game_count == 10
        assert opp_bucket3.score == pytest.approx(0.45)

    def test_bucket_labels_correct(self):
        """Bucket labels are formatted as '0-10%', '10-20%', ..., '90-100%'."""
        buckets: list[list[float]] = [[0.0, 0] for _ in range(10)]
        series = _build_bucket_series(buckets)
        assert len(series) == 10
        assert series[0].bucket_label == "0-10%"
        assert series[4].bucket_label == "40-50%"
        assert series[9].bucket_label == "90-100%"

    def test_bucket_score_none_when_no_games(self):
        """Buckets with no games have score=None (not 0.0)."""
        buckets: list[list[float]] = [[0.0, 0] for _ in range(10)]
        series = _build_bucket_series(buckets)
        for point in series:
            assert point.score is None
            assert point.game_count == 0

    def test_total_endgame_games_counts_all_with_valid_tc(self):
        """total_endgame_games = games with valid time_control_bucket (regardless of clock data)."""
        rows = []
        # 5 games with clocks
        for i in range(5):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        # 5 games without clock data (empty arrays) but valid TC bucket
        for i in range(5):
            rows.append(_make_clock_row(i + 6, "blitz", 180, "checkmate", "1-0", "white", [], []))
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10

    def test_user_and_opp_game_count_totals_are_equal(self):
        """Same-game symmetry: every endgame contributes one user point AND one opp point,
        so summed game_counts across the user series and opp series must be equal.

        Spans multiple time controls (bullet + rapid) to exercise pooled aggregation.
        """
        rows: list[tuple] = []
        # Bullet: 10 games, varied clocks and results so user/opp land in different buckets
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1,
                    "bullet",
                    60,
                    "checkmate",
                    ["1-0", "0-1", "1/2-1/2"][i % 3],
                    "white" if i % 2 == 0 else "black",
                    [0, 1],
                    [float(10 + i * 4), float(5 + i * 3)],
                )
            )
        # Rapid: 12 games, different clock distribution
        for i in range(12):
            rows.append(
                _make_clock_row(
                    100 + i,
                    "rapid",
                    600,
                    "checkmate",
                    ["1-0", "0-1", "1/2-1/2"][i % 3],
                    "white" if i % 2 == 0 else "black",
                    [0, 1],
                    [float(100 + i * 40), float(80 + i * 35)],
                )
            )
        result = _compute_time_pressure_chart(rows)
        total_user = sum(p.game_count for p in result.user_series)
        total_opp = sum(p.game_count for p in result.opp_series)
        assert total_user == total_opp
        # Sanity: both totals match the number of qualifying games (both clocks present, within clamp).
        # All 22 games have both clocks and stay within the 2x clamp, so all contribute.
        assert total_user == 22


# ---------------------------------------------------------------------------
# quick-260414-smt: per-game base_time_seconds denominator + >2x clamp tests
# ---------------------------------------------------------------------------


class TestClockPressurePerGameDenominator:
    """Tests verifying that _compute_clock_pressure uses per-game base_time_seconds.

    Before quick-260414-smt, the denominator was the first-seen time_control_seconds
    for the bucket (base + inc*40). This caused a 1800+0 game's 1500s clock to be
    divided by 600 (=250%), since a 600+0 game happened to be processed first.

    After quick-260414-smt, each game divides by its own base_time_seconds.
    """

    def test_per_game_denominator_two_rapid_games_different_base(self):
        """Two rapid games with different base clocks produce user_avg_pct = per-game mean.

        Game 1: base=600, user_clock=300 -> 50%
        Game 2: base=1800, user_clock=900 -> 50%
        Expected user_avg_pct = 50% (not 300/1800*100=16.7% as bucket-first-seen would give)
        """
        rows = [
            _make_clock_row(1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]),
            _make_clock_row(2, "rapid", 1800, "checkmate", "1-0", "white", [0, 1], [900.0, 600.0]),
        ]
        # Pad to hit MIN_GAMES_FOR_CLOCK_STATS threshold — 8 more rapid games at 600 base, 50%
        for i in range(3, 11):
            rows.append(
                _make_clock_row(
                    i, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
                )
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # All 10 games: 9 at 50%, 1 at 50% -> avg = 50%
        assert row.user_avg_pct == pytest.approx(50.0, abs=0.1)

    def test_per_game_denominator_asymmetric_bases(self):
        """One 600-base game at 300s clock (50%) and one 1800-base game at 1500s clock (83.3%).

        Expected avg_pct = (9*50% + 83.33%) / 10 = 53.33%
        With old bucket-first-seen at base=600, second game would give 1500/600*100=250% (absurd).
        """
        rows = [
            _make_clock_row(1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]),
            _make_clock_row(2, "rapid", 1800, "checkmate", "1-0", "white", [0, 1], [1500.0, 600.0]),
        ]
        # Pad to threshold
        for i in range(3, 11):
            rows.append(
                _make_clock_row(
                    i, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
                )
            )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # Game 1: 300/600=50%; Games 3-10: 300/600=50% each; Game 2: 1500/1800=83.33%
        # avg = (9*50 + 83.33) / 10 = 533.33 / 10 = 53.33%
        assert row.user_avg_pct == pytest.approx((9 * 50.0 + 1500.0 / 1800.0 * 100) / 10, abs=0.1)

    def test_clamp_excludes_game_with_3x_base_clock(self):
        """Game where user_clock = 3 * base_time_seconds is excluded from all clock aggregation.

        The game still counts in total_endgame_games (it reached an endgame), but contributes
        nothing to clock_games, user_avg_pct, user_avg_seconds, or any other clock metric.
        """
        # 9 normal games + 1 clamped game (clock = 3x base = bogus reading)
        rows = []
        for i in range(9):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        # Game 10: user_clock = 3 * 180 = 540 -> >2x -> clamped, excluded from clock accumulation
        rows.append(
            _make_clock_row(10, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [540.0, 60.0])
        )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # total_endgame_games counts all 10 (game reached endgame)
        assert row.total_endgame_games == 10
        # clock_games counts only 9 (clamped game excluded)
        assert row.clock_games == 9
        # Pct based only on the 9 normal games (90/180=50%)
        assert row.user_avg_pct == pytest.approx(50.0, abs=0.1)
        # Seconds also only from 9 games
        assert row.user_avg_seconds == pytest.approx(90.0, abs=0.1)

    def test_clamp_excludes_game_with_high_opp_clock(self):
        """Game where opp_clock > 2x base is also excluded entirely."""
        rows = []
        for i in range(9):
            rows.append(
                _make_clock_row(
                    i + 1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
                )
            )
        # Opp clock = 3 * 600 = 1800 -> >2x -> whole game excluded
        rows.append(
            _make_clock_row(10, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 1800.0])
        )
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.total_endgame_games == 10
        assert row.clock_games == 9

    def test_clamp_does_not_affect_timeout_accounting(self):
        """Timeout tracking is independent of clock accumulation — clamped games still count.

        The clamp only affects clock_games / pct / seconds aggregation.
        Timeout wins/losses are tracked per game_id regardless.
        """
        # Game 1: timeout win with bogus clock (3x base) -> still counts as timeout win
        rows = [_make_clock_row(1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [540.0, 60.0])]
        for i in range(9):
            rows.append(
                _make_clock_row(
                    i + 2, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        result = _compute_clock_pressure(rows)
        row = result.rows[0]
        # 1 timeout win / 10 total games = 10% net timeout rate
        assert row.net_timeout_rate == pytest.approx(10.0)
        # clock_games = 9 (game 1 clamped from clock accumulation)
        assert row.clock_games == 9


class TestTimePressureChartPerGameDenominator:
    """Tests verifying _compute_time_pressure_chart uses per-game base_time_seconds + clamp."""

    def test_per_game_denominator_bucket_assignment(self):
        """Two rapid games with different base clocks bucket independently by their own %.

        Game 1: base=600, user_clock=300 -> 50% -> bucket 5
        Game 2: base=1800, user_clock=1800 -> 100% -> bucket 9 (clamped to last)
        Both at rapid, both wins.
        """
        rows = [
            _make_clock_row(1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]),
            _make_clock_row(2, "rapid", 1800, "checkmate", "1-0", "white", [0, 1], [1800.0, 600.0]),
        ]
        # Pad to threshold
        for i in range(3, 11):
            rows.append(
                _make_clock_row(
                    i, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]
                )
            )
        result = _compute_time_pressure_chart(rows)
        assert result.total_endgame_games == 10
        # 9 games at 50% (bucket 5) + 1 game at 100% (bucket 9)
        assert result.user_series[5].game_count == 9
        assert result.user_series[9].game_count == 1

    def test_chart_clamp_excludes_bogus_game(self):
        """Game with user_clock > 2x base is excluded from chart series.

        10 normal games + 1 clamped game. The clamped game counts in total_endgame_games
        but not in any bucket.
        """
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]
                )
            )
        # Game 11: user_clock = 3 * 180 = 540 -> >2x -> clamped
        rows.append(
            _make_clock_row(11, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [540.0, 60.0])
        )
        result = _compute_time_pressure_chart(rows)
        # total_endgame_games = 11 (all games with valid TC bucket)
        assert result.total_endgame_games == 11
        # Only 10 games contribute to series (clamped game excluded)
        assert sum(p.game_count for p in result.user_series) == 10


# ---------------------------------------------------------------------------
# quick-260416-w3q: _compute_clock_pressure_timeline tests
# ---------------------------------------------------------------------------


class TestComputeClockPressureTimeline:
    """Unit tests for _compute_clock_pressure_timeline (quick-260416-w3q)."""

    def test_empty_input_returns_empty(self):
        assert _compute_clock_pressure_timeline([], 100) == []

    def test_drops_early_points_below_min_games(self):
        """With fewer than MIN_GAMES_FOR_TIMELINE (=10) games total, no weekly points emit."""
        base = datetime.datetime(2026, 1, 5, 12, 0, 0)  # Monday
        rows = [
            _make_clock_row(
                i + 1,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1],
                [50.0, 60.0],
                played_at=base + datetime.timedelta(days=i),
            )
            for i in range(5)
        ]
        assert _compute_clock_pressure_timeline(rows, 100) == []

    def test_emits_one_point_per_iso_week_using_rolling_mean(self):
        """Games across two ISO weeks -> two weekly points with running mean diff %.

        Games in week 1: 10 games with diff = -10/180 (user_clock=50, opp_clock=60, base=180).
        Games in week 2: 10 games with diff = +20/180 (user_clock=80, opp_clock=60, base=180).
        Week-2 point uses mean of all 20 games (trailing window of 100 pre-fills).
        """
        wk1_monday = datetime.datetime(2026, 1, 5, 12, 0, 0)  # ISO week 2
        wk2_monday = datetime.datetime(2026, 1, 12, 12, 0, 0)  # ISO week 3
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [50.0, 60.0],
                    played_at=wk1_monday + datetime.timedelta(hours=i),
                )
            )
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 11,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [80.0, 60.0],
                    played_at=wk2_monday + datetime.timedelta(hours=i),
                )
            )
        series = _compute_clock_pressure_timeline(rows, 100)
        assert len(series) == 2
        # Week 1: mean of 10 games at -10/180*100 ≈ -5.556
        assert series[0].date == "2026-01-05"
        assert series[0].avg_clock_diff_pct == pytest.approx(-10 / 180 * 100, abs=0.01)
        assert series[0].game_count == 10
        # Week 2: mean of all 20 games = ((10 * -10) + (10 * 20)) / 20 / 180 * 100
        assert series[1].date == "2026-01-12"
        expected = ((10 * -10) + (10 * 20)) / 20 / 180 * 100
        assert series[1].avg_clock_diff_pct == pytest.approx(expected, abs=0.01)
        assert series[1].game_count == 20

    def test_rolling_window_caps_at_window_size(self):
        """Window cap: later weeks' point mean reflects only the trailing window games.

        20 games across two weeks (10 each) with window=10: week 2's mean reflects
        only its own 10 games (week 1 scrolls out of the window).
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [50.0, 60.0],  # diff = -10/180
                    played_at=wk1 + datetime.timedelta(hours=i),
                )
            )
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 11,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [80.0, 60.0],  # diff = +20/180
                    played_at=wk2 + datetime.timedelta(hours=i),
                )
            )
        series = _compute_clock_pressure_timeline(rows, 10)
        assert len(series) == 2
        # Week 1: 10-game window filled with week-1 games only
        assert series[0].avg_clock_diff_pct == pytest.approx(-10 / 180 * 100, abs=0.01)
        assert series[0].game_count == 10
        # Week 2: window capped to 10 -> only week-2 games contribute
        assert series[1].avg_clock_diff_pct == pytest.approx(20 / 180 * 100, abs=0.01)
        assert series[1].game_count == 10

    def test_skips_rows_without_played_at_or_base_time(self):
        """Rows missing played_at, base_time_seconds, or clocks are excluded."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        rows = [
            # Valid rows
            *[
                _make_clock_row(
                    i + 1,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [50.0, 60.0],
                    played_at=monday + datetime.timedelta(hours=i),
                )
                for i in range(10)
            ],
            # Invalid: no played_at
            _make_clock_row(100, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [50.0, 60.0]),
            # Invalid: no base_time_seconds
            _make_clock_row(
                101,
                "blitz",
                None,
                "checkmate",
                "1-0",
                "white",
                [0, 1],
                [50.0, 60.0],
                played_at=monday,
            ),
            # Invalid: no clocks
            _make_clock_row(
                102,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1],
                [None, None],
                played_at=monday,
            ),
            # Invalid: clock > 2x base time (bogus)
            _make_clock_row(
                103,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1],
                [540.0, 60.0],
                played_at=monday,
            ),
        ]
        series = _compute_clock_pressure_timeline(rows, 100)
        assert len(series) == 1
        assert series[0].game_count == 10

    def test_compute_clock_pressure_exposes_timeline(self):
        """_compute_clock_pressure returns the timeline + window fields."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        rows = [
            _make_clock_row(
                i + 1,
                "blitz",
                180,
                "checkmate",
                "1-0",
                "white",
                [0, 1],
                [50.0, 60.0],
                played_at=monday + datetime.timedelta(hours=i),
            )
            for i in range(12)
        ]
        result = _compute_clock_pressure(rows)
        assert result.timeline_window == CLOCK_PRESSURE_TIMELINE_WINDOW
        assert len(result.timeline) == 1
        assert result.timeline[0].date == "2026-01-05"
        assert result.timeline[0].game_count == 12

    def test_clock_pressure_timeline_cutoff_filters_output_but_pre_fills_window(self):
        """Cutoff drops pre-cutoff output points but the rolling window still uses them.

        10 games in week 1 (pre-cutoff) with diff -10/180. 10 games in week 2
        (post-cutoff) with diff +20/180. Window=100. Cutoff at start of week 2.
        Week 2's mean must reflect all 20 games (pre-fill), not just week-2's 10.
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        rows = []
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 1,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [50.0, 60.0],
                    played_at=wk1 + datetime.timedelta(hours=i),
                )
            )
        for i in range(10):
            rows.append(
                _make_clock_row(
                    i + 11,
                    "blitz",
                    180,
                    "checkmate",
                    "1-0",
                    "white",
                    [0, 1],
                    [80.0, 60.0],
                    played_at=wk2 + datetime.timedelta(hours=i),
                )
            )
        series = _compute_clock_pressure_timeline(rows, 100, cutoff_str="2026-01-12")
        assert len(series) == 1
        assert series[0].date == "2026-01-12"
        expected = ((10 * -10) + (10 * 20)) / 20 / 180 * 100
        assert series[0].avg_clock_diff_pct == pytest.approx(expected, abs=0.01)
        assert series[0].game_count == 20


# ---------------------------------------------------------------------------
# quick-260417-o2l: _compute_score_gap_timeline tests
# ---------------------------------------------------------------------------


def _perf_row(played_at: Any, result: str, user_color: str) -> tuple:
    """Build a row matching query_endgame_performance_rows output shape.

    Shape: (played_at, result, user_color). Used for the score-gap timeline
    where derive_user_result(result, user_color) yields the per-game outcome.
    """
    return (played_at, result, user_color)


class TestComputeScoreGapTimeline:
    """Unit tests for _compute_score_gap_timeline (quick-260417-o2l)."""

    def test_empty_inputs_returns_empty(self):
        assert _compute_score_gap_timeline([], [], 100) == []

    def test_drops_weeks_with_either_side_below_min_games(self):
        """10 endgame games + 5 non-endgame games -> no points (non_endgame < 10)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ]
        non_endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(5)
        ]
        assert _compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100) == []

    def test_emits_one_point_per_iso_week_using_rolling_diff(self):
        """Two ISO weeks; verify diff and counts evolve via the trailing window.

        Week 1: 10 endgame WINS (score=1.0) + 10 non-endgame LOSSES (score=0.0)
        Week 2: 10 endgame DRAWS (score=0.5) + 10 non-endgame WINS (score=1.0)
        Week 1 diff = 1.0 - 0.0 = +1.0.
        Week 2 windows hold all 20 games per side:
          endgame mean = (10*1 + 10*0.5) / 20 = 0.75
          non_endgame mean = (10*0 + 10*1) / 20 = 0.5
          diff = 0.75 - 0.5 = +0.25.
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1/2-1/2", "white") for i in range(10)]
        non_endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "0-1", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)]
        series = _compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100)
        assert len(series) == 2
        assert series[0].date == "2026-01-05"
        assert series[0].score_difference == pytest.approx(1.0)
        assert series[0].endgame_game_count == 10
        assert series[0].non_endgame_game_count == 10
        # Phase 68: absolute per-side means persisted.
        assert series[0].endgame_score == pytest.approx(1.0)
        assert series[0].non_endgame_score == pytest.approx(0.0)
        assert series[1].date == "2026-01-12"
        assert series[1].score_difference == pytest.approx(0.25)
        assert series[1].endgame_game_count == 20
        assert series[1].non_endgame_game_count == 20
        # endgame_mean = (10*1 + 10*0.5)/20 = 0.75
        # non_endgame_mean = (10*0 + 10*1)/20 = 0.5
        assert series[1].endgame_score == pytest.approx(0.75)
        assert series[1].non_endgame_score == pytest.approx(0.5)
        # Identity invariant: score_difference == endgame_score - non_endgame_score
        for point in series:
            assert (
                abs((point.endgame_score - point.non_endgame_score) - point.score_difference) < 1e-9
            )

    def test_rolling_window_caps_at_window_size(self):
        """window=10: week 2's diff reflects only week-2 games per side."""
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1/2-1/2", "white") for i in range(10)]
        non_endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "0-1", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)]
        series = _compute_score_gap_timeline(endgame_rows, non_endgame_rows, 10)
        assert len(series) == 2
        # Week 1: full window of week-1 only -> +1.0
        assert series[0].score_difference == pytest.approx(1.0)
        assert series[0].endgame_game_count == 10
        # Week 2: window cap drops week-1; endgame=0.5, non_endgame=1.0 -> -0.5
        assert series[1].score_difference == pytest.approx(-0.5)
        assert series[1].endgame_game_count == 10
        assert series[1].non_endgame_game_count == 10

    def test_skips_rows_without_played_at(self):
        """Rows with played_at=None are excluded from the timeline."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ] + [_perf_row(None, "1-0", "white")]
        non_endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "0-1", "white") for i in range(10)
        ]
        series = _compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100)
        assert len(series) == 1
        assert series[0].endgame_game_count == 10

    def test_compute_score_gap_material_passes_timeline_through(self):
        """_compute_score_gap_material returns the pre-computed timeline as-is."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ]
        non_endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "0-1", "white") for i in range(10)
        ]
        timeline = _compute_score_gap_timeline(
            endgame_rows, non_endgame_rows, SCORE_GAP_TIMELINE_WINDOW
        )
        endgame_wdl = EndgameWDLSummary(
            wins=10,
            draws=0,
            losses=0,
            total=10,
            win_pct=100.0,
            draw_pct=0.0,
            loss_pct=0.0,
        )
        non_endgame_wdl = EndgameWDLSummary(
            wins=0,
            draws=0,
            losses=10,
            total=10,
            win_pct=0.0,
            draw_pct=0.0,
            loss_pct=100.0,
        )
        result = _compute_score_gap_material(
            endgame_wdl,
            non_endgame_wdl,
            entry_rows=[],
            timeline=timeline,
            timeline_window=SCORE_GAP_TIMELINE_WINDOW,
        )
        assert result.timeline_window == SCORE_GAP_TIMELINE_WINDOW
        assert len(result.timeline) == 1
        assert result.timeline[0].date == "2026-01-05"
        assert result.timeline[0].score_difference == pytest.approx(1.0)

    def test_compute_score_gap_material_omits_timeline_when_absent(self):
        """Backward compat: omitting `timeline` yields an empty timeline."""
        endgame_wdl = EndgameWDLSummary(
            wins=1,
            draws=0,
            losses=0,
            total=1,
            win_pct=100.0,
            draw_pct=0.0,
            loss_pct=0.0,
        )
        non_endgame_wdl = EndgameWDLSummary(
            wins=0,
            draws=0,
            losses=1,
            total=1,
            win_pct=0.0,
            draw_pct=0.0,
            loss_pct=100.0,
        )
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows=[])
        assert result.timeline == []
        assert result.timeline_window == SCORE_GAP_TIMELINE_WINDOW

    def test_score_gap_timeline_cutoff_filters_output_but_keeps_pre_cutoff_in_window(self):
        """Cutoff drops pre-cutoff output points but the rolling window still uses them.

        Setup: 10 endgame WINS in week 1 (pre-cutoff), 10 non-endgame LOSSES
        in week 1 (pre-cutoff), 10 endgame DRAWS in week 2 (post-cutoff),
        10 non-endgame WINS in week 2 (post-cutoff). Cutoff between weeks.
        Without cutoff filtering on the window, week-2 reflects all 20 games
        per side: endgame mean 0.75, non-endgame mean 0.5, diff = +0.25.
        Without pre-fill, week-2 would only have 10 games per side and report
        endgame 0.5, non-endgame 1.0, diff = -0.5.
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1/2-1/2", "white") for i in range(10)]
        non_endgame_rows = [
            _perf_row(wk1 + datetime.timedelta(hours=i), "0-1", "white") for i in range(10)
        ] + [_perf_row(wk2 + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)]
        # Cutoff sits at the start of week 2.
        series = _compute_score_gap_timeline(
            endgame_rows, non_endgame_rows, 100, cutoff_str="2026-01-12"
        )
        assert len(series) == 1
        assert series[0].date == "2026-01-12"
        # Verifies the window pre-fill: +0.25, NOT -0.5.
        assert series[0].score_difference == pytest.approx(0.25)
        assert series[0].endgame_game_count == 20
        assert series[0].non_endgame_game_count == 20


# -----------------------------------------------------------------------------
# Phase 57 ELO-05 — Endgame ELO formula + timeline helpers
# -----------------------------------------------------------------------------


class TestConversionElo:
    """Unit tests for the Conversion ELO formula (Phase 57 D-01; renamed
    in Phase 87.4 D-06 from Endgame ELO — formula unchanged).

    Formula: round(avg_opp + 400 * log10(clamp(skill, 0.05, 0.95) /
             (1 - clamp(skill)))).
    """

    def test_formula_mid_range(self):
        # skill=0.5 -> log10(0.5/0.5) = 0 -> returns round(avg_opp).
        assert _conversion_elo_from_skill(0.5, 1500.0) == 1500
        assert _conversion_elo_from_skill(0.5, 1847.0) == 1847

    def test_clamp_boundaries_skill_zero_does_not_raise(self):
        # skill=0.0 -> clamped to 0.05 -> log10(0.05/0.95) ~ -1.279
        # -> 1500 + 400*-1.279 ~ 988
        result = _conversion_elo_from_skill(0.0, 1500.0)
        assert isinstance(result, int)
        assert result < 1500
        # Clamp at 0.05 yields approximately -510 Elo delta at the extreme.
        assert result > 900  # not <= 0, not -inf

    def test_clamp_boundaries_skill_one_does_not_raise(self):
        # skill=1.0 -> clamped to 0.95 -> log10(0.95/0.05) ~ +1.279
        # -> 1500 + 400*1.279 ~ 2012
        result = _conversion_elo_from_skill(1.0, 1500.0)
        assert isinstance(result, int)
        assert result > 1500
        assert result < 2100  # well below numeric-overflow territory

    def test_formula_above_parity_raises_elo(self):
        # skill=0.7 > 0.5 -> Elo above opponent average.
        assert _conversion_elo_from_skill(0.7, 1500.0) > 1500

    def test_formula_below_parity_lowers_elo(self):
        # skill=0.3 < 0.5 -> Elo below opponent average.
        assert _conversion_elo_from_skill(0.3, 1500.0) < 1500


# Helper for the timeline tests — mirrors the repo output tuple shape.
def _elo_bucket_row(
    played_at: Any,
    platform: str,
    tc: str,
    user_color: str,
    white_rating: int,
    black_rating: int,
    eval_cp: int | None,
    eval_mate: int | None,
    result: str,
) -> tuple:
    """Row matching query_endgame_elo_timeline_rows bucket output (9 columns).

    Columns: (played_at, platform, time_control_bucket, user_color,
              white_rating, black_rating, eval_cp, eval_mate, result)
    eval_cp and eval_mate are white-perspective Stockfish eval at span-entry ply (REFAC-02).
    """
    return (
        played_at,
        platform,
        tc,
        user_color,
        white_rating,
        black_rating,
        eval_cp,
        eval_mate,
        result,
    )


def _elo_all_row(
    played_at: Any,
    platform: str,
    tc: str,
    user_color: str,
    white_rating: int,
    black_rating: int,
) -> tuple:
    """Row matching query_endgame_elo_timeline_rows all_rows output (6 columns)."""
    return (played_at, platform, tc, user_color, white_rating, black_rating)


def _asof_arrays_from_all_rows(all_rows: list[tuple]) -> tuple[list, list[int]]:
    """Mirror the orchestrator's per-combo asof-array build for unit tests (Phase 57.1)."""
    dates: list = []
    ratings: list[int] = []
    for r in all_rows:
        if r[0] is None or r[4] is None or r[5] is None:
            continue
        dates.append(r[0])
        ratings.append(r[4] if r[3] == "white" else r[5])
    return dates, ratings


# Phase 87.4 (D-05): TestEndgameSkillFromBucketRows class deleted alongside
# _endgame_skill_from_bucket_rows. Endgame Skill concept retired end-to-end.


class TestConversionEloTimeline:
    """Unit tests for _compute_endgame_elo_weekly_series — emits Conversion ELO
    timeline points (Phase 57; revised in Phase 57.1; renamed Phase 87.4 D-06).

    Note (Phase 87.4 D-01): inputs are now drawn from windowed Conv ΔES
    (conversion-bucket rows only, terminal per-game score gap via Lichess
    sigmoid on entry-ply eval). Tests that previously fed parity-bucket
    fixtures (eval_cp=0 / draws) were updated: under the new helper those
    rows do not contribute (parity is excluded by _windowed_conv_delta_es)
    so the timeline emits zero points. The tests below use conversion-bucket
    fixtures (eval_cp > +100, sign-flipped to the user's perspective) to
    keep the emission path exercised."""

    def test_empty_inputs_returns_empty(self):
        assert _compute_endgame_elo_weekly_series([], [], 100, [], []) == []

    def test_below_min_games_dropped(self):
        """Endgame window with 9 conv-bucket games -> no point emitted (D-06 threshold = 10)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        # Phase 87.4 (D-01): conv-bucket fixture (eval_cp >= +100 from white POV).
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,  # white-perspective eval — conv-bucket for white user.
                None,
                "1-0",
            )
            for i in range(9)
        ]
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(50)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows, all_rows, 100, asof_dates, asof_ratings
        )
        assert result == []

    def test_min_games_emits_point(self):
        """Endgame window with 10 conv-bucket wins -> one point. Phase 87.4 D-01:
        per-game Conv ΔES > PIVOT, so the affine recenter pushes ``s`` above 0.5
        and conversion_elo lands above the 1500 actual_elo anchor. We assert
        ordering, not an exact value (the recenter math is unit-tested under
        TestAffineRecenter)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,  # +200cp white POV — conv-bucket.
                None,
                "1-0",
            )
            for i in range(10)
        ]
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(10)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows, all_rows, 100, asof_dates, asof_ratings
        )
        assert len(result) == 1
        # Dated to ISO-Sunday (end of week 2 = 2026-01-11). Monday was 2026-01-05.
        assert result[0].date == "2026-01-11"
        # 10 wins at +200cp (es_entry ≈ 0.68) → per-game gap ≈ +0.32. Mean is
        # well above PIVOT (-0.0474), so s clamps near 0.95 and conversion_elo
        # is the upper-clamp Phase 57 ceiling (~+510 Elo above actual).
        assert result[0].actual_elo == 1500
        assert result[0].conversion_elo > result[0].actual_elo
        assert result[0].endgame_games_in_window == 10
        # Phase 57.1: new per-week count field.
        assert result[0].per_week_endgame_games == 10

    def test_actual_elo_uses_asof_not_rolling_mean(self):
        """Actual ELO comes from per-combo asof-join (Phase 57.1 D-04), not rolling mean.

        Phase 87.4 (D-06): conversion_elo equals actual_elo iff windowed Conv ΔES
        equals PIVOT (-0.0474) via _affine_recenter_conv_delta → s = 0.5. The
        invariant itself is unit-tested under
        ``TestConversionEloInvariant.test_pivot_pipeline_invariant_actual_elo_preserved``;
        here we only assert that the asof-join anchor lands on the latest all-game
        rating (1800, not the rolling mean of 1400/1800).
        """
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        # 10 conv-bucket games at rating 1400 (per-game user_rating in bucket rows
        # no longer influences the Elo formula after Phase 57.1).
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1400,
                1400,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        # All-games at rating 1800 — the asof of the LATEST one wins.
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1800,
                1800,
            )
            for i in range(50)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        assert len(result) == 1
        # Asof returns the latest all-game's rating: 1800 (the asof anchor —
        # NOT the bucket-row 1400 rating, NOT a rolling mean).
        assert result[0].actual_elo == 1800

    def test_cutoff_str_does_not_starve_window(self):
        """Recency cutoff filters EMITTED points but window pre-fills from earlier games (Pitfall 2)."""
        # Week 1: 10 endgame games pre-cutoff (pre-fills the window).
        # Week 2: 1 endgame game post-cutoff (brings window to 11).
        # With cutoff_str = week 2's Monday, only week 2's point should emit,
        # and its window count must be 11 (not 1).
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ] + [
            _elo_bucket_row(wk2, "chess.com", "blitz", "white", 1500, 1500, 200, None, "1-0"),
        ]
        all_rows = [
            _elo_all_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(10)
        ] + [
            _elo_all_row(wk2, "chess.com", "blitz", "white", 1500, 1500),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows, all_rows, 100, asof_dates, asof_ratings, cutoff_str="2026-01-12"
        )
        assert len(result) == 1
        # Dated to ISO-Sunday (end of week 3 = 2026-01-18). Monday was 2026-01-12.
        # cutoff_str="2026-01-12" excludes week-2 point dated 2026-01-11.
        assert result[0].date == "2026-01-18"
        # Window filled with 11 games (10 pre-cutoff + 1 post-cutoff).
        assert result[0].endgame_games_in_window == 11

    def test_rolling_window_caps_at_window_size(self):
        """Window size caps at ENDGAME_ELO_TIMELINE_WINDOW (100); extra games are dropped.

        Seed 150 endgame games across a single ISO week. The emitted point's
        `endgame_games_in_window` must equal the window size (100), not 150 —
        proving the trailing slice `[-window:]` trims old events correctly.
        """
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(minutes=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(150)
        ]
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(minutes=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(150)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            ENDGAME_ELO_TIMELINE_WINDOW,
            asof_dates,
            asof_ratings,
        )
        assert len(result) >= 1
        # Last emitted point of the week reflects the fully-saturated 100-game window.
        assert result[-1].endgame_games_in_window == 100

    # --- Phase 57.1 D-18 tests (asof + per-week count) ---

    def test_actual_elo_asof_forward_fill(self):
        """Week with no games forward-fills from the latest prior game's rating (D-02).

        Week 1 has 12 endgame games at rating 1500 -> emits with actual_elo=1500.
        Week 3 has 1 game with rating 1600 -> emits with actual_elo=1600 (new asof).
        Week 2 has no games -> no emission (the helper only emits on endgame events).
        The forward-fill property is implicit: between week 1's emission and week 3's
        emission, the asof value for any intermediate week would be 1500 until the
        week-3 game updates it.
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk3 = datetime.datetime(2026, 1, 19, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(12)
        ] + [
            _elo_bucket_row(
                wk3,
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            ),
        ]
        # All-games contains the week-1 history at rating 1500 and a week-3 game at
        # rating 1600 (user's rating changed between weeks).
        all_rows = [
            _elo_all_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(12)
        ] + [
            _elo_all_row(wk3, "chess.com", "blitz", "white", 1600, 1600),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        # Week 1 emits with actual_elo=1500 (asof of week-1 latest game).
        # Week 3 emits with actual_elo=1600 (asof of week-3 game).
        assert len(result) >= 2
        assert result[0].actual_elo == 1500
        assert result[-1].actual_elo == 1600

    def test_asof_same_day_uses_last_game(self):
        """Multiple games on the same Sunday: asof picks the last game's rating (D-03)."""
        # 2026-01-11 is a Sunday (ISO week 2 of 2026).
        sunday = datetime.datetime(2026, 1, 11, 12, 0, 0)
        # 10 endgame games on the same Sunday.
        bucket_rows = [
            _elo_bucket_row(
                sunday + datetime.timedelta(minutes=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        # All-games rows: three games on the same Sunday with ratings 1500, 1550, 1600
        # (in chronological order). Asof at week-end (next Monday) must return 1600.
        all_rows = [
            _elo_all_row(
                sunday + datetime.timedelta(hours=1),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            ),
            _elo_all_row(
                sunday + datetime.timedelta(hours=2),
                "chess.com",
                "blitz",
                "white",
                1550,
                1550,
            ),
            _elo_all_row(
                sunday + datetime.timedelta(hours=3),
                "chess.com",
                "blitz",
                "white",
                1600,
                1600,
            ),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        assert len(result) == 1
        assert result[0].actual_elo == 1600  # last game on the Sunday wins

    def test_parity_only_window_emits_no_point(self):
        """Phase 87.4 (D-01): _windowed_conv_delta_es restricts the input to
        conversion-bucket rows. A window of pure parity-bucket games (eval ≈ 0)
        produces no Conv ΔES samples, so the timeline emits zero points.

        The Phase 57 "neutral skill ⇒ Conversion ELO == Actual ELO" invariant
        moved to ``TestConversionEloInvariant`` (unit test on
        ``_affine_recenter_conv_delta`` + ``_conversion_elo_from_skill``).
        """
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                0,  # parity bucket — excluded from windowed Conv ΔES.
                None,
                "1/2-1/2",
            )
            for i in range(10)
        ]
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1700,
                1700,
            )
            for i in range(10)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        assert result == []

    def test_per_combo_asof_isolation(self):
        """asof arrays are per-combo: a chess.com rating doesn't bleed into a lichess call.

        The helper itself takes per-combo arrays as inputs, so isolation is
        enforced at the orchestrator boundary. Test the helper-level contract:
        passing only chess.com asof data still uses ONLY the chess.com asof for
        actual_elo (no leak from a separate lichess pool).
        """
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1400,
                1400,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        # all_rows contains only chess.com entries (orchestrator partitions by
        # combo before calling the helper); asof arrays are derived from them.
        all_rows = [
            _elo_all_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1400,
                1400,
            )
            for i in range(10)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        # Sanity: only chess.com ratings made it into the asof arrays.
        assert max(asof_ratings) == 1400
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        assert len(result) == 1
        assert result[0].actual_elo == 1400  # chess.com rating wins, no leak

    def test_per_week_count_is_not_trailing(self):
        """per_week_endgame_games counts THIS week's games, not trailing window (D-06)."""
        # Week 1: 15 endgame games. Window fills, points emit.
        # Week 2: 12 endgame games. Window now has 27.
        # Points emitted for week 2 must have per_week_endgame_games == 12 (not 27).
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(15)
        ] + [
            _elo_bucket_row(
                wk2 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(12)
        ]
        all_rows = [
            _elo_all_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(15)
        ] + [
            _elo_all_row(
                wk2 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(12)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        # Two points emitted (one per week). Verify per-week counts.
        # Dates are ISO-Sundays (end of week): 2026-01-11 for week 2, 2026-01-18 for week 3.
        assert len(result) == 2
        wk1_pt = next(p for p in result if p.date == "2026-01-11")
        wk2_pt = next(p for p in result if p.date == "2026-01-18")
        assert wk1_pt.per_week_endgame_games == 15
        assert wk2_pt.per_week_endgame_games == 12  # NOT 27 (trailing window)
        # endgame_games_in_window IS the trailing window:
        assert wk2_pt.endgame_games_in_window == 27

    def test_no_prior_game_does_not_emit(self):
        """Empty asof arrays -> bisect returns idx=0 -> no emission (defensive skip)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        bucket_rows = [
            _elo_bucket_row(
                monday + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        all_rows: list[tuple] = []  # no all-games rows -> empty asof
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            [],
            [],
        )
        assert result == []

    def test_asof_cutoff_pinned_to_midnight_no_week_bleed(self):
        """Regression for Phase 57.1 WR-01.

        Previously next_monday_dt carried the triggering played_at's time-of-day,
        so the bisect_right cutoff drifted up to 24h into the next ISO week and
        a Monday-morning rating (week N+1) could leak into week N's actual_elo.

        Setup: 10 endgame games on Sunday 2026-01-11 at 14:00 (ISO week 2, rating
        1500) plus a Monday-morning 2026-01-12 at 08:00 all-game with a fresh
        rating of 1600 (ISO week 3). With the bug, asof for week 2 would return
        1600 because the cutoff (Mon 14:00) > Mon 08:00. Fixed: cutoff is
        Mon 00:00 so week 2's actual_elo stays 1500.
        """
        sunday = datetime.datetime(2026, 1, 11, 14, 0, 0)  # ISO week 2, Sunday
        bucket_rows = [
            _elo_bucket_row(
                sunday + datetime.timedelta(minutes=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        # All-games: 10 week-2 games at rating 1500 + a Monday-morning week-3
        # game at rating 1600. The cutoff for week 2's emission must be
        # Mon 2026-01-12 00:00, not Mon 14:00, so the 08:00 game is excluded.
        all_rows = [
            _elo_all_row(
                sunday + datetime.timedelta(minutes=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(10)
        ] + [
            _elo_all_row(
                datetime.datetime(2026, 1, 12, 8, 0, 0),  # Monday 08:00 week 3
                "chess.com",
                "blitz",
                "white",
                1600,
                1600,
            ),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        # Scoped strictly to WR-01: week 2's actual_elo must NOT see the
        # Monday-morning 1600 rating (cutoff pinned to midnight excludes it).
        # A separate WR-02 regression test covers whether a week-3 point is
        # emitted at all off an "all" event.
        # Point dated to ISO-Sunday (2026-01-11, end of ISO week 2).
        wk2_pt = next(p for p in result if p.date == "2026-01-11")
        assert wk2_pt.actual_elo == 1500  # NOT 1600 — no week-3 bleed

    def test_all_events_do_not_trigger_emission_in_fresh_week(self):
        """Regression for Phase 57.1 WR-02.

        Setup: 10 endgame games in ISO week 1 (saturates window), plus 3
        all-games in ISO week 2 with NO endgame games that week. Before the
        fix, each week-2 all-game triggered an emission with
        per_week_endgame_games=0, contradicting the "only emits on endgame
        events" contract. After the fix, only the week-1 emission should
        appear — no week-2 point at all.
        """
        wk1 = datetime.datetime(2026, 1, 5, 12, 0, 0)  # ISO week 1 Monday
        wk2 = datetime.datetime(2026, 1, 12, 12, 0, 0)  # ISO week 2 Monday
        bucket_rows = [
            _elo_bucket_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
                200,
                None,
                "1-0",
            )
            for i in range(10)
        ]
        all_rows = [
            _elo_all_row(
                wk1 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1500,
                1500,
            )
            for i in range(10)
        ] + [
            _elo_all_row(
                wk2 + datetime.timedelta(hours=i),
                "chess.com",
                "blitz",
                "white",
                1600,
                1600,
            )
            for i in range(3)
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        result = _compute_endgame_elo_weekly_series(
            bucket_rows,
            all_rows,
            100,
            asof_dates,
            asof_ratings,
        )
        # Only week 1 should emit (where endgame games actually happened).
        # Week 2 must NOT be in the result even though "all" events fall there.
        # Dates are ISO-Sundays (end of week): 2026-01-11 for ISO week 2,
        # 2026-01-18 for ISO week 3.
        dates = {p.date for p in result}
        assert "2026-01-11" in dates  # week 1 present
        assert "2026-01-18" not in dates  # week 2 absent (no endgame events)
        # And the week-1 point carries its true per-week count.
        wk1_pt = next(p for p in result if p.date == "2026-01-11")
        assert wk1_pt.per_week_endgame_games == 10


# Sanity check: EndgameEloTimelinePoint is actually exported from the schema.
# Phase 87.4 (D-06): per-point field renamed endgame_elo → conversion_elo.
def test_endgame_elo_timeline_point_constructs():
    pt = EndgameEloTimelinePoint(
        date="2026-01-05",
        conversion_elo=1500,
        actual_elo=1480,
        endgame_games_in_window=42,
        per_week_endgame_games=8,
    )
    assert pt.conversion_elo == 1500
    assert pt.endgame_games_in_window == 42
    assert pt.per_week_endgame_games == 8


class TestEntryEvalAggregation:
    """Phase 81 (D-07, D-08, D-10, D-11, D-12) — entry-eval / endgame-score aggregation
    inside `_get_endgame_performance_from_rows`.

    Phase 81 UAT amendment: aggregation now consumes bucket_rows (one row per game,
    eval at first chronological endgame position) instead of per-class entry_rows.
    The per-game dedup is gone — bucket_rows already returns one row per game.

    Covers:
      - sign flip for black users
      - mate / NULL exclusion (D-07)
      - n < 10 -> p_value is None (D-11)
      - endgame_score_p_value gated on endgame_wdl.total >= 10 (D-08)
      - CI bound exposure for the bullet whisker
    """

    def _bucket(
        self,
        game_id: int,
        endgame_class: int = 1,
        result: str = "1-0",
        user_color: str = "white",
        eval_cp: int | None = 0,
        eval_mate: int | None = None,
    ) -> _FakeRow:
        """Build a single bucket-row stand-in mirroring query_endgame_bucket_rows columns.

        Tuple shape matches query_endgame_entry_rows; the difference is that
        bucket_rows returns one row per game (not per (game, class)).
        """
        return _FakeRow(
            game_id=game_id,
            endgame_class=endgame_class,
            result=result,
            user_color=user_color,
            eval_cp=eval_cp,
            eval_mate=eval_mate,
        )

    def _wdl_rows(self, wins: int, draws: int, losses: int) -> list[Any]:
        """Build (played_at, result, user_color) WDL rows for endgame_rows / non_endgame_rows."""
        rows: list[Any] = []
        d = 0
        for _ in range(wins):
            rows.append(_row("1-0", "white", d))
            d += 1
        for _ in range(draws):
            rows.append(_row("1/2-1/2", "white", d))
            d += 1
        for _ in range(losses):
            rows.append(_row("0-1", "white", d))
            d += 1
        return rows

    def test_empty_bucket_rows_yields_defaults(self) -> None:
        """No bucket_rows -> n=0, mean=0.0, p_value=None, CI bounds None."""
        resp = _get_endgame_performance_from_rows(
            endgame_rows=[],
            non_endgame_rows=[],
            bucket_rows=[],
        )
        assert resp.entry_eval_n == 0
        assert resp.entry_eval_mean_pawns == 0.0
        assert resp.entry_eval_p_value is None
        assert resp.entry_eval_ci_low_pawns is None
        assert resp.entry_eval_ci_high_pawns is None

    def test_n_nine_p_value_gated_to_none(self) -> None:
        """9 distinct games at eval_cp=200 -> n=9, p_value None (n < 10 reliability gate)."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=200) for i in range(9)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=9, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 9
        assert resp.entry_eval_p_value is None
        # Mean still computed (D-11 only gates p_value)
        assert resp.entry_eval_mean_pawns == pytest.approx(2.0)

    def test_n_ten_with_zero_mean_yields_p_close_to_one(self) -> None:
        """10 games at eval_cp=0 -> n=10, mean=0.0, p_value ~ 1.0."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 10
        assert resp.entry_eval_mean_pawns == 0.0
        assert resp.entry_eval_p_value is not None
        assert resp.entry_eval_p_value == pytest.approx(1.0)

    def test_one_row_per_game(self) -> None:
        """bucket_rows returns one row per game; no per-game dedupe needed.

        Three rows with distinct game_ids count as three games.
        """
        bucket_rows = [
            self._bucket(game_id=1, eval_cp=100),
            self._bucket(game_id=2, eval_cp=100),
            self._bucket(game_id=3, eval_cp=100),
        ]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=3, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 3
        assert resp.entry_eval_mean_pawns == pytest.approx(1.0)

    def test_sign_flip_for_black_users(self) -> None:
        """Black user with raw eval_cp=200 -> mean_pawns=-2.0 (user-perspective sign flip)."""
        bucket_rows = [self._bucket(game_id=i, user_color="black", eval_cp=200) for i in range(10)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 10
        assert resp.entry_eval_mean_pawns == pytest.approx(-2.0)

    def test_mate_row_excluded_from_aggregation(self) -> None:
        """Row with eval_mate set is excluded; eval_cp rows are counted."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=5))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 10  # mate row dropped

    def test_null_eval_row_excluded_from_aggregation(self) -> None:
        """Row with both eval_cp and eval_mate None is excluded."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=None))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 10

    def test_endgame_score_p_value_gated_below_n_ten(self) -> None:
        """endgame_wdl.total < 10 -> endgame_score_p_value is None; >= 10 -> float."""
        # Below gate
        resp_low = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=3, draws=2, losses=1),  # total=6
            non_endgame_rows=[],
            bucket_rows=[],
        )
        assert resp_low.endgame_score_p_value is None

        # At/above gate
        resp_ok = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),  # total=10
            non_endgame_rows=[],
            bucket_rows=[],
        )
        assert resp_ok.endgame_score_p_value is not None
        assert isinstance(resp_ok.endgame_score_p_value, float)
        assert 0.0 <= resp_ok.endgame_score_p_value <= 1.0

    def test_non_endgame_score_p_value_gated_below_n_ten(self) -> None:
        """non_endgame_wdl.total < 10 -> non_endgame_score_p_value is None; >= 10 -> float.

        Mirror of test_endgame_score_p_value_gated_below_n_ten for the Section 1
        'Games without Endgame' card (Phase 85 D-01). Kept independent of endgame_rows
        so a future refactor that splits the two p-values still passes.
        """
        # Below gate
        resp_low = _get_endgame_performance_from_rows(
            endgame_rows=[],
            non_endgame_rows=self._wdl_rows(wins=3, draws=2, losses=1),  # total=6
            bucket_rows=[],
        )
        assert resp_low.non_endgame_score_p_value is None

        # At/above gate
        resp_ok = _get_endgame_performance_from_rows(
            endgame_rows=[],
            non_endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),  # total=10
            bucket_rows=[],
        )
        assert resp_ok.non_endgame_score_p_value is not None
        assert isinstance(resp_ok.non_endgame_score_p_value, float)
        assert 0.0 <= resp_ok.non_endgame_score_p_value <= 1.0

    def test_ci_bounds_set_when_n_ge_two(self) -> None:
        """When n >= 2, both CI bounds are floats; below n=2 they are None."""
        # n=10 -> CI bounds set
        bucket_rows = [self._bucket(game_id=i, eval_cp=100) for i in range(10)]
        resp_ok = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp_ok.entry_eval_ci_low_pawns is not None
        assert resp_ok.entry_eval_ci_high_pawns is not None
        # CI is centered on the mean (1.0 pawns); bounds should bracket it
        assert resp_ok.entry_eval_ci_low_pawns <= resp_ok.entry_eval_mean_pawns
        assert resp_ok.entry_eval_ci_high_pawns >= resp_ok.entry_eval_mean_pawns

        # n=1 -> CI bounds are None (variance undefined)
        resp_one = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=1, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=[self._bucket(game_id=1, eval_cp=200)],
        )
        assert resp_one.entry_eval_ci_low_pawns is None
        assert resp_one.entry_eval_ci_high_pawns is None


class TestEntryExpectedScore(TestEntryEvalAggregation):
    """Phase 83 Plan 2 (D-04..D-07, D-21, D-22) — entry_expected_score aggregator
    inside `_get_endgame_performance_from_rows`.

    Reuses the `_bucket` / `_wdl_rows` fixtures from TestEntryEvalAggregation via
    subclassing so we get the same fake-row shape.

    Cohort divergence from entry_eval (D-06): mate games are INCLUDED in the
    expected-score cohort (mate-for-user -> 1.0, mate-against -> 0.0) but
    excluded from entry_eval_mean_pawns. Asserts on this inversion explicitly.

    Cohort clip (D-07): |eval_cp| >= 2000 rows are DROPPED — the sigmoid
    saturates around +/-800 cp anyway and the clip matches Phase 82's
    "analyzable endgame entry" definition.
    """

    def test_entry_expected_score_empty_defaults(self) -> None:
        """No bucket_rows -> entry_expected_score = 0.0, n = 0, p_value/CI = None."""
        resp = _get_endgame_performance_from_rows(
            endgame_rows=[],
            non_endgame_rows=[],
            bucket_rows=[],
        )
        assert resp.entry_expected_score == 0.0
        assert resp.entry_expected_score_n == 0
        assert resp.entry_expected_score_p_value is None
        assert resp.entry_expected_score_ci_low is None
        assert resp.entry_expected_score_ci_high is None

    def test_entry_expected_score_centered_when_eval_zero(self) -> None:
        """10 rows at eval_cp=0 -> sigmoid -> 0.5; p_value ~ 1.0 (no evidence)."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=5, draws=0, losses=5),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        assert resp.entry_expected_score == pytest.approx(0.5, abs=1e-9)
        assert resp.entry_expected_score_p_value is not None
        assert resp.entry_expected_score_p_value == pytest.approx(1.0, abs=1e-9)

    def test_entry_expected_score_n_nine_p_value_gated(self) -> None:
        """n=9 -> score computed, but p_value gated to None (n < 10 reliability gate)."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(9)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=5, draws=0, losses=4),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 9
        assert resp.entry_expected_score == pytest.approx(0.5, abs=1e-9)
        assert resp.entry_expected_score_p_value is None

    def test_entry_expected_score_sign_flip_black(self) -> None:
        """10 rows at eval_cp=+200 with user_color=black -> sigmoid sign-flip ->
        expected score < 0.5 (specifically the (1 - white-perspective) mirror)."""
        bucket_rows = [self._bucket(game_id=i, user_color="black", eval_cp=200) for i in range(10)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        assert resp.entry_expected_score < 0.5
        # 1 / (1 + exp(0.00368208 * 200)) ~ 0.3239
        assert resp.entry_expected_score == pytest.approx(0.3239, abs=1e-3)

    def test_entry_expected_score_mate_INCLUDED(self) -> None:
        """D-06 inversion vs entry_eval: mate row contributes 1.0 (for user)
        or 0.0 (against user) to expected-score cohort, while entry_eval drops it.

        With 10 cp-rows (eval_cp=0 -> 0.5 each) + 1 mate-for-user row (-> 1.0):
          entry_eval_n      == 10       (mate dropped)
          entry_expected_n  == 11       (mate INCLUDED)
          entry_expected_score = (10 * 0.5 + 1.0) / 11 ~ 0.5454
        """
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=5, user_color="white"))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_eval_n == 10  # mate dropped (Phase 81 cohort unchanged)
        assert resp.entry_expected_score_n == 11  # mate INCLUDED (D-06)
        assert resp.entry_expected_score_n > resp.entry_eval_n
        # (10 * 0.5 + 1.0) / 11 = 6.0 / 11 ~ 0.5454...
        assert resp.entry_expected_score == pytest.approx(6.0 / 11.0, abs=1e-9)

    def test_entry_expected_score_mate_against_user_is_zero(self) -> None:
        """Mate-against-user (eval_mate=-5 for white-user) contributes 0.0."""
        # Single mate-against-user row -> score = 0.0
        bucket_rows = [self._bucket(game_id=1, eval_cp=None, eval_mate=-5, user_color="white")]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=0, draws=0, losses=1),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 1
        assert resp.entry_expected_score == 0.0

    def test_entry_expected_score_eval_cp_clip(self) -> None:
        """|eval_cp| >= 2000 rows are dropped (D-07). 9 normal rows + 1 clipped
        row -> n = 9."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=100) for i in range(9)]
        bucket_rows.append(self._bucket(game_id=10, eval_cp=2500))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=9, draws=0, losses=1),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 9  # clipped row dropped

    def test_entry_expected_score_eval_cp_clip_boundary(self) -> None:
        """|eval_cp| == 2000 is the clip boundary — also dropped (>=, not >)."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        bucket_rows.append(self._bucket(game_id=11, eval_cp=2000))
        bucket_rows.append(self._bucket(game_id=12, eval_cp=-2000))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=5, draws=0, losses=5),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10  # both boundary rows dropped

    def test_entry_expected_score_null_eval_dropped(self) -> None:
        """Row with both eval_cp and eval_mate None is dropped from the cohort."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=None))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=5, draws=0, losses=6),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10

    def test_entry_expected_score_ci_bounds_set_when_n_ge_two(self) -> None:
        """n >= 2 -> both CI bounds are floats in [0, 1]; n < 2 -> None."""
        # n=10 above-baseline (eval_cp=200 white) -> score > 0.5, CI brackets it
        bucket_rows = [self._bucket(game_id=i, eval_cp=200) for i in range(10)]
        resp_ok = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=6, draws=0, losses=4),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp_ok.entry_expected_score_ci_low is not None
        assert resp_ok.entry_expected_score_ci_high is not None
        assert 0.0 <= resp_ok.entry_expected_score_ci_low <= 1.0
        assert 0.0 <= resp_ok.entry_expected_score_ci_high <= 1.0
        assert resp_ok.entry_expected_score_ci_low <= resp_ok.entry_expected_score
        assert resp_ok.entry_expected_score_ci_high >= resp_ok.entry_expected_score

        # n=1 -> CI bounds are None (Wilson bounds defensive guard returns
        # (0, 1) which is not meaningful for narration)
        resp_one = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=1, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=[self._bucket(game_id=1, eval_cp=200)],
        )
        assert resp_one.entry_expected_score_ci_low is None
        assert resp_one.entry_expected_score_ci_high is None

    def test_entry_expected_score_p_value_significant_when_strong(self) -> None:
        """Strong evidence (10 rows at eval_cp=+800 white-user, score ~ 0.95)
        -> p_value < 0.05."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=800) for i in range(10)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=10, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        assert resp.entry_expected_score > 0.9
        assert resp.entry_expected_score_p_value is not None
        assert resp.entry_expected_score_p_value < 0.05

    def test_entry_eval_unchanged_by_phase_83(self) -> None:
        """Sanity: Phase 81's entry_eval_n is byte-for-byte preserved when
        the cohort contains a mix of cp / mate / clipped / null rows."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=100) for i in range(8)]
        bucket_rows.append(self._bucket(game_id=9, eval_cp=None, eval_mate=5))
        bucket_rows.append(self._bucket(game_id=10, eval_cp=2500))
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=None))
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=8, draws=0, losses=3),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        # Phase 81 cohort: mate excluded, NULL excluded, no |eval_cp| clip.
        # 8 normal + 0 mate + 1 large-cp (Phase 81 didn't clip) + 0 null = 9.
        assert resp.entry_eval_n == 9
        # Phase 83 cohort: mate INCLUDED, NULL excluded, |eval_cp| >= 2000 clipped.
        # 8 normal + 1 mate + 0 clipped + 0 null = 9.
        assert resp.entry_expected_score_n == 9


class TestScoreGapMaterialScoreDifferenceTest(TestScoreGapMaterial):
    """Phase 85.1 Plan 02 Task 2 — score_difference_p_value / ci_low / ci_high
    on ScoreGapMaterialResponse via compute_score_difference_test.

    Reuses _make_wdl / _make_wdl_pct from TestScoreGapMaterial.
    Mirrors the n-gate pattern of test_endgame_score_p_value_gated_below_n_ten
    on TestEntryEvalAggregation, but for the *two-sample* test on the score
    difference between endgame and non-endgame cohorts.
    """

    def test_score_difference_p_value_below_gate_either_side(self) -> None:
        """min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N
        -> score_difference_p_value is None on either side."""
        # endgame side below gate
        resp_eg_low = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(3, 2, 1),  # total=6 < 10
            non_endgame_wdl=self._make_wdl(10, 0, 0),  # total=10
            entry_rows=[],
        )
        assert resp_eg_low.score_difference_p_value is None

        # non-endgame side below gate
        resp_ne_low = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(10, 0, 0),  # total=10
            non_endgame_wdl=self._make_wdl(3, 2, 1),  # total=6 < 10
            entry_rows=[],
        )
        assert resp_ne_low.score_difference_p_value is None

    def test_score_difference_p_value_at_gate_both_sides(self) -> None:
        """min(eg, ne) >= PVALUE_RELIABILITY_MIN_N -> float in [0, 1]."""
        resp = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(6, 0, 4),  # total=10, score=0.6
            non_endgame_wdl=self._make_wdl(5, 0, 5),  # total=10, score=0.5
            entry_rows=[],
        )
        assert resp.score_difference_p_value is not None
        assert isinstance(resp.score_difference_p_value, float)
        assert 0.0 <= resp.score_difference_p_value <= 1.0

    def test_score_difference_se_zero_short_circuit(self) -> None:
        """All-wins endgame + all-losses non-endgame (both n>=10) -> SE_diff=0,
        scores differ -> p_value=0.0 (perfectly determined signal)."""
        resp = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(10, 0, 0),  # score=1.0, var=0
            non_endgame_wdl=self._make_wdl(0, 0, 10),  # score=0.0, var=0
            entry_rows=[],
        )
        assert resp.score_difference_p_value == 0.0

    def test_score_difference_ci_below_gate(self) -> None:
        """min(eg, ne) < 2 -> ci_low / ci_high are None."""
        resp = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(1, 0, 0),  # n=1
            non_endgame_wdl=self._make_wdl(10, 0, 0),  # n=10
            entry_rows=[],
        )
        assert resp.score_difference_ci_low is None
        assert resp.score_difference_ci_high is None

    def test_score_difference_ci_at_gate_both_sides(self) -> None:
        """min(eg, ne) >= 2 -> ci_low <= score_difference <= ci_high."""
        resp = _compute_score_gap_material(
            endgame_wdl=self._make_wdl(6, 0, 4),  # score=0.6
            non_endgame_wdl=self._make_wdl(4, 0, 6),  # score=0.4
            entry_rows=[],
        )
        assert resp.score_difference_ci_low is not None
        assert resp.score_difference_ci_high is not None
        assert resp.score_difference_ci_low <= resp.score_difference
        assert resp.score_difference_ci_high >= resp.score_difference


class TestAchievableScoreGap(TestEntryEvalAggregation):
    """Phase 85.1 Plan 02 Task 2 — achievable_score_gap + p_value + ci_*
    on EndgamePerformanceResponse via compute_paired_difference_test.

    Reuses _bucket / _wdl_rows from TestEntryEvalAggregation. The paired-diff
    accumulator is merged into the existing ex_sum/ex_n loop, so it must
    apply the SAME filter (mate INCLUDED, NULL eval dropped, |eval_cp| >= 2000
    clipped). The d_n == ex_n invariant follows by construction.
    """

    def test_achievable_score_gap_empty_defaults(self) -> None:
        """Empty bucket_rows -> mean 0.0, p/CI None."""
        resp = _get_endgame_performance_from_rows(
            endgame_rows=[],
            non_endgame_rows=[],
            bucket_rows=[],
        )
        assert resp.achievable_score_gap == 0.0
        assert resp.achievable_score_gap_p_value is None
        assert resp.achievable_score_gap_ci_low is None
        assert resp.achievable_score_gap_ci_high is None

    def test_achievable_score_gap_n_nine_p_value_gated(self) -> None:
        """n=9 surviving rows -> mean is float, p_value is None
        (n < PVALUE_RELIABILITY_MIN_N), CI bounds are floats (n >= 2)."""
        # 9 white-user wins at eval_cp=0 (sigmoid -> 0.5; actual=1.0, diff=0.5)
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(9)]
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=9, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 9
        # Mean: actual=1.0, expected=0.5 -> diff=0.5 each, mean=0.5.
        assert resp.achievable_score_gap == pytest.approx(0.5, abs=1e-9)
        # p_value gated (n < 10).
        assert resp.achievable_score_gap_p_value is None
        # CI bounds defined (n >= 2 — all diffs identical so CI collapses to mean).
        assert resp.achievable_score_gap_ci_low == pytest.approx(0.5, abs=1e-9)
        assert resp.achievable_score_gap_ci_high == pytest.approx(0.5, abs=1e-9)

    def test_achievable_score_gap_n_one_ci_none(self) -> None:
        """n=1 surviving row -> CI bounds None (Bessel variance undefined),
        p_value None (n < 10), mean still computed."""
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=1, draws=0, losses=0),
            non_endgame_rows=[],
            bucket_rows=[self._bucket(game_id=1, eval_cp=0)],
        )
        assert resp.entry_expected_score_n == 1
        # Mean still computed: actual=1.0, expected=0.5 -> diff=0.5.
        assert resp.achievable_score_gap == pytest.approx(0.5, abs=1e-9)
        assert resp.achievable_score_gap_p_value is None
        assert resp.achievable_score_gap_ci_low is None
        assert resp.achievable_score_gap_ci_high is None

    def test_achievable_score_gap_all_zero_diffs_collapses(self) -> None:
        """n=10 with d_i=0 for all (actual=expected) -> SE=0, p_value=1.0,
        CI collapses to mean_d=0."""
        # Each row: white user, eval_cp=0 -> expected=0.5; draw -> actual=0.5; diff=0.
        bucket_rows = [self._bucket(game_id=i, result="1/2-1/2", eval_cp=0) for i in range(10)]
        # WDL must reflect the same 10 draws so the function's invariants hold.
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=0, draws=10, losses=0),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        assert resp.achievable_score_gap == pytest.approx(0.0, abs=1e-9)
        # SE=0 variance-0 trap with mean==0 -> p_value=1.0.
        assert resp.achievable_score_gap_p_value == pytest.approx(1.0, abs=1e-9)
        # CI half-width collapses to 0 (SE=0).
        assert resp.achievable_score_gap_ci_low == pytest.approx(0.0, abs=1e-9)
        assert resp.achievable_score_gap_ci_high == pytest.approx(0.0, abs=1e-9)

    def test_achievable_score_gap_known_mean_at_n_ten(self) -> None:
        """Hand-computed: 10 white-user games, all eval_cp=0 (expected=0.5),
        5 wins (actual=1.0) + 5 losses (actual=0.0) -> diffs alternate +0.5 / -0.5
        -> mean=0.0, p_value high (no signal), CI brackets 0."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(10)]
        # First 5 rows are wins; remaining 5 are losses. Match WDL rows.
        for i in range(5, 10):
            bucket_rows[i] = self._bucket(game_id=i, eval_cp=0, result="0-1")
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=5, draws=0, losses=5),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        # Diffs: 5 * (+0.5) + 5 * (-0.5) = 0 -> mean = 0.
        assert resp.achievable_score_gap == pytest.approx(0.0, abs=1e-9)
        # Mean is exactly 0 against H0=0 -> p_value=1.0.
        assert resp.achievable_score_gap_p_value is not None
        assert resp.achievable_score_gap_p_value == pytest.approx(1.0, abs=1e-9)
        # CI bounds defined and bracket the mean (0).
        assert resp.achievable_score_gap_ci_low is not None
        assert resp.achievable_score_gap_ci_high is not None
        assert resp.achievable_score_gap_ci_low <= 0.0 <= resp.achievable_score_gap_ci_high

    def test_achievable_score_gap_d_n_equals_ex_n_invariant(self) -> None:
        """The paired-diff accumulator filter must match ex_n filter exactly:
        mate INCLUDED, NULL dropped, |eval_cp| >= 2000 clipped. So a mixed
        cohort with all three exclusions still yields d_n == ex_n."""
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(8)]
        bucket_rows.append(self._bucket(game_id=9, eval_cp=None, eval_mate=5))  # mate INCLUDED
        bucket_rows.append(self._bucket(game_id=10, eval_cp=2500))  # clipped
        bucket_rows.append(self._bucket(game_id=11, eval_cp=None, eval_mate=None))  # NULL dropped
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=8, draws=0, losses=3),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        # 8 normal + 1 mate (included) - 1 clipped - 1 null = 9.
        assert resp.entry_expected_score_n == 9
        # achievable_score_gap mean must be defined (not 0.0 default) -- check
        # that paired-diff loop ran on the same 9 rows.
        # 8 wins at eval_cp=0: actual=1.0 expected=0.5 -> diff=0.5 each (sum=4.0)
        # 1 mate-for-white-user (eval_mate=5, result="1-0"): actual=1.0 expected=1.0 -> diff=0
        # Total sum = 4.0, mean = 4.0 / 9 ~ 0.4444
        assert resp.achievable_score_gap == pytest.approx(4.0 / 9.0, abs=1e-9)

    def test_achievable_score_gap_ci_brackets_mean_when_n_ge_two(self) -> None:
        """n >= 2 with non-zero variance -> CI brackets mean strictly."""
        # 5 wins at eval_cp=0 (diff=+0.5) + 5 losses at eval_cp=0 (diff=-0.5)
        # but skewed to give a non-zero mean.
        bucket_rows = [self._bucket(game_id=i, eval_cp=0) for i in range(7)]  # wins -> diff=+0.5
        for i in range(7, 10):
            bucket_rows.append(
                self._bucket(game_id=i, eval_cp=0, result="0-1")
            )  # losses -> diff=-0.5
        resp = _get_endgame_performance_from_rows(
            endgame_rows=self._wdl_rows(wins=7, draws=0, losses=3),
            non_endgame_rows=[],
            bucket_rows=bucket_rows,
        )
        assert resp.entry_expected_score_n == 10
        # Mean: (7 * 0.5 + 3 * -0.5) / 10 = (3.5 - 1.5) / 10 = 0.2.
        assert resp.achievable_score_gap == pytest.approx(0.2, abs=1e-9)
        assert resp.achievable_score_gap_ci_low is not None
        assert resp.achievable_score_gap_ci_high is not None
        # Variance non-zero so CI is a strict bracket.
        assert resp.achievable_score_gap_ci_low < resp.achievable_score_gap
        assert resp.achievable_score_gap_ci_high > resp.achievable_score_gap


class TestPValueReliabilityMinNConstantAndSchemaDefaults:
    """Phase 85.1 Plan 02 Task 1 — n-gate constant + new schema fields (defaults only).

    Task 1 is a pure scaffolding step: extracts PVALUE_RELIABILITY_MIN_N to replace
    the four bare `10` occurrences (REVIEW IN-01 carry-forward) and adds the new
    p-value / CI / mean fields to ScoreGapMaterialResponse + EndgamePerformanceResponse
    with safe defaults. Wiring of real values is Task 2's job.
    """

    def test_pvalue_reliability_min_n_constant_exposed(self) -> None:
        """PVALUE_RELIABILITY_MIN_N is exported from endgame_service and equals 10
        (matches the previous bare-10 wire-format gate)."""
        from app.services import endgame_service

        assert hasattr(endgame_service, "PVALUE_RELIABILITY_MIN_N")
        assert endgame_service.PVALUE_RELIABILITY_MIN_N == 10

    def test_endgame_performance_response_defaults_for_new_fields(self) -> None:
        """EndgamePerformanceResponse carries the 4 new achievable_* fields with
        documented defaults (mean=0.0 always-present; p/CI None below gate)."""
        from app.schemas.endgames import (
            EndgamePerformanceResponse,
            EndgameWDLSummary,
        )

        empty_wdl = EndgameWDLSummary(
            wins=0, draws=0, losses=0, total=0, win_pct=0.0, draw_pct=0.0, loss_pct=0.0
        )
        resp = EndgamePerformanceResponse(
            endgame_wdl=empty_wdl,
            non_endgame_wdl=empty_wdl,
            endgame_win_rate=0.0,
        )
        # Always-present mean (matches the entry_expected_score / entry_eval_mean_pawns pattern).
        assert resp.achievable_score_gap == 0.0
        # Gated p/CI default to None (mirror entry_expected_score_p_value / ci_*).
        assert resp.achievable_score_gap_p_value is None
        assert resp.achievable_score_gap_ci_low is None
        assert resp.achievable_score_gap_ci_high is None

    def test_score_gap_material_response_defaults_for_new_fields(self) -> None:
        """ScoreGapMaterialResponse carries the 3 new score_difference_* fields,
        all None by default (matches the entry_*_p_value / ci_* convention)."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        resp = ScoreGapMaterialResponse(
            endgame_score=0.0,
            non_endgame_score=0.0,
            score_difference=0.0,
            material_rows=[],
            timeline=[],
            timeline_window=0,
        )
        assert resp.score_difference_p_value is None
        assert resp.score_difference_ci_low is None
        assert resp.score_difference_ci_high is None

    def test_score_gap_material_response_defaults_for_phase872_score_gap_fields(self) -> None:
        """Phase 87.2 (SEC2-ΔES-02 / D-06): ScoreGapMaterialResponse carries 20 new
        section2_score_gap_* fields (4 buckets x 5 fields), all None by default.
        The deleted Phase 86 fields (skill, opp_skill, skill_diff_*) are gone."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        resp = ScoreGapMaterialResponse(
            endgame_score=0.0,
            non_endgame_score=0.0,
            score_difference=0.0,
            material_rows=[],
            timeline=[],
            timeline_window=0,
        )
        # New fields all default to None.
        # Phase 87.4 (D-05): "skill" bucket dropped — composite retired.
        for bucket in ("conv", "parity", "recov"):
            assert getattr(resp, f"section2_score_gap_{bucket}_mean") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_n") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_p_value") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_ci_low") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_ci_high") is None
        # Deleted Phase 86 fields must not exist
        assert not hasattr(resp, "skill")
        assert not hasattr(resp, "opp_skill")
        assert not hasattr(resp, "skill_diff_p_value")
        # Phase 87.4 (D-05): the section2_score_gap_skill_* family + the
        # endgame_skill_rate_mean gauge driver were dropped end-to-end.
        for f in (
            "section2_score_gap_skill_mean",
            "section2_score_gap_skill_n",
            "section2_score_gap_skill_p_value",
            "section2_score_gap_skill_ci_low",
            "section2_score_gap_skill_ci_high",
            "endgame_skill_rate_mean",
        ):
            assert not hasattr(resp, f), f"unexpected residual field: {f}"

    def test_material_row_construction_without_deleted_fields(self) -> None:
        """Phase 87.2 (D-05): MaterialRow no longer has opponent_score,
        opponent_games, diff_p_value, diff_ci_low, diff_ci_high.
        Constructing without those kwargs succeeds."""
        from app.schemas.endgames import MaterialRow

        row = MaterialRow(
            bucket="parity",
            label="Parity",
            games=0,
            win_pct=0.0,
            draw_pct=0.0,
            loss_pct=0.0,
            score=0.0,
        )
        # Deleted fields must not exist
        assert not hasattr(row, "opponent_score")
        assert not hasattr(row, "opponent_games")
        assert not hasattr(row, "diff_p_value")
        assert not hasattr(row, "diff_ci_low")
        assert not hasattr(row, "diff_ci_high")


class TestSkillDiffTestWireFields(TestScoreGapMaterial):
    """Phase 86 Plan 02 Task 3 tests replaced in Phase 87.2 (D-05).

    The 5 Skill + 3 per-MaterialRow rate-diff fields (compute_skill_diff_test,
    compute_per_bucket_diff_test) were deleted as part of the mirror-bucket
    plumbing retirement. The per-bucket Delta-ES Score Gap wiring tests live in
    TestPhase872PerBucketMath (Task 2) instead.

    Class retained to avoid renumbering downstream test IDs.
    """

    def test_material_rows_have_no_diff_fields_after_phase872(self) -> None:
        """Sanity check: _compute_score_gap_material returns MaterialRows without
        the deleted diff_p_value / diff_ci_low / diff_ci_high fields (Phase 87.2 D-05)."""
        entry_rows: list[_FakeRow] = []
        for i in range(30):
            entry_rows.append(_FakeRow(i + 1, 1, "1-0", "white", 200, None))
        for i in range(30):
            entry_rows.append(_FakeRow(i + 31, 1, "1/2-1/2", "white", 0, None))
        for i in range(30):
            entry_rows.append(_FakeRow(i + 61, 1, "0-1", "white", -200, None))

        endgame_wdl = self._make_wdl(30, 30, 30)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        resp = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)

        for row in resp.material_rows:
            assert not hasattr(row, "diff_p_value"), f"bucket={row.bucket}"
            assert not hasattr(row, "diff_ci_low")
            assert not hasattr(row, "diff_ci_high")
            assert not hasattr(row, "opponent_score")
            assert not hasattr(row, "opponent_games")


# ---------------------------------------------------------------------------
# Phase 87.2 (SEC2-ΔES-02): schema migration tests (Task 1 RED gate)
# ---------------------------------------------------------------------------


class TestPhase872SchemaFields:
    """Phase 87.2 (SEC2-ΔES-02): 20 new section2_score_gap_* fields on
    ScoreGapMaterialResponse; 5 deletions on MaterialRow (opponent_score,
    opponent_games, diff_p_value, diff_ci_low, diff_ci_high); 5 deletions
    on ScoreGapMaterialResponse (skill, opp_skill, skill_diff_p_value,
    skill_diff_ci_low, skill_diff_ci_high).

    These tests MUST pass after the schema migration in Task 1."""

    def test_score_gap_material_response_has_20_new_fields_with_none_defaults(self) -> None:
        """ScoreGapMaterialResponse(without any 87.2 kwargs) defaults all 20
        new section2_score_gap_* fields to None (backward compat)."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        resp = ScoreGapMaterialResponse(
            endgame_score=0.0,
            non_endgame_score=0.0,
            score_difference=0.0,
            material_rows=[],
            timeline=[],
            timeline_window=0,
        )
        # 3 buckets x 5 fields = 15 fields (Phase 87.4 D-05: "skill" dropped).
        for bucket in ("conv", "parity", "recov"):
            assert getattr(resp, f"section2_score_gap_{bucket}_mean") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_n") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_p_value") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_ci_low") is None
            assert getattr(resp, f"section2_score_gap_{bucket}_ci_high") is None

    def test_score_gap_material_response_new_fields_round_trip(self) -> None:
        """Setting section2_score_gap_conv_mean=0.05 and _conv_n=42 round-trips
        through model_dump() and model_validate()."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        resp = ScoreGapMaterialResponse(
            endgame_score=0.6,
            non_endgame_score=0.5,
            score_difference=0.1,
            material_rows=[],
            timeline=[],
            timeline_window=100,
            section2_score_gap_conv_mean=0.05,
            section2_score_gap_conv_n=42,
            section2_score_gap_conv_p_value=0.03,
            section2_score_gap_conv_ci_low=0.01,
            section2_score_gap_conv_ci_high=0.09,
        )
        dumped = resp.model_dump()
        assert dumped["section2_score_gap_conv_mean"] == pytest.approx(0.05)
        assert dumped["section2_score_gap_conv_n"] == 42
        assert dumped["section2_score_gap_conv_p_value"] == pytest.approx(0.03)
        assert dumped["section2_score_gap_conv_ci_low"] == pytest.approx(0.01)
        assert dumped["section2_score_gap_conv_ci_high"] == pytest.approx(0.09)
        # Round-trip
        resp2 = ScoreGapMaterialResponse.model_validate(dumped)
        assert resp2.section2_score_gap_conv_mean == pytest.approx(0.05)
        assert resp2.section2_score_gap_conv_n == 42

    def test_material_row_does_not_have_opponent_score_field(self) -> None:
        """After Phase 87.2 migration, MaterialRow no longer has opponent_score
        or opponent_games fields. Constructing without them succeeds."""
        from app.schemas.endgames import MaterialRow

        row = MaterialRow(
            bucket="parity",
            label="Parity",
            games=10,
            win_pct=40.0,
            draw_pct=20.0,
            loss_pct=40.0,
            score=0.5,
        )
        # The deleted fields must not exist on the model
        assert not hasattr(row, "opponent_score")
        assert not hasattr(row, "opponent_games")
        assert not hasattr(row, "diff_p_value")
        assert not hasattr(row, "diff_ci_low")
        assert not hasattr(row, "diff_ci_high")

    def test_score_gap_material_response_does_not_have_old_skill_fields(self) -> None:
        """After Phase 87.2 migration, ScoreGapMaterialResponse no longer has
        skill, opp_skill, skill_diff_p_value, skill_diff_ci_low,
        skill_diff_ci_high. They must not appear on the response."""
        from app.schemas.endgames import ScoreGapMaterialResponse

        resp = ScoreGapMaterialResponse(
            endgame_score=0.0,
            non_endgame_score=0.0,
            score_difference=0.0,
            material_rows=[],
            timeline=[],
            timeline_window=0,
        )
        assert not hasattr(resp, "skill")
        assert not hasattr(resp, "opp_skill")
        assert not hasattr(resp, "skill_diff_p_value")
        assert not hasattr(resp, "skill_diff_ci_low")
        assert not hasattr(resp, "skill_diff_ci_high")


class TestPhase872PerBucketDeltaES:
    """Phase 87.2 (D-01/D-06/SEC2-ΔES-07): per-bucket ΔES Score Gap math.

    Tests cover gaps_by_bucket accumulation in _aggregate_endgame_stats (span-grain,
    per-bucket), and the per-bucket paired-z + equal-weighted Skill aggregator wired
    through _compute_score_gap_material.

    Helper fixtures use 8-tuple rows: (game_id, endgame_class_int, result,
    user_color, eval_cp, eval_mate, next_entry_eval_cp, next_entry_eval_mate).
    """

    @staticmethod
    def _gap_row(
        game_id: int,
        endgame_class_int: int,
        result: str,
        user_color: str,
        eval_cp: int | None,
        eval_mate: int | None,
        next_entry_eval_cp: int | None = None,
        next_entry_eval_mate: int | None = None,
    ) -> tuple[Any, ...]:
        """Build an 8-tuple row matching the post-Phase-87.1 repo shape."""
        return (
            game_id,
            endgame_class_int,
            result,
            user_color,
            eval_cp,
            eval_mate,
            next_entry_eval_cp,
            next_entry_eval_mate,
        )

    @staticmethod
    def _make_wdl(wins: int, draws: int, losses: int) -> "EndgameWDLSummary":
        total = wins + draws + losses
        if total > 0:
            win_pct = round(wins / total * 100, 1)
            draw_pct = round(draws / total * 100, 1)
            loss_pct = round(losses / total * 100, 1)
        else:
            win_pct = draw_pct = loss_pct = 0.0
        return EndgameWDLSummary(
            wins=wins,
            draws=draws,
            losses=losses,
            total=total,
            win_pct=win_pct,
            draw_pct=draw_pct,
            loss_pct=loss_pct,
        )

    def test_aggregate_endgame_stats_returns_tuple(self) -> None:
        """Phase 87.2: _aggregate_endgame_stats now returns a 2-tuple
        (categories, gaps_by_bucket) rather than just a list of categories.
        The returned value can be unpacked: categories, gaps_by_bucket = ..."""
        rows: list[tuple[Any, ...]] = []
        categories, gaps_by_bucket = _aggregate_endgame_stats(rows)
        # categories is a list of EndgameCategoryStats; gaps_by_bucket is a dict.
        assert isinstance(categories, list)
        assert isinstance(gaps_by_bucket, dict)

    def test_gaps_by_bucket_partition_three_buckets(self) -> None:
        """3 spans in 3 distinct buckets → one gap value per bucket cohort.

        Conv: eval_cp=+200 (above threshold), Parity: eval_cp=0, Recov: eval_cp=-200.
        All terminal spans (next_entry_eval_* = None) so exit_score = game result.
        """
        rows = [
            # Conv bucket: eval_cp=200 white, wins => gap = exit_score - ES_entry > 0
            self._gap_row(1, 1, "1-0", "white", 200, None),
            # Parity bucket: eval_cp=0 white => ES_entry ≈ 0.5
            self._gap_row(2, 1, "1-0", "white", 0, None),
            # Recov bucket: eval_cp=-200 white => user at disadvantage
            self._gap_row(3, 1, "0-1", "white", -200, None),
        ]
        categories, gaps_by_bucket = _aggregate_endgame_stats(rows)
        # Each bucket gets exactly one span's gap.
        assert len(gaps_by_bucket.get("conversion", [])) == 1
        assert len(gaps_by_bucket.get("parity", [])) == 1
        assert len(gaps_by_bucket.get("recovery", [])) == 1

    def test_gaps_by_bucket_span_grain_not_game_grain(self) -> None:
        """A single game_id with spans in two different buckets contributes one
        span-gap to each bucket (NOT deduplicated to one game). This is per-span
        grain, unlike _aggregate_bucket_counts which dedupes per game."""
        rows = [
            # Same game_id=1, one Conv span and one Recov span (different endgame classes).
            self._gap_row(1, 1, "1-0", "white", 200, None),  # Conv span (rook class)
            self._gap_row(1, 3, "1-0", "white", -200, None),  # Recov span (pawn class)
        ]
        categories, gaps_by_bucket = _aggregate_endgame_stats(rows)
        # Per-span attribution: game_id=1 contributes to BOTH cohorts.
        assert len(gaps_by_bucket.get("conversion", [])) == 1
        assert len(gaps_by_bucket.get("recovery", [])) == 1

    def test_gaps_by_bucket_null_eval_excluded(self) -> None:
        """Spans with both eval_cp=None and eval_mate=None are excluded from
        gaps_by_bucket because _compute_span_gap returns None for NULL-eval spans."""
        rows = [
            # NULL eval — no gap computed.
            self._gap_row(1, 1, "1-0", "white", None, None),
            # Real eval — gap computed and goes into parity bucket.
            self._gap_row(2, 1, "1-0", "white", 0, None),
        ]
        categories, gaps_by_bucket = _aggregate_endgame_stats(rows)
        # Only the real-eval span contributes a gap.
        total_gaps = sum(len(v) for v in gaps_by_bucket.values())
        assert total_gaps == 1

    def test_phase_87_1_outputs_unaffected_by_gaps_by_bucket(self) -> None:
        """Adding gaps_by_bucket does not perturb the per-class
        type_achievable_score_gap_* aggregation from Phase 87.1."""
        rows = [self._gap_row(i + 1, 1, "1-0", "white", 0, None) for i in range(10)]
        categories, gaps_by_bucket = _aggregate_endgame_stats(rows)
        rook = next(c for c in categories if c.endgame_class == "rook")
        # Phase 87.1 per-class gap fields must still be populated correctly.
        assert rook.type_achievable_score_gap_n == 10
        assert rook.type_achievable_score_gap_mean is not None
        assert rook.type_achievable_score_gap_p_value is not None  # n >= 10

    def test_per_bucket_full_cohort_paired_z(self) -> None:
        """15 Conv-bucket spans all with gap=+0.1 (zero variance).

        section2_score_gap_conv_mean = 0.1, n=15, p_value populated (n>=10),
        ci_low == ci_high == 0.1 (zero-variance collapse per helper contract).
        """

        from app.services.score_confidence import CONFIDENCE_MIN_N

        n = 15
        assert n >= CONFIDENCE_MIN_N  # self-check for fixture sanity

        # 15 Conv-bucket terminal spans: eval_cp=200 white, result=win.
        # gap = 1.0 - ES_sigmoid(200) ≈ 1.0 - 0.726 ≈ 0.274 (exact value unimportant here).
        # Use a transitory span shape for exact gap control instead.
        # Transitory: entry eval_cp=0 white, next_entry_eval_cp=0 white.
        # gap = ES_sigmoid(0) - ES_sigmoid(0) = 0, not useful.
        # Use terminal spans with a controlled entry eval so gap is predictable.
        # With eval_cp=0 (ES_entry=0.5) and result=1-0 (exit_score=1.0):
        #   gap = 1.0 - 0.5 = 0.5 for each span (since sigmoid(0) = 0.5 exactly).
        # But these go into parity bucket (eval_cp=0 is below 100 cp threshold).
        # For Conv bucket with consistent gap, use eval_cp=0 on the boundary won't work.
        # Use approach: build gaps_by_bucket directly by injecting 15 conv spans
        # with a controlled next_entry eval so we know the gap exactly.
        # Terminal span: eval_cp=200 (Conv) white win → gap = 1.0 - ES(200cp).
        # All 15 identical → zero variance → ci_low == ci_high == mean.
        # entry_rows for _compute_score_gap_material must be _FakeRow (NamedTuple)
        # because _aggregate_bucket_counts uses .game_id attribute access.
        # gaps_by_bucket is pre-built separately with controlled gap values.
        rows = [_FakeRow(i + 1, 1, "1-0", "white", 200, None) for i in range(n)]
        wdl = self._make_wdl(n, 0, 0)
        empty = self._make_wdl(0, 0, 0)
        gaps_by_bucket = {"conversion": [0.1] * n, "parity": [], "recovery": []}
        result = _compute_score_gap_material(wdl, empty, rows, gaps_by_bucket=gaps_by_bucket)
        assert result.section2_score_gap_conv_mean == pytest.approx(0.1, abs=1e-9)
        assert result.section2_score_gap_conv_n == n
        assert result.section2_score_gap_conv_p_value is not None  # n >= 10
        # Zero-variance collapse: ci_low == ci_high == mean.
        assert result.section2_score_gap_conv_ci_low is not None
        assert result.section2_score_gap_conv_ci_high is not None
        assert result.section2_score_gap_conv_ci_low == pytest.approx(0.1, abs=1e-9)
        assert result.section2_score_gap_conv_ci_high == pytest.approx(0.1, abs=1e-9)

    def test_per_bucket_zero_cohort_returns_none_mean(self) -> None:
        """Bucket with n=0 returns section2_score_gap_*_mean=None (not 0.0).

        The helper compute_paired_difference_test returns (0.0, None, None, None)
        for empty input. The service must gate this to None on the wire to prevent
        polluting the frontend with a misleading 0.0.
        """
        wdl = self._make_wdl(5, 0, 0)
        empty = self._make_wdl(0, 0, 0)
        rows = [_FakeRow(i + 1, 1, "1-0", "white", 200, None) for i in range(5)]
        # Only Conv bucket has data; parity and recovery are empty.
        gaps_by_bucket = {"conversion": [0.1] * 5, "parity": [], "recovery": []}
        result = _compute_score_gap_material(wdl, empty, rows, gaps_by_bucket=gaps_by_bucket)
        assert result.section2_score_gap_parity_mean is None
        assert result.section2_score_gap_parity_n == 0
        assert result.section2_score_gap_recov_mean is None
        assert result.section2_score_gap_recov_n == 0

    # Phase 87.4 (D-05): test_skill_equal_weighted_mean_three_active_buckets,
    # test_skill_denominator_drop_below_floor, test_skill_all_below_floor_returns_none,
    # and test_skill_ci_propagation_variance_of_sum deleted alongside the
    # ScoreGapMaterialResponse.section2_score_gap_skill_* field family.

    def test_sign_convention_positive_means_above_stockfish(self) -> None:
        """Positive section2_score_gap_conv_mean means user outperformed Stockfish baseline.

        Fixture: gaps_by_bucket with one conv gap = +0.1
        (exit_score 0.1 above ES_entry). Mean must be +0.1 (NOT -0.1).
        """
        wdl = self._make_wdl(5, 0, 0)
        empty = self._make_wdl(0, 0, 0)
        rows = [_FakeRow(1, 1, "1-0", "white", 200, None)]
        # Positive gap = user exit_score EXCEEDED Stockfish baseline.
        gaps_by_bucket = {"conversion": [0.1], "parity": [], "recovery": []}
        result = _compute_score_gap_material(wdl, empty, rows, gaps_by_bucket=gaps_by_bucket)
        # n=1 → mean populated, p/CI gated (per compute_paired_difference_test contract).
        assert result.section2_score_gap_conv_mean == pytest.approx(0.1, abs=1e-9)
        assert result.section2_score_gap_conv_mean is not None
        assert result.section2_score_gap_conv_mean > 0  # sign check


# Phase 87.4 (D-05): TestEndgameSkillRateMean class deleted alongside the
# endgame_skill_rate_mean field on ScoreGapMaterialResponse.
