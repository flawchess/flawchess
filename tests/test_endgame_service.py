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
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.endgames import EndgameWDLSummary
from app.services.endgame_service import (
    _aggregate_endgame_stats,
    _build_bucket_series,
    _compute_clock_pressure,
    _compute_rolling_series,
    _compute_score_gap_material,
    _compute_time_pressure_chart,
    _extract_entry_clocks,
    _wdl_to_score,
    classify_endgame_class,
    get_endgame_games,
    get_endgame_overview,
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
        assert result.endgame_win_rate == 0.0

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

    @pytest.mark.asyncio
    async def test_get_endgame_timeline_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """Calling get_endgame_timeline with no data should return empty series."""
        result = await get_endgame_timeline(
            db_session, user_id=999999, time_control=None, platform=None,
            recency=None, rated=None, opponent_type="human",
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
        from app.schemas.endgames import EndgameTimelineResponse

        with (
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
            patch("app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock) as mock_bucket,
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf_rows,
            patch("app.services.endgame_service.count_filtered_games", new_callable=AsyncMock) as mock_count,
            patch("app.services.endgame_service.count_endgame_games", new_callable=AsyncMock) as mock_eg_count,
            patch("app.services.endgame_service.get_endgame_timeline", new_callable=AsyncMock) as mock_timeline,
            patch("app.services.endgame_service.query_clock_stats_rows", new_callable=AsyncMock) as mock_clock,
        ):
            mock_entry.return_value = []
            mock_bucket.return_value = []
            mock_perf_rows.return_value = ([], [])
            mock_count.return_value = 0
            mock_eg_count.return_value = 0
            mock_timeline.return_value = EndgameTimelineResponse(overall=[], per_type={}, window=50)
            mock_clock.return_value = []

            result = await get_endgame_overview(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                rated=None, opponent_type="human", recency=None, window=50,
            )

        # Repository functions called once each
        mock_entry.assert_called_once()
        mock_bucket.assert_called_once()
        mock_perf_rows.assert_called_once()
        mock_count.assert_called_once()
        mock_eg_count.assert_called_once()
        mock_timeline.assert_called_once()
        mock_clock.assert_called_once()

        # All sub-payloads must be present
        assert result.stats is not None
        assert result.performance is not None
        assert result.timeline is not None
        assert result.score_gap_material is not None
        assert result.clock_pressure is not None
        assert result.clock_pressure.rows == []

    @pytest.mark.asyncio
    async def test_overview_passes_window_to_timeline(self):
        """The window parameter must be forwarded to get_endgame_timeline."""
        from app.schemas.endgames import EndgameTimelineResponse

        with (
            patch("app.services.endgame_service.query_endgame_entry_rows", new_callable=AsyncMock) as mock_entry,
            patch("app.services.endgame_service.query_endgame_bucket_rows", new_callable=AsyncMock) as mock_bucket,
            patch("app.services.endgame_service.query_endgame_performance_rows", new_callable=AsyncMock) as mock_perf_rows,
            patch("app.services.endgame_service.count_filtered_games", new_callable=AsyncMock) as mock_count,
            patch("app.services.endgame_service.count_endgame_games", new_callable=AsyncMock),
            patch("app.services.endgame_service.get_endgame_timeline", new_callable=AsyncMock) as mock_timeline,
            patch("app.services.endgame_service.query_clock_stats_rows", new_callable=AsyncMock) as mock_clock,
        ):
            mock_entry.return_value = []
            mock_bucket.return_value = []
            mock_perf_rows.return_value = ([], [])
            mock_count.return_value = 0
            mock_timeline.return_value = EndgameTimelineResponse(overall=[], per_type={}, window=75)
            mock_clock.return_value = []

            await get_endgame_overview(
                AsyncMock(), user_id=1, time_control=None, platform=None,
                rated=None, opponent_type="human", recency=None, window=75,
            )

        # Timeline function must receive window=75
        _, timeline_kwargs = mock_timeline.call_args
        assert timeline_kwargs.get("window") == 75 or mock_timeline.call_args[0][4] == 75  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_overview_returns_empty_for_nonexistent_user(self, db_session: AsyncSession):
        """get_endgame_overview with a user that has no games returns all empty/zero payloads."""
        result = await get_endgame_overview(
            db_session, user_id=999999, time_control=None, platform=None,
            rated=None, opponent_type="human", recency=None, window=50,
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
            wins=wins, draws=draws, losses=losses, total=total,
            win_pct=win_pct, draw_pct=draw_pct, loss_pct=loss_pct,
        )

    def _make_wdl_pct(self, win_pct: float, draw_pct: float, loss_pct: float, total: int = 100) -> EndgameWDLSummary:
        wins = round(win_pct * total / 100)
        draws = round(draw_pct * total / 100)
        losses = total - wins - draws
        return EndgameWDLSummary(
            wins=wins, draws=draws, losses=losses, total=total,
            win_pct=win_pct, draw_pct=draw_pct, loss_pct=loss_pct,
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
        """Entry row with imbalance=150 preserved goes into 'conversion' bucket."""
        # entry_rows: (game_id, endgame_class_int, result, user_color, user_material_imbalance, user_material_imbalance_after)
        entry_rows = [(1, 1, "1-0", "white", 150, 150)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        conversion = result.material_rows[0]
        assert conversion.bucket == "conversion"
        assert conversion.games == 1
        assert conversion.win_pct == 100.0

    def test_score_gap_material_even_bucket(self):
        """Entry row with imbalance=50 goes into 'even' bucket."""
        entry_rows = [(1, 1, "1-0", "white", 50, 50)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        even = result.material_rows[1]
        assert even.bucket == "even"
        assert even.games == 1

    def test_score_gap_material_recovery_bucket(self):
        """Entry row with imbalance=-200 preserved goes into 'recovery' bucket."""
        entry_rows = [(1, 1, "0-1", "white", -200, -200)]
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
            (1, 1, "1-0", "white", 150, 150),  # game_id=1, class rook
            (1, 3, "1-0", "white", 150, 150),  # game_id=1, class pawn — duplicate
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        conversion = result.material_rows[0]
        assert conversion.bucket == "conversion"
        assert conversion.games == 1  # not 2

    def test_score_gap_material_none_imbalance_bucketed_as_even(self):
        """Entry row with user_material_imbalance=None goes into the 'even' bucket (Phase 59)."""
        entry_rows = [(1, 1, "1-0", "white", None, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].games == 0       # conversion
        assert result.material_rows[1].bucket == "even"
        assert result.material_rows[1].games == 1       # even — NULL rows now land here
        assert result.material_rows[2].games == 0       # recovery

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

    def test_score_gap_material_overall_score_weighted(self):
        """overall_score is weighted from both WDL summaries combined."""
        # endgame: 45W 10D 45L (total=100), non_endgame: 55W 10D 35L (total=100)
        # combined: 100W 20D 80L (total=200) -> (100 + 10) / 200 = 0.55
        endgame_wdl = self._make_wdl(45, 10, 45)
        non_endgame_wdl = self._make_wdl(55, 10, 35)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        assert result.overall_score == pytest.approx(0.55, abs=1e-9)

    def test_score_gap_material_persistence_required_for_conversion(self):
        """Material bucket applies 4-ply persistence rule matching conversion/recovery.

        A row with imbalance=150 (advantage threshold) but imbalance_after=-50
        falls into the 'even' bucket because the advantage did not persist.
        This filters transient imbalances from trades at the endgame boundary.
        """
        entry_rows = [(1, 1, "1-0", "white", 150, -50)]  # imbalance_after negative
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].games == 0  # conversion: not counted
        assert result.material_rows[1].games == 1  # even: counted here
        assert result.material_rows[1].bucket == "even"

    def test_score_gap_material_persistence_required_for_recovery(self):
        """Transient deficit that does not persist falls into 'even' bucket."""
        entry_rows = [(1, 1, "0-1", "white", -150, 50)]  # imbalance_after positive
        endgame_wdl = self._make_wdl(0, 0, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[2].games == 0  # recovery: not counted
        assert result.material_rows[1].games == 1  # even: counted here
        assert result.material_rows[1].bucket == "even"

    def test_score_gap_material_persistence_none_after_falls_to_even(self):
        """imbalance_after=None means persistence cannot be verified -> 'even' bucket."""
        entry_rows = [(1, 1, "1-0", "white", 150, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].games == 0  # conversion: not counted
        assert result.material_rows[1].games == 1  # even: counted here

    def test_score_gap_material_all_three_rows_always_present(self):
        """All three material_rows (conversion, even, recovery) present even when games=0."""
        endgame_wdl = self._make_wdl(0, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, [])
        buckets = [r.bucket for r in result.material_rows]
        assert buckets == ["conversion", "even", "recovery"]

    def test_score_gap_material_boundary_conversion(self):
        """Imbalance exactly == 100 (preserved) -> 'conversion' bucket (>= 100)."""
        entry_rows = [(1, 1, "1-0", "white", 100, 100)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[0].bucket == "conversion"
        assert result.material_rows[0].games == 1

    def test_score_gap_material_boundary_recovery(self):
        """Imbalance exactly == -100 (preserved) -> 'recovery' bucket (<= -100)."""
        entry_rows = [(1, 1, "0-1", "white", -100, -100)]
        endgame_wdl = self._make_wdl(0, 0, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert result.material_rows[2].bucket == "recovery"
        assert result.material_rows[2].games == 1


class TestScoreGapMaterialInvariant(TestScoreGapMaterial):
    """Phase 59 (Decision 4): assert sum(material_rows[i].games) == endgame_wdl.total.

    Inherits _make_wdl and _make_wdl_pct helpers from TestScoreGapMaterial.
    """

    def test_invariant_single_span_each_bucket(self):
        entry_rows = [
            (1, 1, "1-0",    "white", 150, 150),   # conversion
            (2, 1, "0-1",    "white", -150, -150), # recovery
            (3, 1, "1/2-1/2","white", 50, 50),     # even
        ]
        endgame_wdl = self._make_wdl(1, 1, 1)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        total = sum(row.games for row in result.material_rows)
        assert total == endgame_wdl.total == 3
        assert result.material_rows[0].games == 1  # conversion
        assert result.material_rows[1].games == 1  # even
        assert result.material_rows[2].games == 1  # recovery

    def test_invariant_multi_span_conversion_over_recovery(self):
        """Decision 2 tiebreak: when a game has both conversion and recovery spans, pick conversion."""
        entry_rows = [
            (1, 1, "1-0", "white", 150, 150),   # conversion span (rook)
            (1, 3, "1-0", "white", -150, -150), # recovery span (pawn) — same game
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
            (1, 1, "1-0", "white", None, None),  # NULL first (would have been dropped pre-Phase 59)
            (1, 3, "1-0", "white", 150, 150),    # qualifying conversion span
        ]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[0].bucket == "conversion"
        assert result.material_rows[0].games == 1

    def test_invariant_null_imbalance_lands_in_even(self):
        """Decision 1: NULL imbalance -> 'even' bucket (not dropped)."""
        entry_rows = [(1, 1, "1/2-1/2", "white", None, None)]
        endgame_wdl = self._make_wdl(0, 1, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[1].games == 1  # even
        assert result.material_rows[1].draw_pct == 100.0

    def test_invariant_null_after_lands_in_even(self):
        """Decision 1: NULL user_material_imbalance_after (non-contiguous span) -> 'even'."""
        entry_rows = [(1, 1, "1-0", "white", 150, None)]
        endgame_wdl = self._make_wdl(1, 0, 0)
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 1
        assert result.material_rows[1].games == 1  # even

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
            (1, 1, "1-0", "white", 150, 150),
            (2, 1, "1-0", "white", 200, 200),
            (3, 1, "0-1", "white", 150, 150),
            # 2 pure recovery
            (4, 1, "1/2-1/2", "white", -150, -150),
            (5, 1, "0-1", "white", -200, -200),
            # 2 pure even (below threshold)
            (6, 1, "1-0", "white", 50, 50),
            (7, 1, "0-1", "white", -50, -50),
            # 1 multi-span conversion-over-recovery
            (8, 1, "1-0", "white", 150, 150),
            (8, 3, "1-0", "white", -150, -150),
            # 1 NULL-first but conversion-qualifying second
            (9, 1, "1-0", "white", None, None),
            (9, 3, "1-0", "white", 150, 150),
            # 1 all-NULL (lands in even)
            (10, 1, "1/2-1/2", "white", None, None),
        ]
        endgame_wdl = self._make_wdl(6, 2, 2)  # total=10
        non_endgame_wdl = self._make_wdl(0, 0, 0)
        result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
        assert sum(row.games for row in result.material_rows) == endgame_wdl.total == 10

    def test_invariant_deterministic_ordering(self):
        """Decision 2: within the 'even' fallback, lowest endgame_class_int wins for reproducibility."""
        rows_order_a = [
            (1, 1, "1-0", "white", 50, 50),
            (1, 3, "0-1", "white", 40, 40),
        ]
        rows_order_b = [
            (1, 3, "0-1", "white", 40, 40),
            (1, 1, "1-0", "white", 50, 50),
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


# ---------------------------------------------------------------------------
# Phase 54: _extract_entry_clocks and _compute_clock_pressure tests
# ---------------------------------------------------------------------------


def _make_clock_row(
    game_id: int,
    time_control_bucket: str | None,
    time_control_seconds: int | None,
    termination: str | None,
    result: str,
    user_color: str,
    ply_array: list[int],
    clock_array: list[float | None],
) -> tuple:
    """Build a tuple matching the query_clock_stats_rows output shape.

    Shape: (game_id, time_control_bucket, time_control_seconds, termination,
            result, user_color, ply_array, clock_array)
    """
    return (game_id, time_control_bucket, time_control_seconds, termination,
            result, user_color, ply_array, clock_array)


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
        time_control_seconds: int | None = 180,
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
            rows.append(_make_clock_row(
                game_id=game_id,
                time_control_bucket="blitz",
                time_control_seconds=time_control_seconds,
                termination=termination,
                result=result,
                user_color=user_color,
                ply_array=[0, 1],
                clock_array=[user_clock, opp_clock],
            ))
        return rows

    def test_basic_single_bucket(self):
        """12 blitz games with clock data produce one ClockStatsRow for blitz with correct averages."""
        rows = self._make_blitz_rows(12, user_clock=50.0, opp_clock=60.0, time_control_seconds=180)
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
            rows.append(_make_clock_row(
                game_id=i + 1,
                time_control_bucket="bullet",
                time_control_seconds=60,
                termination="checkmate",
                result="1-0",
                user_color="white",
                ply_array=[0, 1],
                clock_array=[5.0, 4.0],
            ))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 0

    def test_net_timeout_rate_deduplication(self):
        """Same game_id in two spans (different endgame_class), both timeout wins -> counted once."""
        # game_id=1 appears twice (two endgame spans), timeout win
        rows = [
            _make_clock_row(1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [5.0, 3.0]),
            _make_clock_row(1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [5.0, 3.0]),
        ]
        # Add 9 more games (total 10 unique) so the row passes the threshold
        for i in range(2, 11):
            rows.append(_make_clock_row(i, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [5.0, 3.0]))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # 10 unique games, 1 timeout win, 0 timeout losses -> rate = 1/10 * 100 = 10.0
        assert row.total_endgame_games == 10
        assert row.net_timeout_rate == pytest.approx(10.0)

    def test_net_timeout_rate_computation(self):
        """20 games, 3 timeout wins, 1 timeout loss -> rate = (3-1)/20*100 = 10.0."""
        rows = []
        for i in range(3):
            rows.append(_make_clock_row(i + 1, "blitz", 180, "timeout", "1-0", "white", [0, 1], [3.0, 10.0]))
        rows.append(_make_clock_row(4, "blitz", 180, "timeout", "0-1", "white", [0, 1], [3.0, 10.0]))
        for i in range(16):
            rows.append(_make_clock_row(i + 5, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [50.0, 60.0]))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        assert result.rows[0].net_timeout_rate == pytest.approx(10.0)

    def test_time_control_seconds_none_pct_is_none(self):
        """Games with time_control_seconds=None -> pct fields are None, seconds fields computed."""
        rows = self._make_blitz_rows(10, user_clock=50.0, opp_clock=60.0, time_control_seconds=None)
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.user_avg_pct is None
        assert row.opp_avg_pct is None
        # Seconds should still be computed
        assert row.user_avg_seconds == pytest.approx(50.0)
        assert row.opp_avg_seconds == pytest.approx(60.0)

    def test_both_clocks_none_excluded_from_clock_games(self):
        """Spans where both user and opp clocks are None -> clock_games=0, averages=None."""
        rows = []
        for i in range(10):
            rows.append(_make_clock_row(
                game_id=i + 1,
                time_control_bucket="rapid",
                time_control_seconds=600,
                termination="checkmate",
                result="1-0",
                user_color="white",
                ply_array=[0, 1],
                clock_array=[None, None],
            ))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.clock_games == 0
        assert row.user_avg_seconds is None
        assert row.opp_avg_seconds is None
        assert row.avg_clock_diff_seconds is None

    def test_fixed_row_order(self):
        """Rows returned in bullet, blitz, rapid, classical order."""
        rows = []
        for tc, tc_secs in [("rapid", 600), ("bullet", 60), ("classical", 1800), ("blitz", 180)]:
            for i in range(10):
                rows.append(_make_clock_row(
                    game_id=len(rows) + 1,
                    time_control_bucket=tc,
                    time_control_seconds=tc_secs,
                    termination="checkmate",
                    result="1-0",
                    user_color="white",
                    ply_array=[0, 1],
                    clock_array=[20.0, 25.0],
                ))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 4
        assert [r.time_control for r in result.rows] == ["bullet", "blitz", "rapid", "classical"]

    def test_response_totals_include_hidden_rows(self):
        """total_clock_games and total_endgame_games include all time controls, even hidden rows."""
        # 5 bullet games (hidden — below threshold) + 10 blitz games (visible)
        rows = []
        for i in range(5):
            rows.append(_make_clock_row(i + 1, "bullet", 60, "checkmate", "1-0", "white", [0, 1], [5.0, 4.0]))
        for i in range(10):
            rows.append(_make_clock_row(i + 6, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [50.0, 60.0]))
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
            rows.append(_make_clock_row(i + 1, None, None, "checkmate", "1-0", "white", [0, 1], [5.0, 4.0]))
        result = _compute_clock_pressure(rows)
        assert len(result.rows) == 0
        assert result.total_endgame_games == 0


class TestComputeTimePressureChart:
    """Unit tests for _compute_time_pressure_chart (Phase 55).

    Verifies bucket assignment, score averaging, exclusion rules,
    and the minimum games threshold.
    """

    def test_single_game_win_user_bucket_populated(self):
        """Test 1: 10 bullet wins, user 50% time -> user_score=1.0 -> user bucket 5 (50-60%) populated."""
        # time_control_seconds=60, user_clock=30 -> 50% -> bucket index 5
        # opp_clock=20 -> 33% -> bucket index 3
        rows = [_make_clock_row(
            game_id=i + 1,
            time_control_bucket="bullet",
            time_control_seconds=60,
            termination="checkmate",
            result="1-0",
            user_color="white",
            ply_array=[0, 1],
            clock_array=[30.0, 20.0],
        ) for i in range(10)]
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.time_control == "bullet"
        assert len(row.user_series) == 10
        assert len(row.opp_series) == 10
        # User bucket 5 (50-60%) should have score 1.0
        user_bucket5 = row.user_series[5]
        assert user_bucket5.bucket_index == 5
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(1.0)
        # Opp bucket 3 (30-40%) should have score 0.0 (1 - 1.0)
        opp_bucket3 = row.opp_series[3]
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
            rows.append(_make_clock_row(i, "blitz", 180, "checkmate", "1/2-1/2", "white", [0, 1], [90.0, 60.0]))
        result = _compute_time_pressure_chart(rows)
        row = result.rows[0]
        # All games in user bucket 5 (90/180=50%) -> average of 1.0 + 0.0 + 8*0.5 = 5.0 / 10 = 0.5
        user_bucket5 = row.user_series[5]
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(0.5)

    def test_game_without_both_clocks_excluded(self):
        """Test 3: Game without both clocks is excluded from both series."""
        rows = []
        # 9 games with clocks (ply=[0,1] clock=[90,60])
        for i in range(9):
            rows.append(_make_clock_row(i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]))
        # This game has only user ply/clock (no opp) -> opp_clock=None -> excluded from series
        rows.append(_make_clock_row(10, "blitz", 180, "checkmate", "1-0", "white", [0], [90.0]))
        # Total = 10 games -> row appears; only 9 contribute to series
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.total_endgame_games == 10
        # Only 9 games with both clocks contribute to series
        total_user = sum(p.game_count for p in row.user_series)
        assert total_user == 9

    def test_game_without_time_control_seconds_excluded(self):
        """Test 4: Game without time_control_seconds is excluded from chart series."""
        rows = []
        for i in range(10):
            # time_control_seconds=None -> excluded from bucket computation
            rows.append(_make_clock_row(i + 1, "blitz", None, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]))
        result = _compute_time_pressure_chart(rows)
        # 10 games with valid TC bucket -> row appears; but no time_control_seconds -> series empty
        assert len(result.rows) == 1
        row = result.rows[0]
        for p in row.user_series:
            assert p.game_count == 0
            assert p.score is None

    def test_time_control_below_min_games_excluded(self):
        """Test 5: Time control with fewer than MIN_GAMES_FOR_CLOCK_STATS=10 games excluded."""
        rows = [_make_clock_row(i + 1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0])
                for i in range(9)]
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 0

    def test_bucket_clamping_100_percent_time(self):
        """Test 6: 100% time remaining -> clamped to bucket index 9 (not 10)."""
        rows = [_make_clock_row(i + 1, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [600.0, 300.0])
                for i in range(10)]
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # 100% time -> int(100/10)=10, clamped to 9
        user_bucket9 = row.user_series[9]
        assert user_bucket9.bucket_index == 9
        assert user_bucket9.bucket_label == "90-100%"
        assert user_bucket9.game_count == 10

    def test_empty_clock_rows_returns_empty_response(self):
        """Test 7: Empty clock_rows produces response with no rows."""
        result = _compute_time_pressure_chart([])
        assert result.rows == []

    def test_multiple_time_controls_separate_rows(self):
        """Test 8: Multiple time controls produce separate rows in correct order."""
        rows = []
        for i in range(10):
            rows.append(_make_clock_row(i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]))
        for i in range(10):
            rows.append(_make_clock_row(i + 11, "rapid", 600, "checkmate", "1-0", "white", [0, 1], [300.0, 200.0]))
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 2
        # blitz before rapid in _TIME_CONTROL_ORDER
        assert result.rows[0].time_control == "blitz"
        assert result.rows[1].time_control == "rapid"

    def test_user_score_derivation_win_draw_loss(self):
        """Test 9: win=1.0, draw=0.5, loss=0.0 for user_score; opp gets 1-user_score."""
        # 10 games: 4 wins, 3 draws, 3 losses — all at same bucket (50%) so we check the average
        # user_score avg = (4*1.0 + 3*0.5 + 3*0.0) / 10 = 5.5/10 = 0.55
        # opp_score avg = 1 - 0.55 = 0.45
        rows = []
        for i in range(4):
            rows.append(_make_clock_row(i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]))
        for i in range(3):
            rows.append(_make_clock_row(i + 5, "blitz", 180, "checkmate", "1/2-1/2", "white", [0, 1], [90.0, 60.0]))
        for i in range(3):
            rows.append(_make_clock_row(i + 8, "blitz", 180, "checkmate", "0-1", "white", [0, 1], [90.0, 60.0]))
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        # 90/180 = 50% -> bucket index 5
        user_bucket5 = row.user_series[5]
        assert user_bucket5.game_count == 10
        assert user_bucket5.score == pytest.approx(0.55)
        # opp: 60/180 = 33% -> bucket index 3
        opp_bucket3 = row.opp_series[3]
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
            rows.append(_make_clock_row(i + 1, "blitz", 180, "checkmate", "1-0", "white", [0, 1], [90.0, 60.0]))
        # 5 games without clock data (empty arrays) but valid TC bucket
        for i in range(5):
            rows.append(_make_clock_row(i + 6, "blitz", 180, "checkmate", "1-0", "white", [], []))
        result = _compute_time_pressure_chart(rows)
        assert len(result.rows) == 1
        row = result.rows[0]
        assert row.total_endgame_games == 10
