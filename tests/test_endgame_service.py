"""Tests for endgame service: classify_endgame_class, _aggregate_endgame_stats, and service entry points.

Tests cover:
- classify_endgame_class: maps material_signature strings to endgame category names
- _aggregate_endgame_stats: aggregates raw per-(game, class) rows into EndgameCategoryStats list
- get_endgame_stats / get_endgame_games: smoke tests to catch wiring bugs (typos, import errors)
- extract_entry_clocks: ply-parity clock extraction (Phase 54)
- quick task 260519-lu0: WDLStats-aligned score/eval/last_played_at via shared helpers
"""

import datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import (
    EndgameEloTimelinePoint,
    EndgameWDLSummary,
    ScoreGapTimelinePoint,
)
from app.services.endgame_service import (
    _aggregate_endgame_stats,
    aggregate_endgame_stats_by_tc,
    _classify_endgame_bucket,
    _compute_endgame_elo_weekly_series,
    compute_score_gap_timeline,
    compute_span_gap,
    _endgame_elo_logistic,
    extract_entry_clocks,
    classify_endgame_class,
    get_endgame_games,
    get_endgame_stats,
)


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

    Drives the per-class Score p-value gating (score_p_value),
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
        gap = compute_span_gap(
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

        gap = compute_span_gap(
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
        gap = compute_span_gap(
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
        gap = compute_span_gap(
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
        gap = compute_span_gap(
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
        gap = compute_span_gap(
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
        gap = compute_span_gap(
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
        gap = compute_span_gap(
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

        gap = compute_span_gap(
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

    def test_ci_is_99_percent(self):
        """The per-class gap CI is the 99% Wald CI (Phase 239 D-14), not 95%."""
        import math

        from app.services.eval_utils import eval_cp_to_expected_score
        from app.services.score_confidence import VERDICT_CI_Z_99

        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),
            self._gap_row(2, 1, "1/2-1/2", "white", -200, None),
            self._gap_row(3, 1, "0-1", "white", 50, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        mean = rook.type_achievable_score_gap_mean
        lo = rook.type_achievable_score_gap_ci_low
        hi = rook.type_achievable_score_gap_ci_high
        assert mean is not None and lo is not None and hi is not None
        gaps = [
            1.0 - eval_cp_to_expected_score(100, "white"),
            0.5 - eval_cp_to_expected_score(-200, "white"),
            0.0 - eval_cp_to_expected_score(50, "white"),
        ]
        g_mean = sum(gaps) / 3
        se = math.sqrt(sum((g - g_mean) ** 2 for g in gaps) / 2 / 3)
        assert hi - mean == pytest.approx(VERDICT_CI_Z_99 * se, abs=1e-9)
        assert mean - lo == pytest.approx(VERDICT_CI_Z_99 * se, abs=1e-9)

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


class TestStartEndScoreMeans:
    """quick-260519-ni3 (Task 1): per-class start/end predicted score means.

    Asserts the reconciliation invariant: end_mean - start_mean == gap_mean
    (within float tolerance 1e-9) for every class over the identical span cohort.
    Also covers the null-when-n==0 contract and two-class independence.
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

    def test_new_fields_present_on_schema(self) -> None:
        """type_achievable_score_start_mean / _end_mean attributes exist on EndgameCategoryStats."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert hasattr(rook, "type_achievable_score_start_mean")
        assert hasattr(rook, "type_achievable_score_end_mean")

    def test_start_end_null_when_n_zero(self) -> None:
        """All spans have NULL entry eval → start/end means are None (same gate as gap_mean)."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", None, None),
            self._gap_row(2, 1, "0-1", "white", None, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.type_achievable_score_gap_n == 0
        assert rook.type_achievable_score_start_mean is None
        assert rook.type_achievable_score_end_mean is None

    def test_reconciliation_invariant_terminal_spans(self) -> None:
        """end_mean - start_mean == gap_mean for a 3-span hand-computed rook fixture (terminal spans).

        Fixture:
          Span 1: entry cp=100, white wins → es_entry=ES(100,white), exit=1.0
          Span 2: entry cp=-200, white draws → es_entry=ES(-200,white), exit=0.5
          Span 3: entry cp=0, white wins (transitory, next cp=300) → exit=ES(300,white)

        Reconciliation: gap_i = exit_i - start_i, so
          mean(exit) - mean(start) = mean(exit - start) = mean(gap) exactly.
        """
        from app.services.eval_utils import eval_cp_to_expected_score

        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),
            self._gap_row(2, 1, "1/2-1/2", "white", -200, None),
            self._gap_row(3, 1, "1-0", "white", 0, None, next_entry_eval_cp=300),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")

        assert rook.type_achievable_score_gap_n == 3
        assert rook.type_achievable_score_gap_mean is not None
        assert rook.type_achievable_score_start_mean is not None
        assert rook.type_achievable_score_end_mean is not None

        # Hand-compute expected values
        starts = [
            eval_cp_to_expected_score(100, "white"),
            eval_cp_to_expected_score(-200, "white"),
            eval_cp_to_expected_score(0, "white"),
        ]
        ends = [
            1.0,
            0.5,
            eval_cp_to_expected_score(300, "white"),
        ]
        expected_start = sum(starts) / 3
        expected_end = sum(ends) / 3
        expected_gap = sum(e - s for e, s in zip(ends, starts)) / 3

        assert rook.type_achievable_score_start_mean == pytest.approx(expected_start, abs=1e-9)
        assert rook.type_achievable_score_end_mean == pytest.approx(expected_end, abs=1e-9)
        assert rook.type_achievable_score_gap_mean == pytest.approx(expected_gap, abs=1e-9)

        # Core reconciliation invariant: end_mean - start_mean == gap_mean exactly
        assert (
            rook.type_achievable_score_end_mean - rook.type_achievable_score_start_mean
            == pytest.approx(rook.type_achievable_score_gap_mean, abs=1e-9)
        )

    def test_reconciliation_invariant_two_classes(self) -> None:
        """Reconciliation holds independently for two classes (rook + queen)."""
        from app.services.eval_utils import eval_cp_to_expected_score

        rows = [
            # Rook: 2 terminal spans
            self._gap_row(1, 1, "1-0", "white", 50, None),
            self._gap_row(2, 1, "0-1", "white", -100, None),
            # Queen: 1 transitory + 1 terminal
            self._gap_row(3, 4, "1-0", "white", 200, None, next_entry_eval_cp=500),
            self._gap_row(4, 4, "0-1", "black", 0, None),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        queen = next(c for c in result if c.endgame_class == "queen")

        for cat in (rook, queen):
            assert cat.type_achievable_score_start_mean is not None
            assert cat.type_achievable_score_end_mean is not None
            assert cat.type_achievable_score_gap_mean is not None
            # Reconciliation: end_mean - start_mean == gap_mean (tol 1e-9)
            assert (
                cat.type_achievable_score_end_mean - cat.type_achievable_score_start_mean
                == pytest.approx(cat.type_achievable_score_gap_mean, abs=1e-9)
            )

        # Spot-check rook start
        rook_starts = [
            eval_cp_to_expected_score(50, "white"),
            eval_cp_to_expected_score(-100, "white"),
        ]
        assert rook.type_achievable_score_start_mean == pytest.approx(
            sum(rook_starts) / 2, abs=1e-9
        )

    def test_null_eval_spans_excluded_from_start_end(self) -> None:
        """Mixed cohort: NULL-eval spans excluded; start/end computed only over eligible spans."""
        from app.services.eval_utils import eval_cp_to_expected_score

        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),  # eligible
            self._gap_row(2, 1, "0-1", "white", None, None),  # excluded (NULL eval)
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")

        assert rook.type_achievable_score_gap_n == 1
        assert rook.type_achievable_score_start_mean is not None
        assert rook.type_achievable_score_start_mean == pytest.approx(
            eval_cp_to_expected_score(100, "white"), abs=1e-9
        )
        # Terminal win → exit_score = 1.0
        assert rook.type_achievable_score_end_mean == pytest.approx(1.0, abs=1e-9)

    def test_per_bucket_path_unchanged(self) -> None:
        """gaps_by_bucket still receives only gap values (not start/end) — per-bucket path intact."""
        rows = [
            self._gap_row(1, 1, "1-0", "white", 100, None),
            self._gap_row(2, 1, "0-1", "white", -200, None),
        ]
        _, gaps_by_bucket = _aggregate_endgame_stats(rows)
        # Each bucket entry is a float (the gap), not a tuple or dict
        for bucket_gaps in gaps_by_bucket.values():
            for g in bucket_gaps:
                assert isinstance(g, float)


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
            from_date=None,
            to_date=None,
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
            from_date=None,
            to_date=None,
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


# ---------------------------------------------------------------------------
# Phase 54: extract_entry_clocks tests
# ---------------------------------------------------------------------------
# NOTE: _compute_clock_pressure, _compute_clock_pressure_timeline,
# _build_bucket_series, and _compute_time_pressure_chart were deleted in
# Phase 88 (Plan 88-04) when ClockPressureResponse and TimePressureChartResponse
# were replaced by TimePressureCardsResponse. The corresponding test classes
# (TestComputeClockPressure, TestComputeTimePressureChart,
# TestClockPressurePerGameDenominator, TestTimePressureChartPerGameDenominator,
# TestComputeClockPressureTimeline) were removed along with the functions.
# ---------------------------------------------------------------------------


class TestExtractEntryClocks:
    """Unit tests for extract_entry_clocks helper (Phase 54).

    Verifies ply-parity logic: white player's clocks are at even plies (0,2,4,...),
    black player's clocks are at odd plies (1,3,5,...).
    """

    def test_white_user_even_plies(self):
        """White user: first even-ply clock is user clock, first odd-ply clock is opp clock."""
        result = extract_entry_clocks([0, 1, 2, 3], [10.0, 8.0, 9.0, 7.0], "white")
        assert result == (10.0, 8.0)

    def test_black_user_odd_plies(self):
        """Black user: first odd-ply clock is user clock, first even-ply clock is opp clock."""
        result = extract_entry_clocks([0, 1, 2, 3], [10.0, 8.0, 9.0, 7.0], "black")
        assert result == (8.0, 10.0)

    def test_all_none_clocks(self):
        """All None clocks return (None, None)."""
        result = extract_entry_clocks([0, 1, 2, 3], [None, None, None, None], "white")
        assert result == (None, None)

    def test_user_clock_only(self):
        """User clock present, opp clock None -> (value, None)."""
        result = extract_entry_clocks([0, 1], [10.0, None], "white")
        assert result == (10.0, None)

    def test_opp_clock_only(self):
        """Opp clock present, user clock None -> (None, value)."""
        result = extract_entry_clocks([0, 1], [None, 8.0], "white")
        assert result == (None, 8.0)

    def test_skips_none_finds_later(self):
        """Skips None entries; finds first non-None for each parity.

        plies=[0,1,2,3], clocks=[None,8.0,9.0,7.0], user=white:
        - first user ply (even): ply 0 -> None; next even ply 2 -> 9.0
        - first opp ply (odd): ply 1 -> 8.0
        -> (9.0, 8.0)
        """
        result = extract_entry_clocks([0, 1, 2, 3], [None, 8.0, 9.0, 7.0], "white")
        assert result == (9.0, 8.0)

    def test_empty_plies(self):
        """Empty ply array returns (None, None)."""
        result = extract_entry_clocks([], [], "white")
        assert result == (None, None)

    def test_single_ply_user_parity(self):
        """Single ply matching user parity -> (value, None)."""
        result = extract_entry_clocks([0], [5.0], "white")
        assert result == (5.0, None)

    def test_single_ply_opp_parity(self):
        """Single ply matching opp parity -> (None, value)."""
        result = extract_entry_clocks([1], [5.0], "white")
        assert result == (None, 5.0)


# ---------------------------------------------------------------------------
# quick-260417-o2l: compute_score_gap_timeline tests
# ---------------------------------------------------------------------------


def _perf_row(
    played_at: Any,
    result: str,
    user_color: str,
) -> tuple:
    """Build a row matching query_endgame_performance_rows output shape.

    Shape: (played_at, result, user_color, platform, time_control_bucket).
    Phase 87.6 amendment dropped the opponent-rating columns added by the
    earlier 87.6 PR-direct mapping; the logistic-anchored stretch reads only
    per-side scores + Actual ELO.
    """
    return (played_at, result, user_color, "chess.com", "blitz")


class TestComputeScoreGapTimeline:
    """Unit tests for compute_score_gap_timeline (quick-260417-o2l)."""

    def test_empty_inputs_returns_empty(self):
        assert compute_score_gap_timeline([], [], 100) == []

    def test_drops_weeks_with_either_side_below_min_games(self):
        """10 endgame games + 5 non-endgame games -> no points (non_endgame < 10)."""
        monday = datetime.datetime(2026, 1, 5, 12, 0, 0)
        endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(10)
        ]
        non_endgame_rows = [
            _perf_row(monday + datetime.timedelta(hours=i), "1-0", "white") for i in range(5)
        ]
        assert compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100) == []

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
        series = compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100)
        assert len(series) == 2
        assert series[0].date == "2026-01-05"
        assert series[0].score_difference == pytest.approx(1.0)
        assert series[0].endgame_game_count == 10
        assert series[0].non_endgame_game_count == 10
        # UAT fix post-87.5: per_week_endgame_games tracks endgame events in the
        # ISO week (10 endgame rows scheduled into week 1, 10 into week 2).
        assert series[0].per_week_endgame_games == 10
        assert series[0].per_week_total_games == 20
        # Phase 68: absolute per-side means persisted.
        assert series[0].endgame_score == pytest.approx(1.0)
        assert series[0].non_endgame_score == pytest.approx(0.0)
        assert series[1].date == "2026-01-12"
        assert series[1].score_difference == pytest.approx(0.25)
        assert series[1].endgame_game_count == 20
        assert series[1].non_endgame_game_count == 20
        assert series[1].per_week_endgame_games == 10
        assert series[1].per_week_total_games == 20
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
        series = compute_score_gap_timeline(endgame_rows, non_endgame_rows, 10)
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
        series = compute_score_gap_timeline(endgame_rows, non_endgame_rows, 100)
        assert len(series) == 1
        assert series[0].endgame_game_count == 10

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
        series = compute_score_gap_timeline(
            endgame_rows, non_endgame_rows, 100, cutoff_str="2026-01-12"
        )
        assert len(series) == 1
        assert series[0].date == "2026-01-12"
        # Verifies the window pre-fill: +0.25, NOT -0.5.
        assert series[0].score_difference == pytest.approx(0.25)
        assert series[0].endgame_game_count == 20
        assert series[0].non_endgame_game_count == 20


# -----------------------------------------------------------------------------
# Phase 57 ELO-05 / Phase 87.5 — Endgame ELO additive K mapping + timeline helpers
# -----------------------------------------------------------------------------


def _asof_arrays_from_all_rows(all_rows: list[tuple]) -> tuple[list, list[int]]:
    """Mirror the orchestrator's per-combo asof-array build for unit tests.

    Row shape (Phase 57.1): (played_at, platform, time_control_bucket,
    user_color, white_rating, black_rating). The orchestrator derives the
    user's rating per-row via user_color and skips NULL-rating rows.
    """
    dates: list = []
    ratings: list[int] = []
    for r in all_rows:
        if r[0] is None or r[4] is None or r[5] is None:
            continue
        dates.append(r[0])
        ratings.append(r[4] if r[3] == "white" else r[5])
    return dates, ratings


def _sg_pt(
    date: str,
    *,
    endgame_score: float,
    non_endgame_score: float,
    endgame_game_count: int = 10,
    non_endgame_game_count: int = 10,
    per_week_total_games: int = 20,
    per_week_endgame_games: int = 0,
) -> "ScoreGapTimelinePoint":
    """Build a ScoreGapTimelinePoint fixture for the weekly Endgame ELO producer."""
    return ScoreGapTimelinePoint(
        date=date,
        score_difference=round(endgame_score - non_endgame_score, 4),
        endgame_game_count=endgame_game_count,
        non_endgame_game_count=non_endgame_game_count,
        per_week_total_games=per_week_total_games,
        per_week_endgame_games=per_week_endgame_games,
        endgame_score=endgame_score,
        non_endgame_score=non_endgame_score,
    )


class TestEndgameEloTimeline:
    """Unit tests for _compute_endgame_elo_weekly_series (Phase 87.6 amendment
    2026-05-17 — logistic stretch anchored on Actual ELO).

    The weekly producer consumes a per-combo ScoreGapTimelinePoint list
    (already filtered to weeks where both windows hold >= MIN_GAMES_FOR_TIMELINE
    games) and the per-combo asof arrays. Each point's endgame_elo and
    non_endgame_elo are placed symmetrically around the asof-joined Actual ELO:
    endgame_elo + non_endgame_elo == 2 * actual_elo exactly.
    """

    def test_empty_inputs_returns_empty(self):
        assert _compute_endgame_elo_weekly_series([], [], []) == []

    def test_single_point_at_zero_gap_preserves_actual_elo(self):
        # At endgame_score == non_endgame_score the logit ratio is 1, spread = 0,
        # so both ELO sides equal actual_elo.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.5,
                non_endgame_score=0.5,
                endgame_game_count=20,
                non_endgame_game_count=20,
            )
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 1
        assert result[0].endgame_elo == 1500
        assert result[0].non_endgame_elo == 1500
        assert result[0].actual_elo == 1500

    def test_positive_gap_lifts_endgame_elo(self):
        # endgame_score > non_endgame_score => endgame_elo > actual_elo > non_endgame_elo.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.6,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 1
        pt = result[0]
        assert pt.endgame_elo > pt.actual_elo > pt.non_endgame_elo
        # Midpoint exactness.
        assert pt.endgame_elo + pt.non_endgame_elo == 2 * pt.actual_elo

    def test_negative_gap_holds_back_endgame_elo(self):
        # endgame_score < non_endgame_score => endgame_elo < actual_elo < non_endgame_elo.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1800, 1800)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.4,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 1
        pt = result[0]
        assert pt.endgame_elo < pt.actual_elo < pt.non_endgame_elo
        assert pt.endgame_elo + pt.non_endgame_elo == 2 * pt.actual_elo

    def test_multi_point_series_each_point_satisfies_midpoint_identity(self):
        # Five points spanning the realistic gap range. The midpoint property
        # must hold EXACTLY for every emitted point (Phase 87.6 amendment
        # invariant): endgame_elo + non_endgame_elo == 2 * actual_elo.
        all_rows = [
            (datetime.datetime(2026, 1, 9, 12, 0, 0), "chess.com", "blitz", "white", 1500, 1500),
            (datetime.datetime(2026, 1, 16, 12, 0, 0), "chess.com", "blitz", "white", 1520, 1520),
            (datetime.datetime(2026, 1, 23, 12, 0, 0), "chess.com", "blitz", "white", 1540, 1540),
            (datetime.datetime(2026, 1, 30, 12, 0, 0), "chess.com", "blitz", "white", 1560, 1560),
            (datetime.datetime(2026, 2, 6, 12, 0, 0), "chess.com", "blitz", "white", 1580, 1580),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        gaps = [-0.20, -0.10, 0.0, 0.10, 0.20]
        dates = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26", "2026-02-02"]
        sg = [
            _sg_pt(
                dates[i],
                endgame_score=0.5 + g / 2,
                non_endgame_score=0.5 - g / 2,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
            for i, g in enumerate(gaps)
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 5
        for pt in result:
            assert pt.endgame_elo + pt.non_endgame_elo == 2 * pt.actual_elo

    def test_monotone_in_score_gap(self):
        # Increasing endgame_score with non_endgame_score held fixed must
        # monotonically grow endgame_elo.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        prev = None
        for s_e in [0.40, 0.45, 0.50, 0.55, 0.60]:
            sg = [
                _sg_pt(
                    "2026-01-05",
                    endgame_score=s_e,
                    non_endgame_score=0.50,
                    endgame_game_count=100,
                    non_endgame_game_count=100,
                )
            ]
            result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
            assert len(result) == 1
            if prev is not None:
                assert result[0].endgame_elo > prev
            prev = result[0].endgame_elo

    def test_cutoff_filters_pre_cutoff_points(self):
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt("2026-01-05", endgame_score=0.55, non_endgame_score=0.50),
            _sg_pt("2026-01-12", endgame_score=0.50, non_endgame_score=0.50),
        ]
        result = _compute_endgame_elo_weekly_series(
            sg, asof_dates, asof_ratings, cutoff_str="2026-01-10"
        )
        assert len(result) == 1
        assert result[0].date >= "2026-01-10"

    def test_asof_uses_largest_date_le_point_date(self):
        # asof-join must pick the latest rating sample <= next-Monday of the
        # point's ISO week. For a point dated 2026-01-12 (Monday) the bisect
        # cutoff is 2026-01-19 (next Monday, exclusive). The 2026-01-15 sample
        # at rating 1520 must be the picked one; with score gap = 0 the midpoint
        # stretch is 0 so both endgame_elo and non_endgame_elo equal that 1520.
        all_rows = [
            (datetime.datetime(2026, 1, 5, 12, 0, 0), "chess.com", "blitz", "white", 1500, 1500),
            (datetime.datetime(2026, 1, 15, 12, 0, 0), "chess.com", "blitz", "white", 1520, 1500),
            (datetime.datetime(2026, 2, 1, 12, 0, 0), "chess.com", "blitz", "white", 1540, 1500),
        ]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt(
                "2026-01-12",
                endgame_score=0.5,
                non_endgame_score=0.5,
            )
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 1
        assert result[0].actual_elo == 1520
        assert result[0].endgame_elo == 1520
        assert result[0].non_endgame_elo == 1520

    def test_per_week_endgame_games_carries_through(self):
        # The producer carries pt.endgame_game_count → endgame_games_in_window,
        # pt.per_week_endgame_games → per_week_endgame_games, and
        # pt.per_week_total_games → per_week_total_games.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.5,
                non_endgame_score=0.5,
                endgame_game_count=42,
                per_week_endgame_games=7,
                per_week_total_games=23,
            )
        ]
        result = _compute_endgame_elo_weekly_series(sg, asof_dates, asof_ratings)
        assert len(result) == 1
        assert result[0].endgame_games_in_window == 42
        assert result[0].per_week_endgame_games == 7
        assert result[0].per_week_total_games == 23

    def test_per_combo_isolation(self):
        # Each combo's Endgame ELO is derived ONLY from that combo's own
        # score-gap series. Symmetric mirror: combo A's positive gap and
        # combo B's negative gap must produce different endgame_elos.
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg_a = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.6,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        sg_b = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.4,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        out_a = _compute_endgame_elo_weekly_series(sg_a, asof_dates, asof_ratings)
        out_b = _compute_endgame_elo_weekly_series(sg_b, asof_dates, asof_ratings)
        assert len(out_a) == 1 and len(out_b) == 1
        assert out_a[0].endgame_elo > 1500 > out_b[0].endgame_elo
        # Cross-combo independence: combos produce different endgame_elos.
        assert out_a[0].endgame_elo != out_b[0].endgame_elo

    def test_per_side_independence(self):
        # Changing only the endgame score must change endgame_elo AND
        # non_endgame_elo symmetrically (the anchored stretch ties both sides
        # to the same spread, mirroring through actual_elo).
        played_at = datetime.datetime(2026, 1, 9, 12, 0, 0)
        all_rows = [(played_at, "chess.com", "blitz", "white", 1500, 1500)]
        asof_dates, asof_ratings = _asof_arrays_from_all_rows(all_rows)
        sg_a = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.6,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        sg_b = [
            _sg_pt(
                "2026-01-05",
                endgame_score=0.4,
                non_endgame_score=0.5,
                endgame_game_count=100,
                non_endgame_game_count=100,
            )
        ]
        series_a = _compute_endgame_elo_weekly_series(sg_a, asof_dates, asof_ratings)
        series_b = _compute_endgame_elo_weekly_series(sg_b, asof_dates, asof_ratings)
        assert len(series_a) == 1 and len(series_b) == 1
        assert series_a[0].endgame_elo != series_b[0].endgame_elo
        # Midpoint property holds in both fixtures.
        for s in (series_a[0], series_b[0]):
            assert s.endgame_elo + s.non_endgame_elo == 2 * s.actual_elo


# Sanity check: EndgameEloTimelinePoint is actually exported from the schema.
# Phase 87.5 (D-06): per-point field name restored to endgame_elo (Phase 87.4 had renamed it).
# Phase 87.6: non_endgame_elo added.
def test_endgame_elo_timeline_point_constructs():
    pt = EndgameEloTimelinePoint(
        date="2026-01-05",
        endgame_elo=1500,
        non_endgame_elo=1480,
        actual_elo=1480,
        endgame_games_in_window=42,
        per_week_endgame_games=8,
    )
    assert pt.endgame_elo == 1500
    assert pt.non_endgame_elo == 1480
    assert pt.endgame_games_in_window == 42
    assert pt.per_week_endgame_games == 8


class TestEndgameEloLogistic:
    """Unit tests for _endgame_elo_logistic helper (Phase 87.6 amendment
    2026-05-17 — logistic stretch anchored on Actual ELO).

    Formula:
        spread = 400 * log10( (s_E / (1 - s_E)) / (s_N / (1 - s_N)) )
        endgame_elo     = actual_elo + spread / 2
        non_endgame_elo = actual_elo - spread / 2

    At s_E == s_N the spread is 0 so both sides equal actual_elo. The midpoint
    holds exactly for every input because round(a + d) + round(a - d) == 2a
    when a is an integer.
    """

    @pytest.mark.parametrize("actual_elo", [800, 1200, 1500, 2000, 2400])
    def test_zero_gap_returns_actual_elo(self, actual_elo: int) -> None:
        eg, neg = _endgame_elo_logistic(actual_elo, 0.5, 0.5)
        assert eg == actual_elo
        assert neg == actual_elo

    @pytest.mark.parametrize(
        "endgame_score, non_endgame_score, actual_elo",
        [
            (0.30, 0.70, 1200),
            (0.45, 0.55, 1500),
            (0.55, 0.45, 1500),
            (0.70, 0.30, 1800),
            (0.99, 0.01, 2000),
            (0.01, 0.99, 2000),
            (0.50, 0.50, 1500),
        ],
    )
    def test_midpoint_property_exact(
        self, endgame_score: float, non_endgame_score: float, actual_elo: int
    ) -> None:
        eg, neg = _endgame_elo_logistic(actual_elo, endgame_score, non_endgame_score)
        # The midpoint property must hold EXACTLY for every emitted pair.
        assert eg + neg == 2 * actual_elo

    def test_sign_convention_positive_gap_lifts_endgame_elo(self) -> None:
        eg, neg = _endgame_elo_logistic(1500, 0.60, 0.50)
        assert eg > 1500 > neg

    def test_sign_convention_negative_gap_lowers_endgame_elo(self) -> None:
        eg, neg = _endgame_elo_logistic(1500, 0.40, 0.50)
        assert eg < 1500 < neg

    def test_monotone_in_endgame_score(self) -> None:
        # With non_endgame_score fixed, endgame_elo grows monotonically with
        # endgame_score over the realistic range.
        prev = None
        for s_e in [0.30, 0.40, 0.50, 0.60, 0.70]:
            eg, _ = _endgame_elo_logistic(1500, s_e, 0.50)
            if prev is not None:
                assert eg > prev
            prev = eg

    def test_clamps_score_extremes_no_overflow(self) -> None:
        # All-loss/all-win streaks must not blow up the logit. Both sides
        # remain finite ints with the midpoint property intact.
        eg_high, neg_high = _endgame_elo_logistic(1500, 1.0, 0.0)
        eg_low, neg_low = _endgame_elo_logistic(1500, 0.0, 1.0)
        assert isinstance(eg_high, int) and isinstance(neg_high, int)
        assert isinstance(eg_low, int) and isinstance(neg_low, int)
        assert eg_high + neg_high == 3000
        assert eg_low + neg_low == 3000
        # Sign convention preserved at the extremes.
        assert eg_high > neg_high
        assert eg_low < neg_low

    def test_returns_ints(self) -> None:
        eg, neg = _endgame_elo_logistic(1500, 0.55, 0.50)
        assert isinstance(eg, int)
        assert isinstance(neg, int)


def test_K_constant_deleted_from_endgame_service() -> None:
    """Regression: Phase 87.5 K=450 and Phase 87.6 PR helper must both be gone
    after the Phase 87.6 amendment (logistic-anchored stretch) ships.
    """
    from pathlib import Path

    src = Path("app/services/endgame_service.py").read_text()
    # Strip comments before searching so a historical mention in a comment
    # cannot mask a real definition.
    non_comment_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    non_comment = "\n".join(non_comment_lines)
    assert "K: float = 450" not in non_comment, "K=450 must be deleted, not retuned"
    assert "K = 450" not in non_comment, "K=450 must be deleted, not retuned"
    assert "_endgame_elo_from_score_gap" not in non_comment, (
        "Phase 87.5 additive helper must be deleted"
    )
    assert "_performance_rating" not in non_comment, (
        "Phase 87.6 PR helper must be deleted (amendment supersedes it)"
    )


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


# ---------------------------------------------------------------------------
# Phase 87.2 (SEC2-ΔES-02): schema migration tests (Task 1 RED gate)
# ---------------------------------------------------------------------------


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

    def test_gaps_by_bucket_null_eval_excluded(self) -> None:
        """Spans with both eval_cp=None and eval_mate=None are excluded from
        gaps_by_bucket because compute_span_gap returns None for NULL-eval spans."""
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

    # Phase 87.4 (D-05): test_skill_equal_weighted_mean_three_active_buckets,
    # test_skill_denominator_drop_below_floor, test_skill_all_below_floor_returns_none,
    # and test_skill_ci_propagation_variance_of_sum deleted alongside the
    # ScoreGapMaterialResponse.score_gap_skill_* field family.


# Phase 87.4 (D-05): TestEndgameSkillRateMean class deleted alongside the
# endgame_skill_rate_mean field on ScoreGapMaterialResponse.


# ── Quick task 260519-lu0: WDLStats-aligned score/eval/last_played_at fields ──


class TestEndgameCategoryStatsWdlAlignedFields:
    """Quick task 260519-lu0: EndgameCategoryStats now carries WDLStats-aligned
    score/eval/last_played_at fields populated via the same shared helpers as the
    openings stats path (_build_wdl_stats + compute_eval_confidence_bucket).
    """

    # ── Reuse equality tests ──────────────────────────────────────────────────

    def test_score_equals_build_wdl_stats(self) -> None:
        """score/confidence/ci_low/ci_high/p_value equal _build_wdl_stats for same W/D/L."""
        from app.services.openings_service import _build_wdl_stats

        # 30W 5D 5L on rook (class_int=1) in parity bucket (eval ~0).
        rows = [(i + 1, 1, "1-0", "white", 0, None) for i in range(30)]
        rows += [(i + 31, 1, "1/2-1/2", "white", 0, None) for i in range(5)]
        rows += [(i + 36, 1, "0-1", "white", 0, None) for i in range(5)]

        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")

        reference = _build_wdl_stats(30, 5, 5, 40)
        assert rook.score == pytest.approx(reference.score, abs=1e-9)
        assert rook.confidence == reference.confidence
        assert rook.ci_low == pytest.approx(reference.ci_low, abs=1e-9)
        assert rook.ci_high == pytest.approx(reference.ci_high, abs=1e-9)
        assert rook.p_value == pytest.approx(reference.p_value, abs=1e-9)

    def test_score_p_value_gated_below_n10_backward_compat(self) -> None:
        """score_p_value stays None when total < PVALUE_RELIABILITY_MIN_N=10.

        Regression guard: existing consumers read score_p_value (the
        gated field), NOT the new ungated p_value. Both must exist and the gated
        one must be None below the threshold.
        """
        # 5 games — below the n=10 gate.
        rows = [(i + 1, 1, "1-0", "white", 0, None) for i in range(5)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Gated field (existing, backward compat) must be None.
        assert rook.score_p_value is None
        # New ungated p_value field is always populated.
        assert rook.p_value is not None
        assert isinstance(rook.p_value, float)

    # ── Eval cohort tests ─────────────────────────────────────────────────────

    def test_eval_equals_compute_eval_confidence_bucket(self) -> None:
        """avg_eval_pawns/eval_ci_*/eval_n/eval_p_value/eval_confidence equal
        compute_eval_confidence_bucket over the same user-perspective cohort.
        """
        from app.services.eval_confidence import compute_eval_confidence_bucket

        # 20 parity-bucket rows (for WDL), each at +200 cp white-perspective.
        # user_color=white → user_cp = +200 cp each.
        rows = [(i + 1, 1, "1-0", "white", 200, None) for i in range(20)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")

        # Reference: compute_eval_confidence_bucket over 20 identical user_cp=200 values.
        eval_sum = 200.0 * 20
        eval_sumsq = 200.0**2 * 20
        eval_n = 20
        ref_conf, ref_pval, ref_mean_cp, ref_ci_half = compute_eval_confidence_bucket(
            eval_sum, eval_sumsq, eval_n
        )

        assert rook.eval_n == eval_n
        assert rook.avg_eval_pawns == pytest.approx(ref_mean_cp / 100.0, abs=1e-9)
        assert rook.eval_ci_low_pawns == pytest.approx(
            (ref_mean_cp - ref_ci_half) / 100.0, abs=1e-9
        )
        assert rook.eval_ci_high_pawns == pytest.approx(
            (ref_mean_cp + ref_ci_half) / 100.0, abs=1e-9
        )
        assert rook.eval_p_value == pytest.approx(ref_pval, abs=1e-9)
        assert rook.eval_confidence == ref_conf

    def test_eval_sign_flip_for_black_user(self) -> None:
        """Black-user rows: user_cp = -eval_cp. eval_cp=+200 → user_cp=-200 (disadvantage)."""
        rows = [(i + 1, 1, "1-0", "black", 200, None) for i in range(20)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Black perspective: eval_cp=+200 (white advantage) → user_cp=-200.
        assert rook.avg_eval_pawns is not None
        assert rook.avg_eval_pawns < 0  # negative = user is behind

    def test_eval_outlier_trim_excluded(self) -> None:
        """Rows with |eval_cp| >= EVAL_OUTLIER_TRIM_CP=2000 must NOT enter eval cohort."""
        from app.repositories.stats_repository import EVAL_OUTLIER_TRIM_CP

        # 5 normal rows (user_cp=100) + 1 outlier (eval_cp=2000, excluded) + 1 exact boundary (2001, excluded).
        normal_rows = [(i + 1, 1, "1-0", "white", 100, None) for i in range(5)]
        outlier_row = (6, 1, "1-0", "white", EVAL_OUTLIER_TRIM_CP, None)  # |cp|=2000 → excluded
        over_row = (7, 1, "1-0", "white", EVAL_OUTLIER_TRIM_CP + 1, None)  # |cp|=2001 → excluded
        all_rows = normal_rows + [outlier_row, over_row]
        result, _ = _aggregate_endgame_stats(all_rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Outlier rows excluded → eval_n = 5 (only the normal rows).
        assert rook.eval_n == 5

    def test_eval_mate_row_excluded(self) -> None:
        """Rows with eval_mate is not None must be excluded from the eval cohort."""
        # 5 normal rows + 5 mate rows (eval_mate set → excluded).
        normal_rows = [(i + 1, 1, "1-0", "white", 200, None) for i in range(5)]
        mate_rows = [
            (i + 6, 1, "1-0", "white", None, 3) for i in range(5)
        ]  # eval_mate=3 (in 3 moves)
        result, _ = _aggregate_endgame_stats(normal_rows + mate_rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.eval_n == 5  # only the normal rows

    def test_eval_null_cp_excluded(self) -> None:
        """Rows with eval_cp=None (engine not backfilled) must be excluded from eval cohort."""
        normal_rows = [(i + 1, 1, "1-0", "white", 100, None) for i in range(3)]
        null_eval_rows = [(i + 4, 1, "1-0", "white", None, None) for i in range(3)]
        result, _ = _aggregate_endgame_stats(normal_rows + null_eval_rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.eval_n == 3

    def test_eval_fields_null_when_no_eligible_rows(self) -> None:
        """When all rows have eval_mate set, eval_n=0 and all eval fields are None/default."""
        rows = [(i + 1, 1, "1-0", "white", None, 2) for i in range(10)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.eval_n == 0
        assert rook.avg_eval_pawns is None
        assert rook.eval_ci_low_pawns is None
        assert rook.eval_ci_high_pawns is None
        assert rook.eval_p_value is None
        assert rook.eval_confidence == "low"

    # ── eval_baseline_pawns ───────────────────────────────────────────────────

    def test_eval_baseline_pawns_is_white_baseline(self) -> None:
        """eval_baseline_pawns must equal EVAL_BASELINE_PAWNS_WHITE (color-agnostic, D-02)."""
        from app.services.opening_insights_constants import EVAL_BASELINE_PAWNS_WHITE

        rows = [(1, 1, "1-0", "white", 0, None)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.eval_baseline_pawns == EVAL_BASELINE_PAWNS_WHITE

    # ── last_played_at ────────────────────────────────────────────────────────

    def test_last_played_at_max_across_rows(self) -> None:
        """last_played_at is MAX(played_at) across the category's span rows."""
        older = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        newer = datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc)
        # 9-tuple rows (with played_at in position 8).
        rows: list[tuple] = [
            (1, 1, "1-0", "white", 0, None, None, None, older),
            (2, 1, "0-1", "white", 0, None, None, None, newer),
        ]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.last_played_at == newer

    def test_last_played_at_none_when_all_missing(self) -> None:
        """Legacy 6-tuple fixtures have no played_at → last_played_at is None."""
        rows = [(1, 1, "1-0", "white", 0, None), (2, 1, "0-1", "white", 0, None)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.last_played_at is None

    # ── eval_n==1 edge case (no CI) ───────────────────────────────────────────

    def test_eval_ci_none_when_n_is_one(self) -> None:
        """eval_ci_low/high_pawns are None when eval_n < 2 (not enough for a CI)."""
        rows = [(1, 1, "1-0", "white", 150, None)]
        result, _ = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.eval_n == 1
        assert rook.avg_eval_pawns is not None
        assert rook.eval_ci_low_pawns is None
        assert rook.eval_ci_high_pawns is None


# --- Phase 94 (PCTL-02 / PCTL-06): percentile gate tests ----------------------


# Phase 97 D-10: score_gap_conv_percentile, score_gap_parity_percentile, and
# recovery_score_gap_percentile tests removed — those fields were Metrics-section-only
# and are deleted along with EndgameMetricsSection.tsx (superseded by per-TC cards).
# The conv/parity mean and n fields remain (statistical backbone for per-TC cards).


class TestAggregateEndgameStatsByTc:
    """Unit tests for aggregate_endgame_stats_by_tc (Phase 98).

    Prod feeds per-class `entry_rows` (one row per (game, endgame_class) span,
    carrying time_control_bucket). Tests use plain tuples with the column layout:
    game_id[0], endgame_class_int[1], result[2], user_color[3],
    eval_cp[4], eval_mate[5], time_control_bucket[6],
    next_entry_eval_cp[7], next_entry_eval_mate[8]

    rook=1, minor_piece=2, pawn=3, queen=4, mixed=5, pawnless=6.
    Mixed and pawnless are EXCLUDED from the output (only rook/minor/pawn/queen
    tiles render — D-05); see test_mixed_and_pawnless_excluded.
    """

    # Conversion threshold is >=100cp for white (see _classify_endgame_bucket).
    # Recovery threshold is <=-100cp for white.

    @staticmethod
    def _row(
        game_id: int,
        class_int: int,
        result: str,
        user_color: str,
        eval_cp: int | None,
        tc: str,
    ) -> tuple[int, int, str, str, int | None, None, str, None, None]:
        """Helper: build a 9-tuple bucket row with NULL eval_mate and next-eval cols."""
        return (game_id, class_int, result, user_color, eval_cp, None, tc, None, None)

    def test_empty_rows_returns_empty_dict(self) -> None:
        result = aggregate_endgame_stats_by_tc([])
        assert result == {}

    def test_mixed_and_pawnless_excluded(self) -> None:
        """Mixed (5) and pawnless (6) spans are dropped; only the four type tiles remain.

        Regression for the empty-tile bug: when fed per-class spans, the header
        count must equal the sum of the four rendered tiles (no Mixed/pawnless).
        """
        rows = [
            self._row(1, 1, "1-0", "white", 200, "rapid"),  # rook (kept)
            self._row(2, 2, "1-0", "white", 200, "rapid"),  # minor_piece (kept)
            self._row(3, 3, "1-0", "white", 200, "rapid"),  # pawn (kept)
            self._row(4, 4, "1-0", "white", 200, "rapid"),  # queen (kept)
            self._row(5, 5, "1-0", "white", 200, "rapid"),  # mixed (excluded)
            self._row(6, 6, "1-0", "white", 200, "rapid"),  # pawnless (excluded)
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        classes = {c.endgame_class for c in result["rapid"]}
        assert classes == {"rook", "minor_piece", "pawn", "queen"}
        # Header count (sum of categories) excludes the 2 dropped spans.
        assert sum(c.total for c in result["rapid"]) == 4

    def test_dict_keys_are_tc_strings(self) -> None:
        rows = [
            self._row(1, 1, "1-0", "white", 200, "blitz"),
            self._row(2, 1, "1-0", "white", 200, "rapid"),
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        assert set(result.keys()) == {"blitz", "rapid"}

    def test_per_tc_totals_match_row_counts(self) -> None:
        """Each TC's total across classes must equal the number of rows for that TC."""
        rows = [
            self._row(1, 1, "1-0", "white", 200, "blitz"),  # blitz, rook
            self._row(2, 2, "0-1", "white", -200, "blitz"),  # blitz, minor_piece
            self._row(3, 1, "1-0", "white", 200, "rapid"),  # rapid, rook
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        blitz_total = sum(c.total for c in result["blitz"])
        rapid_total = sum(c.total for c in result["rapid"])
        assert blitz_total == 2
        assert rapid_total == 1

    def test_conversion_rate_computed_correctly(self) -> None:
        """Three conversion wins out of four conversion games = 75%."""
        rows = [
            self._row(1, 1, "1-0", "white", 200, "blitz"),  # conversion win
            self._row(2, 1, "1-0", "white", 200, "blitz"),  # conversion win
            self._row(3, 1, "1-0", "white", 200, "blitz"),  # conversion win
            self._row(4, 1, "0-1", "white", 200, "blitz"),  # conversion loss
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        assert "blitz" in result
        cats = result["blitz"]
        rook_cat = next((c for c in cats if c.endgame_class == "rook"), None)
        assert rook_cat is not None
        assert rook_cat.conversion.conversion_games == 4
        assert rook_cat.conversion.conversion_pct == pytest.approx(75.0)

    def test_recovery_rate_computed_correctly(self) -> None:
        """One recovery save (win/draw) out of two recovery games = 50%."""
        rows = [
            self._row(1, 3, "1/2-1/2", "white", -200, "rapid"),  # recovery draw (save)
            self._row(2, 3, "0-1", "white", -200, "rapid"),  # recovery loss
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        assert "rapid" in result
        cats = result["rapid"]
        pawn_cat = next((c for c in cats if c.endgame_class == "pawn"), None)
        assert pawn_cat is not None
        assert pawn_cat.conversion.recovery_games == 2
        assert pawn_cat.conversion.recovery_pct == pytest.approx(50.0)

    def test_wdl_split_correct(self) -> None:
        """WDL counts and percentages are correct for a two-TC, two-class fixture."""
        rows = [
            self._row(1, 1, "1-0", "white", 50, "bullet"),  # rook win (parity)
            self._row(2, 1, "1/2-1/2", "white", 50, "bullet"),  # rook draw (parity)
            self._row(3, 1, "0-1", "white", 50, "bullet"),  # rook loss (parity)
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        cats = result["bullet"]
        rook = next((c for c in cats if c.endgame_class == "rook"), None)
        assert rook is not None
        assert rook.wins == 1
        assert rook.draws == 1
        assert rook.losses == 1
        assert rook.total == 3

    def test_score_p_value_none_below_reliability_floor(self) -> None:
        """score_p_value is None when total < PVALUE_RELIABILITY_MIN_N (=10)."""
        rows = [self._row(i, 1, "1-0", "white", 200, "rapid") for i in range(5)]
        result = aggregate_endgame_stats_by_tc(rows)
        rook = next((c for c in result["rapid"] if c.endgame_class == "rook"), None)
        assert rook is not None
        assert rook.score_p_value is None

    def test_score_p_value_populated_above_reliability_floor(self) -> None:
        """score_p_value is populated when total >= PVALUE_RELIABILITY_MIN_N (=10)."""
        rows = [self._row(i, 1, "1-0", "white", 200, "rapid") for i in range(10)]
        result = aggregate_endgame_stats_by_tc(rows)
        rook = next((c for c in result["rapid"] if c.endgame_class == "rook"), None)
        assert rook is not None
        assert rook.score_p_value is not None

    def test_tc_ordering_matches_time_control_order(self) -> None:
        """Result dict keys appear in bullet/blitz/rapid/classical order."""
        rows = [
            self._row(1, 1, "1-0", "white", 200, "classical"),
            self._row(2, 1, "1-0", "white", 200, "rapid"),
            self._row(3, 1, "1-0", "white", 200, "bullet"),
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        # Dict insertion order must match _TIME_CONTROL_ORDER
        assert list(result.keys()) == ["bullet", "rapid", "classical"]

    def test_two_tc_two_class_fixture(self) -> None:
        """Verify per-(TC, class) isolation: blitz/rook and rapid/pawn stay separate."""
        rows = [
            self._row(1, 1, "1-0", "white", 200, "blitz"),  # blitz rook conv win
            self._row(2, 1, "0-1", "white", 200, "blitz"),  # blitz rook conv loss
            self._row(3, 3, "1-0", "white", -200, "rapid"),  # rapid pawn recov win
        ]
        result = aggregate_endgame_stats_by_tc(rows)
        blitz_rook = next(c for c in result["blitz"] if c.endgame_class == "rook")
        assert blitz_rook.total == 2
        assert blitz_rook.conversion.conversion_games == 2
        rapid_pawn = next(c for c in result["rapid"] if c.endgame_class == "pawn")
        assert rapid_pawn.total == 1
        assert rapid_pawn.conversion.recovery_games == 1
