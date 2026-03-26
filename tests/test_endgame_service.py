"""Tests for endgame service: classify_endgame_class, _aggregate_endgame_stats, and service entry points.

Tests cover:
- classify_endgame_class: maps material_signature strings to endgame category names
- _aggregate_endgame_stats: aggregates raw per-game rows into EndgameCategoryStats list
- get_endgame_stats / get_endgame_games: smoke tests to catch wiring bugs (typos, import errors)
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.endgame_service import (
    _aggregate_endgame_stats,
    classify_endgame_class,
    get_endgame_stats,
    get_endgame_games,
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

    def test_mixed_rook_and_minor(self):
        """KRB vs KR — rook + minor piece = mixed."""
        assert classify_endgame_class("KRB_KR") == "mixed"

    def test_mixed_queen_and_rook(self):
        """KQR vs KQ — queen + rook = mixed."""
        assert classify_endgame_class("KQR_KQ") == "mixed"

    def test_pawnless(self):
        """K vs K — bare kings, pawnless endgame."""
        assert classify_endgame_class("K_K") == "pawnless"

    def test_minor_piece_with_pawns_is_minor(self):
        """KBPP vs KNP — minor piece + pawns = minor_piece (pawns don't create a mixed endgame)."""
        assert classify_endgame_class("KBPP_KNP") == "minor_piece"

    def test_rook_with_pawns_is_rook(self):
        """KRPP vs KRP — rook + pawns = rook (pawns alongside single piece family)."""
        assert classify_endgame_class("KRPP_KRP") == "rook"

    def test_queen_with_pawns_is_queen(self):
        """KQPP vs KQP — queen + pawns = queen."""
        assert classify_endgame_class("KQPP_KQP") == "queen"

    def test_rook_and_minor_is_mixed(self):
        """KRN vs KR — two piece families (rook + minor) = mixed."""
        assert classify_endgame_class("KRN_KR") == "mixed"


class TestAggregateEndgameStats:
    """Unit tests for endgame stats aggregation logic."""

    def test_empty_input_returns_empty(self):
        """Empty row list produces empty output list."""
        result = _aggregate_endgame_stats([])
        assert result == []

    def test_sorted_by_total_descending(self):
        """D-05: Categories sorted by game count descending."""
        # 1 rook game, 3 pawn games
        rows = [
            # 1 rook game (win)
            (1, "1-0", "white", "KR_KR", 100),
            # 3 pawn games (2 wins, 1 loss)
            (2, "1-0", "white", "KPP_KP", 50),
            (3, "1-0", "white", "KP_KP", 0),
            (4, "0-1", "white", "KPP_KP", -100),
        ]
        result = _aggregate_endgame_stats(rows)
        # Pawn category has 3 games, rook has 1 — pawn should come first
        assert len(result) >= 2
        # Verify sorting is descending by total
        totals = [cat.total for cat in result]
        assert totals == sorted(totals, reverse=True)

    def test_win_draw_loss_percentages(self):
        """Percentages computed correctly for 1W/1D/1L split."""
        rows = [
            (1, "1-0", "white", "KR_KR", 0),       # win
            (2, "1/2-1/2", "white", "KR_KR", 0),   # draw
            (3, "0-1", "white", "KR_KR", 0),        # loss
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.wins == 1
        assert rook.draws == 1
        assert rook.losses == 1
        assert rook.total == 3
        assert abs(rook.win_pct - 33.3) < 1

    def test_conversion_pct_per_category(self):
        """D-08: Conversion = win rate when user entered endgame with material advantage."""
        rows = [
            (1, "1-0", "white", "KR_KR", 200),    # up, won → converted
            (2, "0-1", "white", "KR_KR", 150),     # up, lost → failed conversion
            (3, "1-0", "white", "KR_KR", -100),    # down, won → not a conversion game
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 2 games up, 1 win when up → 50% conversion
        assert rook.conversion.conversion_games == 2
        assert rook.conversion.conversion_wins == 1
        assert abs(rook.conversion.conversion_pct - 50.0) < 0.1

    def test_recovery_pct_per_category(self):
        """D-09: Recovery = draw+win rate when user entered endgame with material disadvantage."""
        rows = [
            (1, "1/2-1/2", "white", "KR_KR", -200),   # down, draw → recovered
            (2, "0-1", "white", "KR_KR", -150),         # down, lost → not recovered
            (3, "1-0", "white", "KR_KR", -100),         # down, won → recovered
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 3 games down, 2 saves (draw + win) → 66.7%
        assert rook.conversion.recovery_games == 3
        assert rook.conversion.recovery_saves == 2
        assert abs(rook.conversion.recovery_pct - 66.7) < 0.1

    def test_no_game_phase_breakdown(self):
        """D-11: Single aggregate per endgame type, no opening/middlegame/endgame sub-breakdown."""
        rows = [
            (1, "1-0", "white", "KR_KR", 100),
        ]
        result = _aggregate_endgame_stats(rows)
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
            (1, "1-0", "white", "KR_KR", 0),     # rook win
            (2, "0-1", "white", "KR_KR", 0),      # rook loss
            (3, "1-0", "white", "KQ_KQ", 0),      # queen win
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        queen = next(c for c in result if c.endgame_class == "queen")
        assert rook.total == 2
        assert queen.total == 1
        assert rook.wins == 1
        assert rook.losses == 1
        assert queen.wins == 1

    def test_zero_conversion_games_returns_zero_pct(self):
        """When no games have material advantage, conversion_pct should be 0 (not a divide-by-zero error)."""
        rows = [
            (1, "1-0", "white", "KR_KR", -100),   # down, won → recovery only
            (2, "0-1", "white", "KR_KR", 0),       # equal, lost → neither
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.conversion_pct == 0.0

    def test_zero_recovery_games_returns_zero_pct(self):
        """When no games have material disadvantage, recovery_pct should be 0."""
        rows = [
            (1, "1-0", "white", "KR_KR", 200),    # up, won → conversion only
            (2, "0-1", "white", "KR_KR", 0),       # equal, lost → neither
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.recovery_games == 0
        assert rook.conversion.recovery_pct == 0.0


class TestGetEndgameStatsSmoke:
    """Smoke tests for service entry points — catch wiring bugs like typos and broken imports."""

    @pytest.mark.asyncio
    async def test_get_endgame_stats_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """Calling get_endgame_stats with a user that has no games should return empty categories."""
        result = await get_endgame_stats(
            db_session, user_id=999999, time_control=None, platform=None,
            rated=None, opponent_type="human", recency=None,
        )
        assert result.categories == []

    @pytest.mark.asyncio
    async def test_get_endgame_games_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """Calling get_endgame_games with a user that has no games should return empty."""
        result = await get_endgame_games(
            db_session, user_id=999999, endgame_class="rook",
            time_control=None, platform=None, rated=None,
            opponent_type="human", recency=None, offset=0, limit=20,
        )
        assert result.games == []
        assert result.matched_count == 0
