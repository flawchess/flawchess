"""Service-level integration tests for get_time_series (openings service).

This module tests the rolling-window computation logic in openings_service.py,
which was previously untested.

Key mechanics under test:
- query_time_series returns rows ordered by played_at ASC.
- For each row the service appends the outcome to results_so_far and slices
  the trailing ROLLING_WINDOW_SIZE entries to compute the chess score
  (W + 0.5·D) / N.
- data_by_date keeps only the LAST game's rolling window per calendar day.
- Date-windowed emission (D-19 amendment): when from_date/to_date are given,
  only points whose played_at is inside the window are emitted, and WDL totals
  count only in-window games. The rolling average is warmed from games before
  the window start (warm-up preserved).

Coverage:
- TestTimeSeriesRequestSchema: TimeSeriesRequest has no recency field (D-19);
  exposes from_date and to_date (D-19 amendment)
- TestRollingWindow: single game, two same-day games, multi-day sequence, empty position
- TestMultipleBookmarks: two bookmarks produce two BookmarkTimeSeries
- TestDateWindowedTimeSeries: from_date/to_date windowing + warm-up preservation
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
from app.services.openings_service import (
    MIN_GAMES_FOR_TIMELINE,
    ROLLING_WINDOW_SIZE,
    get_time_series,
)

# ---------------------------------------------------------------------------
# TestTimeSeriesRequestSchema — D-19: recency field removed from TimeSeriesRequest
# D-19 amendment: from_date/to_date added for date-windowed totals + emission
# ---------------------------------------------------------------------------


class TestTimeSeriesRequestSchema:
    """Verify TimeSeriesRequest exposes from_date/to_date but NOT recency (D-19 + amendment)."""

    def test_no_recency_field_in_schema(self) -> None:
        """TimeSeriesRequest model fields must not include 'recency' (D-19)."""
        assert "recency" not in TimeSeriesRequest.model_fields, (
            "TimeSeriesRequest must not have a 'recency' field — D-19 removes it "
            "so the time-series endpoint uses resolved date bounds, not preset labels."
        )

    def test_from_date_field_exists(self) -> None:
        """TimeSeriesRequest must expose from_date (D-19 amendment)."""
        assert "from_date" in TimeSeriesRequest.model_fields, (
            "TimeSeriesRequest must have a 'from_date' field (D-19 amendment: "
            "totals + emitted points are now date-windowed while the rolling "
            "average is warmed from pre-window games)."
        )

    def test_to_date_field_exists(self) -> None:
        """TimeSeriesRequest must expose to_date (D-19 amendment)."""
        assert "to_date" in TimeSeriesRequest.model_fields, (
            "TimeSeriesRequest must have a 'to_date' field (D-19 amendment)."
        )

    def test_from_date_defaults_to_none(self) -> None:
        """from_date defaults to None (open lower bound = full history behavior)."""
        req = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=1, target_hash=1, match_side="full", color="white"
                )
            ]
        )
        assert req.from_date is None

    def test_to_date_defaults_to_none(self) -> None:
        """to_date defaults to None (open upper bound = full history behavior)."""
        req = TimeSeriesRequest(
            bookmarks=[
                TimeSeriesBookmarkParam(
                    bookmark_id=1, target_hash=1, match_side="full", color="white"
                )
            ]
        )
        assert req.to_date is None

    def test_date_range_validation_rejects_inverted_range(self) -> None:
        """from_date > to_date must raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="from_date must be <= to_date"):
            TimeSeriesRequest(
                bookmarks=[
                    TimeSeriesBookmarkParam(
                        bookmark_id=1, target_hash=1, match_side="full", color="white"
                    )
                ],
                from_date=datetime.date(2026, 6, 1),
                to_date=datetime.date(2026, 5, 1),
            )


# ---------------------------------------------------------------------------
# User IDs (900-series to avoid collision with other test modules)
# ---------------------------------------------------------------------------

_USER_ROLLING = 901
_USER_MULTI = 903
_USER_DATE_WINDOW = 905

_ALL_TEST_USER_IDS = [_USER_ROLLING, _USER_MULTI, _USER_DATE_WINDOW]


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
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
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
        from_date=from_date,
        to_date=to_date,
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
        # Pure W/L (no draws): score == wins / n
        assert pt.score == pytest.approx(wins / n, abs=0.01)
        assert pt.game_count == n

        # Totals
        assert bts.total_games == n
        assert bts.total_wins == wins
        assert bts.total_losses == losses

    @pytest.mark.asyncio
    async def test_score_across_multiple_days(self, db_session: AsyncSession) -> None:
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

        # Final game (all 12 in window): 8W + 4L (no draws) -> score = 8/12
        last_pt = bts.data[-1]
        assert last_pt.score == pytest.approx(8 / 12, abs=0.01)
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
# TestMultipleBookmarks — Multi-bookmark request
# ---------------------------------------------------------------------------


class TestMultipleBookmarks:
    """Verify a single TimeSeriesRequest with multiple bookmarks returns separate series."""

    @pytest.mark.asyncio
    async def test_two_bookmarks_return_two_series(self, db_session: AsyncSession) -> None:
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
        assert series_b.data[0].score == 0.0

    @pytest.mark.asyncio
    async def test_empty_and_populated_bookmark_together(self, db_session: AsyncSession) -> None:
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
        # All draws -> score = 0.5 * n / n = 0.5
        assert series_pop.data[0].score == 0.5

        assert len(series_emp.data) == 0
        assert series_emp.total_games == 0


# ---------------------------------------------------------------------------
# TestDateWindowedTimeSeries — D-19 amendment: from_date/to_date windowing
# ---------------------------------------------------------------------------


class TestDateWindowedTimeSeries:
    """Verify date-windowed totals + warm-up rolling emission (D-19 amendment).

    Key invariants tested:
    - Totals (total_wins/draws/losses/total_games) count only in-window games.
    - Emitted TimeSeriesPoint.date values all fall within [from_date, to_date].
    - Rolling average is warmed from pre-window games (warm-up preserved):
      the first emitted point at/after from_date reports game_count ==
      ROLLING_WINDOW_SIZE when exactly ROLLING_WINDOW_SIZE games were played
      before the window start.
    - A zero-match window yields total_games==0, empty data, last_played_at=None.
    """

    @pytest.mark.asyncio
    async def test_windowed_totals_exclude_out_of_window_games(
        self, db_session: AsyncSession
    ) -> None:
        """Totals from a date-windowed request only count in-window games.

        Setup: 3 wins before the window, 2 losses inside the window.
        Expected: total_games=2, total_wins=0, total_losses=2.
        Full-history call returns total_games=5 to prove the totals differ.
        """
        uid = _USER_DATE_WINDOW
        fh = 9_500_001

        # 3 wins before the window (January 2026)
        for day in range(1, 4):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 1, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        # 2 losses inside the window (March 2026)
        for day in range(1, 3):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="0-1",
                user_color="white",
                played_at=datetime.datetime(2026, 3, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        window_from = datetime.date(2026, 2, 1)
        window_to = datetime.date(2026, 3, 31)

        windowed = await get_time_series(
            db_session,
            uid,
            _make_request(
                bookmark_id=40,
                target_hash=fh,
                color="white",
                from_date=window_from,
                to_date=window_to,
            ),
        )
        bts = windowed.series[0]

        # Only the 2 in-window losses are counted in totals
        assert bts.total_games == 2
        assert bts.total_wins == 0
        assert bts.total_losses == 2
        assert bts.total_draws == 0

        # Full-history call gives different (higher) total
        full = await get_time_series(
            db_session,
            uid,
            _make_request(bookmark_id=40, target_hash=fh, color="white"),
        )
        assert full.series[0].total_games == 5

    @pytest.mark.asyncio
    async def test_emitted_points_fall_inside_window(self, db_session: AsyncSession) -> None:
        """Every emitted TimeSeriesPoint.date is within [from_date, to_date].

        Setup: enough games spread across January + February + March that
        the unfiltered series would span all three months. The windowed request
        covers February only — all emitted points must be in February.
        """
        uid = _USER_DATE_WINDOW
        fh = 9_500_002
        n = MIN_GAMES_FOR_TIMELINE

        # Seed n games in January (pre-window)
        for day in range(1, n + 1):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 1, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        # Seed n games in February (in-window)
        for day in range(1, n + 1):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 2, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        # Seed n games in March (post-window)
        for day in range(1, n + 1):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 3, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        window_from = datetime.date(2026, 2, 1)
        window_to = datetime.date(2026, 2, 28)

        response = await get_time_series(
            db_session,
            uid,
            _make_request(
                bookmark_id=41,
                target_hash=fh,
                color="white",
                from_date=window_from,
                to_date=window_to,
            ),
        )
        bts = response.series[0]

        # Must have at least one emitted point (February games are in-window)
        assert len(bts.data) > 0

        # Every emitted point's date must be within the window
        for pt in bts.data:
            pt_date = datetime.date.fromisoformat(pt.date)
            assert pt_date >= window_from, f"Point {pt.date} is before from_date {window_from}"
            assert pt_date <= window_to, f"Point {pt.date} is after to_date {window_to}"

    @pytest.mark.asyncio
    async def test_warm_up_preserved_at_window_boundary(self, db_session: AsyncSession) -> None:
        """First emitted point at window start reports game_count == ROLLING_WINDOW_SIZE.

        Setup:
        - Seed exactly ROLLING_WINDOW_SIZE wins before the window (Jan + Feb 2025,
          multiple games per day spaced 30 minutes apart to fit within month bounds).
        - Seed 1 win on the window start day (Mar 1 2026).
        - from_date = Mar 1 2026.

        The service processes all rows chronologically. When it reaches the Mar
        game, results_so_far has ROLLING_WINDOW_SIZE+1 entries, so the trailing
        slice is ROLLING_WINDOW_SIZE. The Mar point's game_count must be
        ROLLING_WINDOW_SIZE (not 1 as it would be with a reset).

        This also proves the trailing average reflects pre-window games: if the
        rolling accumulator were reset at the window boundary, game_count would be 1.
        """
        uid = _USER_DATE_WINDOW
        fh = 9_500_003
        warmup_games = ROLLING_WINDOW_SIZE  # 50 pre-window games

        # Seed ROLLING_WINDOW_SIZE wins before the window.
        # Use 2025 so they are well before the 2026 window.
        # Spread across multiple days (up to 28 games in Feb, the rest in Jan)
        # using hour offsets so each game has a distinct timestamp (and thus
        # distinct played_at for correct ordering).
        jan_games = min(warmup_games, 28)  # fill February first to avoid month-overflow
        feb_games = warmup_games - jan_games
        game_index = 0
        for i in range(jan_games):
            # Jan 1–28, hour 0–23 cycling, minute ticks for uniqueness
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(
                    2025,
                    1,
                    (i % 28) + 1,
                    i % 24,
                    game_index % 60,
                    tzinfo=datetime.timezone.utc,
                ),
                full_hash=fh,
            )
            game_index += 1
        for i in range(feb_games):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(
                    2025,
                    2,
                    (i % 28) + 1,
                    i % 24,
                    game_index % 60,
                    tzinfo=datetime.timezone.utc,
                ),
                full_hash=fh,
            )
            game_index += 1

        # One win on Mar 1 2026 (in-window)
        await _seed_game_with_position(
            db_session,
            user_id=uid,
            result="1-0",
            user_color="white",
            played_at=datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc),
            full_hash=fh,
        )

        window_from = datetime.date(2026, 3, 1)
        window_to = datetime.date(2026, 3, 31)

        response = await get_time_series(
            db_session,
            uid,
            _make_request(
                bookmark_id=42,
                target_hash=fh,
                color="white",
                from_date=window_from,
                to_date=window_to,
            ),
        )
        bts = response.series[0]

        # The March game is the only emitted point
        assert len(bts.data) == 1
        pt = bts.data[0]
        assert pt.date == "2026-03-01"

        # Warm-up preserved: game_count == ROLLING_WINDOW_SIZE (not 1)
        assert pt.game_count == ROLLING_WINDOW_SIZE, (
            f"Expected game_count={ROLLING_WINDOW_SIZE} (warm-up from pre-window games), "
            f"got {pt.game_count}. A reset-to-1 would indicate warm-up was not preserved."
        )

        # Totals count only the 1 in-window game
        assert bts.total_games == 1
        assert bts.total_wins == 1

    @pytest.mark.asyncio
    async def test_zero_match_window_returns_empty(self, db_session: AsyncSession) -> None:
        """A from_date/to_date window with no matching games returns empty results.

        total_games == 0, data == [], last_played_at is None.
        """
        uid = _USER_DATE_WINDOW
        fh = 9_500_004
        n = MIN_GAMES_FOR_TIMELINE

        # Seed n games in January
        for day in range(1, n + 1):
            await _seed_game_with_position(
                db_session,
                user_id=uid,
                result="1-0",
                user_color="white",
                played_at=datetime.datetime(2026, 1, day, tzinfo=datetime.timezone.utc),
                full_hash=fh,
            )

        # Request a window in June — no games there
        window_from = datetime.date(2026, 6, 1)
        window_to = datetime.date(2026, 6, 30)

        response = await get_time_series(
            db_session,
            uid,
            _make_request(
                bookmark_id=43,
                target_hash=fh,
                color="white",
                from_date=window_from,
                to_date=window_to,
            ),
        )
        bts = response.series[0]

        assert bts.total_games == 0
        assert bts.total_wins == 0
        assert bts.total_draws == 0
        assert bts.total_losses == 0
        assert bts.data == []
        assert bts.last_played_at is None
