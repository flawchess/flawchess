"""Tests for endgame service: classify_endgame_class, _aggregate_endgame_stats, and service entry points.

Tests cover:
- classify_endgame_class: maps material_signature strings to endgame category names
- _aggregate_endgame_stats: aggregates raw per-(game, class) rows into EndgameCategoryStats list
- get_endgame_stats / get_endgame_games: smoke tests to catch wiring bugs (typos, import errors)
- get_endgame_performance: WDL comparison + gauge values
- get_endgame_timeline: rolling-window time series
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.endgame_service import (
    _aggregate_endgame_stats,
    _compute_rolling_series,
    classify_endgame_class,
    get_endgame_games,
    get_endgame_performance,
    get_endgame_stats,
    get_endgame_timeline,
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


class TestAggregateEndgameStats:
    """Unit tests for endgame stats aggregation logic.

    Rows use the new shape: (game_id, endgame_class_int, result, user_color, user_material_imbalance, user_material_imbalance_after)
    where endgame_class_int is 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    The 6th element (user_material_imbalance_after) is the imbalance 4 plies after entry — used
    for the persistence check: both entry AND entry+4 must meet the threshold.
    """

    def test_empty_input_returns_empty(self):
        """Empty row list produces empty output list."""
        result = _aggregate_endgame_stats([])
        assert result == []

    def test_sorted_by_total_descending(self):
        """D-05: Categories sorted by game count descending."""
        # 1 rook game (endgame_class_int=1), 3 pawn games (endgame_class_int=3)
        rows = [
            # 1 rook game (win)
            (1, 1, "1-0", "white", 100, 100),
            # 3 pawn games (2 wins, 1 loss)
            (2, 3, "1-0", "white", 50, 50),
            (3, 3, "1-0", "white", 0, 0),
            (4, 3, "0-1", "white", -100, -100),
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
            (1, 1, "1-0", "white", 0, 0),       # rook win (endgame_class_int=1)
            (2, 1, "1/2-1/2", "white", 0, 0),   # rook draw
            (3, 1, "0-1", "white", 0, 0),        # rook loss
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.wins == 1
        assert rook.draws == 1
        assert rook.losses == 1
        assert rook.total == 3
        assert abs(rook.win_pct - 33.3) < 1

    def test_conversion_pct_per_category(self):
        """D-08: Conversion = win rate when user entered endgame with >= 100cp material advantage (persisted)."""
        rows = [
            (1, 1, "1-0", "white", 500, 500),     # rook, up 500cp, persisted, won → converted
            (2, 1, "0-1", "white", 350, 350),      # rook, up 350cp, persisted, lost → failed conversion
            (3, 1, "1/2-1/2", "white", 100, 100),  # rook, up 100cp (threshold), persisted, draw → draw conversion
            (4, 1, "1-0", "white", 200, 50),        # rook, up 200cp at entry but only 50cp after → NOT conversion (didn't persist)
            (5, 1, "1-0", "white", -400, -400),     # rook, down, won → not a conversion game
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 3 games with persisted >= 100cp: 1 win, 1 draw, 1 loss → 33.3% conversion
        assert rook.conversion.conversion_games == 3
        assert rook.conversion.conversion_wins == 1
        assert rook.conversion.conversion_draws == 1
        assert rook.conversion.conversion_losses == 1
        assert abs(rook.conversion.conversion_pct - 33.3) < 0.1

    def test_recovery_pct_per_category(self):
        """D-09: Recovery = draw+win rate when user entered endgame with <= -100cp material deficit (persisted)."""
        rows = [
            (1, 1, "1-0", "white", -400, -400),    # rook, down 400cp, persisted, won → recovery win
            (2, 1, "1/2-1/2", "white", -500, -500), # rook, down 500cp, persisted, draw → recovery draw
            (3, 1, "0-1", "white", -100, -100),      # rook, down 100cp (threshold), persisted, lost → not recovered
            (4, 1, "0-1", "white", -200, -50),       # rook, down 200cp but only -50cp after → NOT recovery (didn't persist)
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # 3 games with persisted <= -100cp, 2 saves (win + draw) → 66.7%
        assert rook.conversion.recovery_games == 3
        assert rook.conversion.recovery_wins == 1
        assert rook.conversion.recovery_draws == 1
        assert rook.conversion.recovery_saves == 2
        assert abs(rook.conversion.recovery_pct - 66.7) < 0.1

    def test_no_game_phase_breakdown(self):
        """D-11: Single aggregate per endgame type, no opening/middlegame/endgame sub-breakdown."""
        rows = [
            (1, 1, "1-0", "white", 100, 100),  # rook, endgame_class_int=1
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
            (1, 1, "1-0", "white", 0, 0),     # rook win (endgame_class_int=1)
            (2, 1, "0-1", "white", 0, 0),      # rook loss
            (3, 4, "1-0", "white", 0, 0),      # queen win (endgame_class_int=4)
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
            (1, 1, "1-0", "white", -100, -100),   # rook, down, won → recovery only
            (2, 1, "0-1", "white", 0, 0),          # rook, equal, lost → neither
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.conversion_pct == 0.0

    def test_zero_recovery_games_returns_zero_pct(self):
        """When no games have material disadvantage, recovery_pct should be 0."""
        rows = [
            (1, 1, "1-0", "white", 200, 200),    # rook, up, won → conversion only
            (2, 1, "0-1", "white", 0, 0),         # rook, equal, lost → neither
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.recovery_games == 0
        assert rook.conversion.recovery_pct == 0.0

    def test_multi_class_per_game_in_aggregation(self):
        """A game_id appearing with two different endgame_class_int values contributes to both classes."""
        rows = [
            # Same game (game_id=1) in two classes: rook (1) and pawn (3)
            (1, 1, "1-0", "white", 100, 100),   # rook class for game 1
            (1, 3, "1-0", "white", 50, 50),      # pawn class for game 1
            # Another game in rook only
            (2, 1, "0-1", "white", 0, 0),
        ]
        result = _aggregate_endgame_stats(rows)
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

    def test_persistence_filter_excludes_transient_imbalance(self):
        """Imbalance must persist 4 plies after entry — transient trade imbalances are excluded."""
        rows = [
            # Entry imbalance 200cp but after 4 plies only 50cp -> NOT conversion (transient)
            (1, 1, "1-0", "white", 200, 50),
            # Entry imbalance -300cp but after 4 plies only -80cp -> NOT recovery (transient)
            (2, 1, "0-1", "white", -300, -80),
            # Entry 150cp, persisted at 120cp -> IS conversion (both >= 100)
            (3, 1, "1-0", "white", 150, 120),
            # Entry -200cp, persisted at -150cp -> IS recovery (both <= -100)
            (4, 1, "1/2-1/2", "white", -200, -150),
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        # Only game 3 qualifies for conversion
        assert rook.conversion.conversion_games == 1
        assert rook.conversion.conversion_wins == 1
        # Only game 4 qualifies for recovery
        assert rook.conversion.recovery_games == 1
        assert rook.conversion.recovery_draws == 1

    def test_persistence_none_after_value_excluded(self):
        """If imbalance_after is None (shouldn't happen with ply threshold, but safety), exclude from conv/recov."""
        rows = [
            (1, 1, "1-0", "white", 200, None),
            (2, 1, "0-1", "white", -200, None),
        ]
        result = _aggregate_endgame_stats(rows)
        rook = next(c for c in result if c.endgame_class == "rook")
        assert rook.conversion.conversion_games == 0
        assert rook.conversion.recovery_games == 0


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


# --- Helpers ---

def _dt(days_offset: int) -> datetime.datetime:
    """Return a UTC datetime N days from epoch for use in test rows."""
    return datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=days_offset)


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
        expected = (datetime.datetime(2024, 1, 1) + datetime.timedelta(days=n - 1)).strftime("%Y-%m-%d")
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
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = ([], [])
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert result.endgame_wdl.total == 0
        assert result.non_endgame_wdl.total == 0
        assert result.overall_win_rate == 0.0
        assert result.endgame_win_rate == 0.0
        assert result.relative_strength == 0.0
        assert result.aggregate_conversion_pct == 0.0
        assert result.aggregate_recovery_pct == 0.0
        assert result.endgame_skill == 0.0

    @pytest.mark.asyncio
    async def test_wdl_counts_and_percentages(self):
        """3 endgame wins, 1 draw, 1 loss + 2 non-endgame wins, 3 draws, 5 losses."""
        endgame_rows = self._make_wdl_rows(wins=3, draws=1, losses=1)
        non_endgame_rows = self._make_wdl_rows(wins=2, draws=3, losses=5)

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = (endgame_rows, non_endgame_rows)
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
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

    @pytest.mark.asyncio
    async def test_overall_win_rate_across_all_games(self):
        """overall_win_rate = total wins / total games (endgame + non-endgame)."""
        # 3 endgame wins out of 5 + 0 non-endgame wins out of 5 = 3/10 = 30%
        endgame_rows = self._make_wdl_rows(wins=3, draws=1, losses=1)
        non_endgame_rows = self._make_wdl_rows(wins=0, draws=2, losses=3)

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = (endgame_rows, non_endgame_rows)
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert abs(result.overall_win_rate - 30.0) < 0.2

    @pytest.mark.asyncio
    async def test_relative_strength_above_100_possible(self):
        """relative_strength can exceed 100 when endgame_win_rate > overall_win_rate."""
        # endgame: 4W/0D/0L = 100% win rate; non-endgame: 0W/0D/4L = 0% win rate
        # overall = 4/8 = 50%, endgame = 4/4 = 100% → relative_strength = 200
        endgame_rows = self._make_wdl_rows(wins=4, draws=0, losses=0)
        non_endgame_rows = self._make_wdl_rows(wins=0, draws=0, losses=4)

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = (endgame_rows, non_endgame_rows)
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert abs(result.relative_strength - 200.0) < 0.2

    @pytest.mark.asyncio
    async def test_relative_strength_zero_when_overall_win_rate_zero(self):
        """relative_strength should be 0.0 when overall_win_rate is 0 (guard div by zero)."""
        endgame_rows = self._make_wdl_rows(wins=0, draws=0, losses=2)
        non_endgame_rows = self._make_wdl_rows(wins=0, draws=0, losses=2)

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = (endgame_rows, non_endgame_rows)
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert result.relative_strength == 0.0


class TestEndgameGaugeCalculations:
    """Unit tests for gauge value formulas: aggregate conversion/recovery and endgame_skill."""

    def _entry_row(self, game_id: int, endgame_class_int: int, result: str, user_color: str, imbalance: int):
        """Build a (game_id, endgame_class_int, result, user_color, user_material_imbalance, user_material_imbalance_after) entry row.

        Sets imbalance_after equal to imbalance so the persistence check always passes in these gauge tests.
        """
        return (game_id, endgame_class_int, result, user_color, imbalance, imbalance)

    @pytest.mark.asyncio
    async def test_aggregate_conversion_uses_sum_of_raw_not_mean_of_percentages(self):
        """Aggregate conversion_pct = sum(conv_wins) / sum(conv_games) * 100 (not mean of pcts)."""
        # Category A (rook=1): 2 games up material, 1 win → 50%
        # Category B (minor=2): 4 games up material, 3 wins → 75%
        # Mean of percentages: (50 + 75) / 2 = 62.5%
        # Sum of raw: 4 wins / 6 games = 66.67%
        entry_rows = [
            # Category A: rook (1), positive imbalance — 1 win, 1 loss
            self._entry_row(1, 1, "1-0", "white", 500),
            self._entry_row(2, 1, "0-1", "white", 500),
            # Category B: minor_piece (2), positive imbalance — 3 wins, 1 loss
            self._entry_row(3, 2, "1-0", "white", 500),
            self._entry_row(4, 2, "1-0", "white", 500),
            self._entry_row(5, 2, "1-0", "white", 500),
            self._entry_row(6, 2, "0-1", "white", 500),
        ]

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = ([], [])
            mock_entry.return_value = entry_rows

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        # Should be 4/6 * 100 = 66.67, not (50+75)/2 = 62.5
        assert abs(result.aggregate_conversion_pct - 66.7) < 0.2

    @pytest.mark.asyncio
    async def test_endgame_skill_formula(self):
        """endgame_skill = 0.7 * conversion_pct + 0.3 * recovery_pct."""
        # conversion: 8 wins / 10 games up material = 80%
        # recovery: 6 saves / 10 games down material = 60% → skill = 0.7*80 + 0.3*60 = 74
        entry_rows = (
            # 10 games with positive imbalance (rook=1): 8 wins, 2 losses
            [self._entry_row(i, 1, "1-0", "white", 500) for i in range(1, 9)]
            + [self._entry_row(i, 1, "0-1", "white", 500) for i in range(9, 11)]
            # 10 games with negative imbalance (rook=1): 4 wins, 2 draws, 4 losses (6 saves)
            + [self._entry_row(i, 1, "1-0", "white", -500) for i in range(11, 15)]
            + [self._entry_row(i, 1, "1/2-1/2", "white", -500) for i in range(15, 17)]
            + [self._entry_row(i, 1, "0-1", "white", -500) for i in range(17, 21)]
        )

        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = ([], [])
            mock_entry.return_value = entry_rows

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert abs(result.endgame_skill - 74.0) < 0.2

    @pytest.mark.asyncio
    async def test_endgame_skill_zero_with_no_conversion_recovery_data(self):
        """endgame_skill should be 0.0 when no conversion/recovery games exist."""
        with (
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf,
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
        ):
            mock_perf.return_value = ([], [])
            mock_entry.return_value = []

            result = await get_endgame_performance(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human",
            )

        assert result.endgame_skill == 0.0


class TestGetEndgameTimeline:
    """Tests for get_endgame_timeline service function."""

    @pytest.mark.asyncio
    async def test_empty_rows_returns_empty_series(self):
        """With no games, overall and per_type should be empty."""
        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=50,
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

        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = (endgame_rows, non_endgame_rows, {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=n,
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

        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = (endgame_rows, [], {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=50,
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

        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = (endgame_rows, non_endgame_rows, {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=50,
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
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE
        n = MIN_GAMES_FOR_TIMELINE
        rook_rows = [_row("1-0", "white", i) for i in range(n)]

        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: rook_rows, 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=50,
            )

        assert "rook" in result.per_type
        assert "minor_piece" in result.per_type
        assert "pawn" in result.per_type
        assert "queen" in result.per_type
        assert "mixed" in result.per_type
        assert "pawnless" in result.per_type
        # Rook series should have one point (game n passes threshold)
        assert len(result.per_type["rook"]) == 1
        assert result.per_type["rook"][0].win_rate == 1.0

    @pytest.mark.asyncio
    async def test_window_parameter_reflected_in_response(self):
        """window field in response matches the requested window parameter."""
        with patch("app.services.endgame_service.query_endgame_timeline_rows", new_callable=AsyncMock) as mock_timeline:
            mock_timeline.return_value = ([], [], {1: [], 2: [], 3: [], 4: [], 5: [], 6: []})

            result = await get_endgame_timeline(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                recency=None, rated=None, opponent_type="human", window=25,
            )

        assert result.window == 25


class TestGetEndgamePerformanceSmoke:
    """Smoke tests for performance/timeline service entry points with real DB."""

    @pytest.mark.asyncio
    async def test_get_endgame_performance_returns_zeros_for_nonexistent_user(self, db_session: AsyncSession):
        """Calling get_endgame_performance with no data should return all-zero response."""
        result = await get_endgame_performance(
            db_session, user_id=999999, time_control=None, platform=None,
            recency=None, rated=None, opponent_type="human",
        )
        assert result.endgame_wdl.total == 0
        assert result.non_endgame_wdl.total == 0
        assert result.overall_win_rate == 0.0
        assert result.relative_strength == 0.0

    @pytest.mark.asyncio
    async def test_get_endgame_timeline_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """Calling get_endgame_timeline with no data should return empty series."""
        result = await get_endgame_timeline(
            db_session, user_id=999999, time_control=None, platform=None,
            recency=None, rated=None, opponent_type="human",
        )
        assert result.overall == []
        assert result.window == 50
