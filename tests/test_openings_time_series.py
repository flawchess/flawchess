"""Service-level integration tests for get_time_series (openings service).

This module tests the rolling-window computation logic in openings_service.py
(lines 182-275), which was previously untested.

Key mechanics under test:
- query_time_series returns rows ordered by played_at ASC.
- For each row the service appends the outcome to results_so_far and slices
  the trailing ROLLING_WINDOW_SIZE entries to compute win_rate.
- data_by_date keeps only the LAST game's rolling window per calendar day.
- The recency filter trims output datapoints (but rolling windows are computed
  over the full chronological history first).
- Totals are recomputed from the filtered period when a recency cutoff is set.

Coverage:
- TestRollingWindow: single game, two same-day games, multi-day sequence, empty position
- TestRecencyFilter: recency trims output; full-history rolling window preserved inside recency window
- TestMultipleBookmarks: two bookmarks produce two BookmarkTimeSeries
"""

import datetime
import uuid
from typing import Literal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.schemas.openings import TimeSeriesBookmarkParam, TimeSeriesRequest
from app.services.openings_service import MIN_GAMES_FOR_TIMELINE, get_time_series

# ---------------------------------------------------------------------------
# User IDs (900-series to avoid collision with other test modules)
# ---------------------------------------------------------------------------

_USER_ROLLING = 901
_USER_RECENCY = 902
_USER_MULTI = 903

_ALL_TEST_USER_IDS = [_USER_ROLLING, _USER_RECENCY, _USER_MULTI]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in users table (FK constraint)."""
    from tests.conftest import ensure_test_user
    for uid in _ALL_TEST_USER_IDS:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_id() -> str:
    return str(uuid.uuid4())


async def _seed_game_with_position(
    session: AsyncSession,
    *,
    user_id: int,
    result: str = "1-0",
    user_color: str = "white",
    played_at: datetime.datetime,
    full_hash: int,
    time_control_bucket: str = "blitz",
    platform: str = "chess.com",
) -> Game:
    """Seed a Game + one GamePosition (at ply=1) for the given full_hash.

    The combination of user_color on Game and full_hash on GamePosition is
    what query_time_series matches against — the bookmark's color parameter
    filters by Game.user_color and the hash_column parameter filters by
    GamePosition.full_hash (for match_side="full").
    """
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_id(),
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=True,
        white_username="testuser",
        black_username="opponent",
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    pos = GamePosition(
        game_id=game.id,
        user_id=user_id,
        ply=1,
        full_hash=full_hash,
        white_hash=full_hash + 1_000_000,
        black_hash=full_hash + 2_000_000,
    )
    session.add(pos)
    await session.flush()

    return game


def _make_request(
    bookmark_id: int,
    target_hash: int,
    color: Literal["white", "black"] = "white",
    match_side: Literal["white", "black", "full"] = "full",
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None,
) -> TimeSeriesRequest:
    """Build a minimal TimeSeriesRequest for one bookmark."""
    return TimeSeriesRequest(
        bookmarks=[
            TimeSeriesBookmarkParam(
                bookmark_id=bookmark_id,
                target_hash=target_hash,
                match_side=match_side,
                color=color,
            )
        ],
        recency=recency,
    )


# ---------------------------------------------------------------------------
# TestRollingWindow — Core rolling window math
# ---------------------------------------------------------------------------


class TestRollingWindow:
    """Verify rolling-window win-rate computation."""

    @pytest.mark.asyncio
    async def test_few_games_filtered_by_min_threshold(self, db_session: AsyncSession) -> None:
        """Games below MIN_GAMES_FOR_TIMELINE produce no data points, but totals are correct."""
        uid = _USER_ROLLING
        fh = 9_100_001

        await _seed_game_with_position(
            db_session,
            user_id=uid,
            result="1-0",
            user_color="white",
            played_at=datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc),
            full_hash=fh,
        )

        response = await get_time_series(
            db_session, uid, _make_request(bookmark_id=1, target_hash=fh, color="white")
        )

        assert len(response.series) == 1
        bts = response.series[0]
        assert bts.bookmark_id == 1
        # Data points filtered out (game_count=1 < MIN_GAMES_FOR_TIMELINE)
        assert len(bts.data) == 0

        # Totals still reflect all games
        assert bts.total_wins == 1
        assert bts.total_draws == 0
        assert bts.total_losses == 0
        assert bts.total_games == 1

    @pytest.mark.asyncio
    async def test_single_loss_filtered_by_min_threshold(self, db_session: AsyncSession) -> None:
        """1 loss -> no data points (below threshold), but totals correct."""
        uid = _USER_ROLLING
        fh = 9_100_002

        await _seed_game_with_position(
            db_session,
            user_id=uid,
            result="0-1",
            user_color="white",
            played_at=datetime.datetime(2026, 3, 2, tzinfo=datetime.timezone.utc),
            full_hash=fh,
        )

        response = await get_time_series(
            db_session, uid, _make_request(bookmark_id=2, target_hash=fh, color="white")
        )

        assert len(response.series) == 1
        assert len(response.series[0].data) == 0
        assert response.series[0].total_losses == 1
        assert response.series[0].total_wins == 0

    @pytest.mark.asyncio
    async def test_multiple_games_same_day_keeps_last(self, db_session: AsyncSession) -> None:
        """Multiple games on the same calendar day -> 1 data point reflecting all in window.

        The rolling window processes games chronologically, but data_by_date
        keeps only the LAST game's snapshot per day. Seeding MIN_GAMES_FOR_TIMELINE
        games (alternating W/L) on the same day verifies same-day collapse and
        that the data point passes the min-games threshold.
        """
        uid = _USER_ROLLING
        fh = 9_100_003
        n = MIN_GAMES_FOR_TIMELINE  # seed exactly the threshold number of games

        wins = 0
        losses = 0
        for i in range(n):
            result = "1-0" if i % 2 == 0 else "0-1"
            if result == "1-0":
                wins += 1
            else:
                losses += 1
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result=result,
                user_color="white",
                played_at=datetime.datetime(2026, 3, 5, 10 + i, 0, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        response = await get_time_series(
            db_session, uid, _make_request(bookmark_id=3, target_hash=fh, color="white")
        )

        bts = response.series[0]
        # Only one data point (same date collapsed)
        assert len(bts.data) == 1
        pt = bts.data[0]
        assert pt.date == "2026-03-05"
        assert pt.win_rate == pytest.approx(wins / n, abs=0.01)
        assert pt.game_count == n

        # Totals
        assert bts.total_games == n
        assert bts.total_wins == wins
        assert bts.total_losses == losses

    @pytest.mark.asyncio
    async def test_win_rate_across_multiple_days(self, db_session: AsyncSession) -> None:
        """12 games across 12 days — first data point appears at MIN_GAMES_FOR_TIMELINE."""
        uid = _USER_ROLLING
        fh = 9_100_004
        n = MIN_GAMES_FOR_TIMELINE

        # 8 wins then 4 losses = 12 games total
        results = ["1-0"] * 8 + ["0-1"] * 4
        for i, result in enumerate(results):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result=result,
                user_color="white",
                played_at=datetime.datetime(2026, 3, 10 + i, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        response = await get_time_series(
            db_session, uid, _make_request(bookmark_id=4, target_hash=fh, color="white")
        )

        bts = response.series[0]
        # Points with game_count < MIN_GAMES_FOR_TIMELINE are filtered out
        total = len(results)
        expected_points = total - n + 1  # first point at game n, then one per day
        assert len(bts.data) == expected_points

        # First visible point has exactly MIN_GAMES_FOR_TIMELINE games in window
        first_pt = bts.data[0]
        assert first_pt.game_count == n

        # Final game (all 12 in window): 8W + 4L ≈ 66.7% win rate
        last_pt = bts.data[-1]
        assert last_pt.win_rate == pytest.approx(8 / 12, abs=0.01)
        assert last_pt.game_count == 12

        # Totals reflect full history
        assert bts.total_games == 12
        assert bts.total_wins == 8
        assert bts.total_losses == 4

    @pytest.mark.asyncio
    async def test_empty_position_returns_empty_series(self, db_session: AsyncSession) -> None:
        """Target hash matching no games -> empty data, total_games=0."""
        uid = _USER_ROLLING
        fh = 9_100_999  # no games seeded for this hash

        response = await get_time_series(
            db_session, uid, _make_request(bookmark_id=99, target_hash=fh, color="white")
        )

        assert len(response.series) == 1
        bts = response.series[0]
        assert bts.data == []
        assert bts.total_games == 0
        assert bts.total_wins == 0
        assert bts.total_draws == 0
        assert bts.total_losses == 0


# ---------------------------------------------------------------------------
# TestRecencyFilter — Recency trimming behaviour
# ---------------------------------------------------------------------------


class TestRecencyFilter:
    """Verify recency filter trims output while rolling windows use full history."""

    @pytest.mark.asyncio
    async def test_recency_filter_trims_old_data(self, db_session: AsyncSession) -> None:
        """Games from >30 days ago are excluded from output when recency='month'.

        Seed: MIN_GAMES_FOR_TIMELINE old games + MIN_GAMES_FOR_TIMELINE recent games.
        recency='month' (30 days) -> only recent games appear in data.
        total_games reflects only the recent period.
        """
        uid = _USER_RECENCY
        fh = 9_200_001
        n = MIN_GAMES_FOR_TIMELINE

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        old_base = now - datetime.timedelta(days=60)
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)

        # n old games (losses) on separate days
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="0-1",
                user_color="white",
                played_at=old_base + datetime.timedelta(days=i),
                full_hash=fh,
            )
        # n recent games (wins) on same day
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=today + datetime.timedelta(minutes=i),
                full_hash=fh,
            )

        request = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=10,
                    target_hash=fh,
                    match_side="full",
                    color="white",
                )
            ],
            recency="month",
        )
        response = await get_time_series(db_session, uid, request)

        bts = response.series[0]
        # Data points should only include recent dates (not old games)
        today_str = today.strftime("%Y-%m-%d")
        for pt in bts.data:
            assert pt.date >= today_str, f"Expected recent date, got {pt.date}"

        # Totals reflect only the filtered period (n recent wins)
        assert bts.total_games == n
        assert bts.total_wins == n
        assert bts.total_losses == 0

    @pytest.mark.asyncio
    async def test_rolling_window_uses_full_history_with_recency(
        self, db_session: AsyncSession
    ) -> None:
        """Rolling window for recent games includes old games in its trailing window.

        Seed: MIN_GAMES_FOR_TIMELINE wins from >30 days ago + 1 loss today.
        With recency='month', only today's datapoint appears in output.
        But the rolling window for today's game includes all games in its
        trailing ROLLING_WINDOW_SIZE, so game_count = n+1.
        """
        uid = _USER_RECENCY
        fh = 9_200_002
        n = MIN_GAMES_FOR_TIMELINE

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        old_base = now - datetime.timedelta(days=45)

        # n old wins
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=old_base + datetime.timedelta(days=i),
                full_hash=fh,
            )

        # 1 recent loss
        today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        await _seed_game_with_position(
            db_session,
            user_id=uid,
            result="0-1",
            user_color="white",
            played_at=today,
            full_hash=fh,
        )

        request = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=11,
                    target_hash=fh,
                    match_side="full",
                    color="white",
                )
            ],
            recency="month",
        )
        response = await get_time_series(db_session, uid, request)

        bts = response.series[0]
        # Only today's datapoint is in the output (recency filter trims the rest)
        today_str = today.strftime("%Y-%m-%d")
        today_points = [pt for pt in bts.data if pt.date == today_str]
        assert len(today_points) >= 1, "Expected at least today's data point"

        pt = today_points[0]
        # Rolling window includes all n+1 games -> win_rate = n/(n+1)
        assert pt.game_count == n + 1
        assert pt.win_rate == pytest.approx(n / (n + 1), abs=0.01)

        # Totals are recomputed from the filtered period only (1 recent loss)
        assert bts.total_losses == 1
        assert bts.total_wins == 0


# ---------------------------------------------------------------------------
# TestMultipleBookmarks — Multi-bookmark request
# ---------------------------------------------------------------------------


class TestMultipleBookmarks:
    """Verify a single TimeSeriesRequest with multiple bookmarks returns separate series."""

    @pytest.mark.asyncio
    async def test_two_bookmarks_return_two_series(
        self, db_session: AsyncSession
    ) -> None:
        """Two bookmarks with different hashes produce two distinct BookmarkTimeSeries."""
        uid = _USER_MULTI
        fh_a = 9_300_001
        fh_b = 9_300_002
        n = MIN_GAMES_FOR_TIMELINE

        # Seed n wins for hash A on separate days
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 2, 1 + i, tzinfo=datetime.timezone.utc),
                full_hash=fh_a,
            )
        # Seed n losses for hash B on separate days
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="0-1",
                user_color="white",
                played_at=datetime.datetime(2026, 2, 1 + i, tzinfo=datetime.timezone.utc),
                full_hash=fh_b,
            )

        request = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=20,
                    target_hash=fh_a,
                    match_side="full",
                    color="white",
                ),
                TimeSeriesBookmarkParam(
                    bookmark_id=21,
                    target_hash=fh_b,
                    match_side="full",
                    color="white",
                ),
            ],
        )
        response = await get_time_series(db_session, uid, request)

        # Two series returned, each keyed by bookmark_id
        assert len(response.series) == 2
        ids = {s.bookmark_id for s in response.series}
        assert ids == {20, 21}

        series_a = next(s for s in response.series if s.bookmark_id == 20)
        series_b = next(s for s in response.series if s.bookmark_id == 21)

        # Hash A: n wins, first data point at game n (threshold)
        assert series_a.total_wins == n
        assert series_a.total_games == n
        assert len(series_a.data) == 1  # only the nth game passes threshold

        # Hash B: n losses
        assert series_b.total_losses == n
        assert series_b.total_games == n
        assert len(series_b.data) == 1
        assert series_b.data[0].win_rate == 0.0

    @pytest.mark.asyncio
    async def test_empty_and_populated_bookmark_together(
        self, db_session: AsyncSession
    ) -> None:
        """One populated bookmark + one with no games: both series returned, one empty."""
        uid = _USER_MULTI
        fh_populated = 9_300_003
        fh_empty = 9_300_999  # no games seeded
        n = MIN_GAMES_FOR_TIMELINE

        # Seed n draws on separate days
        for i in range(n):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1/2-1/2",
                user_color="white",
                played_at=datetime.datetime(2026, 2, 10 + i, tzinfo=datetime.timezone.utc),
                full_hash=fh_populated,
            )

        request = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=30,
                    target_hash=fh_populated,
                    match_side="full",
                    color="white",
                ),
                TimeSeriesBookmarkParam(
                    bookmark_id=31,
                    target_hash=fh_empty,
                    match_side="full",
                    color="white",
                ),
            ],
        )
        response = await get_time_series(db_session, uid, request)

        assert len(response.series) == 2

        series_pop = next(s for s in response.series if s.bookmark_id == 30)
        series_emp = next(s for s in response.series if s.bookmark_id == 31)

        assert len(series_pop.data) == 1  # first point at game n
        assert series_pop.total_draws == n
        assert series_pop.data[0].win_rate == 0.0  # draws -> 0 wins

        assert len(series_emp.data) == 0
        assert series_emp.total_games == 0
