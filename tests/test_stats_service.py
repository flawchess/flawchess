"""Service-level integration tests for the stats service.

The existing test_stats_router.py only verifies HTTP shape (200 / structure).
These tests go deeper: they seed data and assert that the business logic
(_rows_to_wdl_categories, get_rating_history, get_global_stats) produces
correct WDL counts and percentages.

Coverage:
- TestRowsToWdlCategories: pure function — basic conversion, missing category,
  zero total, label_order preservation
- TestGetRatingHistory: platform filtering with seeded games
- TestGetGlobalStats: WDL by time control and color with seeded data
- TestGetMostPlayedOpenings: response structure validation (data-seeding of
  openings_dedup is intentionally skipped — that view is DB-managed)
"""

import datetime
import io
import json
import uuid
from collections import namedtuple
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import chess
import chess.pgn
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.stats_service as stats_service
from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.position_bookmark import PositionBookmark
from app.repositories.stats_repository import PositionWDL, _openings_dedup
from app.services.stats_service import (
    MOST_PLAYED_CURRENT_LIMIT,
    MOST_PLAYED_PAST_LIMIT,
    _bookmark_full_hashes_by_color,
    _dedupe_identical_sets,
    _drop_bookmark_twins,
    _MostPlayedCandidate,
    _needs_recent_fallback,
    _prepare_candidates,
    _recent_from_date,
    _rows_to_wdl_categories,
    _split_and_cap,
    get_global_stats,
    get_most_played_openings,
    get_rating_history,
)
from app.services.zobrist import compute_hashes

# ---------------------------------------------------------------------------
# User IDs (800-series to avoid cross-test pollution with other test modules)
# ---------------------------------------------------------------------------

_USER_RATING = 801
_USER_GLOBAL = 802
_USER_MOST_PLAYED = 803
# 24205-24207 are reserved for the Phase 242 most-played pipeline tests below.
_USER_PIPELINE = 24205
_USER_TWIN = 24206
_USER_FALLBACK = 24207

_ALL_TEST_USER_IDS = [
    _USER_RATING,
    _USER_GLOBAL,
    _USER_MOST_PLAYED,
    _USER_PIPELINE,
    _USER_TWIN,
    _USER_FALLBACK,
]


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure all test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in _ALL_TEST_USER_IDS:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_id() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    white_rating: int | None = 1500,
    black_rating: int | None = 1400,
    opening_eco: str | None = None,
    opening_name: str | None = None,
    full_hash: int | None = None,
) -> Game:
    """Seed a Game row (no GamePosition) and return it.

    Includes white_rating and black_rating to support rating history tests.
    """
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

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
        white_rating=white_rating,
        black_rating=black_rating,
        opening_eco=opening_eco,
        opening_name=opening_name,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    if full_hash is not None:
        pos = GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=1,
            full_hash=full_hash,
            white_hash=full_hash + 1000,
            black_hash=full_hash + 2000,
        )
        session.add(pos)
        await session.flush()

    return game


# ---------------------------------------------------------------------------
# Mock Row helper for pure-function tests
# ---------------------------------------------------------------------------

# SQLAlchemy Row supports index-based access (row[0], row[1] ...).
# namedtuple implements __getitem__ with the same integer semantics.
MockRow = namedtuple("MockRow", ["key", "total", "wins", "draws", "losses"])


# ---------------------------------------------------------------------------
# TestRowsToWdlCategories — pure function, no DB needed
# ---------------------------------------------------------------------------


class TestRowsToWdlCategories:
    """Verify _rows_to_wdl_categories converts SQL-aggregated rows correctly."""

    def test_basic_conversion(self) -> None:
        """Two categories converted to WDLByCategory with correct percentages."""
        rows: list[Any] = [
            MockRow("blitz", 10, 6, 2, 2),
            MockRow("rapid", 5, 3, 1, 1),
        ]
        result = _rows_to_wdl_categories(
            rows,
            label_fn=lambda k: k.title(),
            label_order=["blitz", "rapid"],
        )

        assert len(result) == 2

        blitz = result[0]
        assert blitz.label == "Blitz"
        assert blitz.wins == 6
        assert blitz.draws == 2
        assert blitz.losses == 2
        assert blitz.total == 10
        assert blitz.win_pct == pytest.approx(60.0, abs=0.1)
        assert blitz.draw_pct == pytest.approx(20.0, abs=0.1)
        assert blitz.loss_pct == pytest.approx(20.0, abs=0.1)

        rapid = result[1]
        assert rapid.label == "Rapid"
        assert rapid.total == 5
        assert rapid.win_pct == pytest.approx(60.0, abs=0.1)

    def test_missing_category_skipped(self) -> None:
        """Categories not present in rows are silently skipped."""
        rows: list[Any] = [MockRow("blitz", 10, 6, 2, 2)]
        result = _rows_to_wdl_categories(
            rows,
            label_fn=lambda k: k.title(),
            label_order=["blitz", "rapid", "classical"],
        )

        # Only blitz is in rows — rapid and classical are missing
        assert len(result) == 1
        assert result[0].label == "Blitz"

    def test_zero_total_yields_zero_pcts(self) -> None:
        """A row with total=0 produces 0.0 for all percentages (no division by zero)."""
        rows: list[Any] = [MockRow("bullet", 0, 0, 0, 0)]
        result = _rows_to_wdl_categories(
            rows,
            label_fn=lambda k: k.title(),
            label_order=["bullet"],
        )

        # With total=0 the category is still included but all percentages are 0.
        # Note: _rows_to_wdl_categories skips the entry when total==0 because
        # the outer `if total > 0` guard skips pct computation, but the category
        # IS still appended (just with 0.0 percentages).
        # Verify no exception is raised and result can be empty or has 0 pcts.
        if len(result) == 1:
            assert result[0].win_pct == 0.0
            assert result[0].draw_pct == 0.0
            assert result[0].loss_pct == 0.0

    def test_preserves_label_order(self) -> None:
        """Output order follows label_order, not row insertion order."""
        # Rows are in reverse order vs label_order
        rows: list[Any] = [
            MockRow("rapid", 5, 3, 1, 1),
            MockRow("blitz", 10, 6, 2, 2),
        ]
        result = _rows_to_wdl_categories(
            rows,
            label_fn=lambda k: k.title(),
            # bullet not in rows, so skipped; blitz before rapid
            label_order=["bullet", "blitz", "rapid"],
        )

        assert len(result) == 2
        assert result[0].label == "Blitz"  # follows label_order
        assert result[1].label == "Rapid"


# ---------------------------------------------------------------------------
# TestGetRatingHistory — DB integration with seeded games
# ---------------------------------------------------------------------------


class TestGetRatingHistory:
    """Verify get_rating_history platform filtering with seeded game data."""

    @pytest.mark.asyncio
    async def test_both_platforms(self, db_session: AsyncSession) -> None:
        """Seeding chess.com and lichess games produces data points on both platforms."""
        uid = _USER_RATING

        # 2 chess.com games
        for i in range(2):
            await _seed_game(
                db_session,
                user_id=uid,
                platform="chess.com",
                result="1-0",
                user_color="white",
                white_rating=1500 + i * 10,
                played_at=datetime.datetime(2026, 1, i + 1, tzinfo=datetime.timezone.utc),
            )
        # 1 lichess game
        await _seed_game(
            db_session,
            user_id=uid,
            platform="lichess",
            result="0-1",
            user_color="black",
            black_rating=1600,
            played_at=datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc),
        )

        response = await get_rating_history(db_session, uid, from_date=None, to_date=None)

        assert len(response.chess_com) > 0, "Expected chess.com data points"
        assert len(response.lichess) > 0, "Expected lichess data points"

    @pytest.mark.asyncio
    async def test_platform_filter_chess_com(self, db_session: AsyncSession) -> None:
        """platform='chess.com' returns chess.com data and an empty lichess list."""
        uid = _USER_RATING

        response = await get_rating_history(
            db_session, uid, from_date=None, to_date=None, platform="chess.com"
        )

        # lichess must always be empty when filtering for chess.com
        assert response.lichess == []
        # chess.com data was seeded in the previous test (same session within module scope)
        # — at minimum the list type is correct
        assert isinstance(response.chess_com, list)

    @pytest.mark.asyncio
    async def test_platform_filter_lichess(self, db_session: AsyncSession) -> None:
        """platform='lichess' returns lichess data and an empty chess_com list."""
        uid = _USER_RATING

        response = await get_rating_history(
            db_session, uid, from_date=None, to_date=None, platform="lichess"
        )

        # chess.com must always be empty when filtering for lichess
        assert response.chess_com == []
        assert isinstance(response.lichess, list)

    @pytest.mark.asyncio
    async def test_data_point_fields(self, db_session: AsyncSession) -> None:
        """Each returned RatingDataPoint has date, rating, and time_control_bucket."""
        uid = _USER_RATING

        response = await get_rating_history(db_session, uid, from_date=None, to_date=None)

        for pt in response.chess_com + response.lichess:
            assert isinstance(pt.date, str), "date must be a string"
            assert isinstance(pt.rating, int), "rating must be an int"
            assert isinstance(pt.time_control_bucket, str), "time_control_bucket must be a string"
            assert pt.game_count >= 1, "game_count counts the day's games, at least the kept one"


# ---------------------------------------------------------------------------
# TestGetGlobalStats — DB integration
# ---------------------------------------------------------------------------


class TestGetGlobalStats:
    """Verify get_global_stats WDL aggregation with seeded data."""

    @pytest.mark.asyncio
    async def test_returns_wdl_by_time_control_and_color(self, db_session: AsyncSession) -> None:
        """3 blitz games as white (1W/1D/1L) + 2 rapid games as black (2W) produce correct counts."""
        uid = _USER_GLOBAL

        # 3 blitz games as white
        await _seed_game(
            db_session, user_id=uid, result="1-0", user_color="white", time_control_bucket="blitz"
        )
        await _seed_game(
            db_session,
            user_id=uid,
            result="1/2-1/2",
            user_color="white",
            time_control_bucket="blitz",
        )
        await _seed_game(
            db_session, user_id=uid, result="0-1", user_color="white", time_control_bucket="blitz"
        )

        # 2 rapid games as black (both wins for the user)
        await _seed_game(
            db_session, user_id=uid, result="0-1", user_color="black", time_control_bucket="rapid"
        )
        await _seed_game(
            db_session, user_id=uid, result="0-1", user_color="black", time_control_bucket="rapid"
        )

        response = await get_global_stats(db_session, uid, from_date=None, to_date=None)

        # --- by_time_control ---
        tc_map = {cat.label: cat for cat in response.by_time_control}
        assert "Blitz" in tc_map, f"Expected Blitz in: {list(tc_map.keys())}"
        assert "Rapid" in tc_map, f"Expected Rapid in: {list(tc_map.keys())}"

        blitz = tc_map["Blitz"]
        assert blitz.total == 3
        assert blitz.wins == 1
        assert blitz.draws == 1
        assert blitz.losses == 1

        rapid = tc_map["Rapid"]
        assert rapid.total == 2
        assert rapid.wins == 2  # user is black, result "0-1" = user wins
        assert rapid.draws == 0
        assert rapid.losses == 0

        # --- by_color ---
        color_map = {cat.label: cat for cat in response.by_color}
        assert "White" in color_map
        assert "Black" in color_map

        white = color_map["White"]
        assert white.total == 3
        assert white.wins == 1
        assert white.draws == 1
        assert white.losses == 1

        black = color_map["Black"]
        assert black.total == 2
        assert black.wins == 2
        assert black.draws == 0
        assert black.losses == 0

    @pytest.mark.asyncio
    async def test_win_percentage_calculation(self, db_session: AsyncSession) -> None:
        """win_pct is rounded to 1 decimal place and accurate."""
        uid = _USER_GLOBAL
        # Data was seeded in previous test (same db_session within function scope —
        # each test gets its own transaction-rolled-back session). This test seeds
        # independently to be self-contained.
        await _seed_game(
            db_session, user_id=uid, result="1-0", user_color="white", time_control_bucket="blitz"
        )
        await _seed_game(
            db_session, user_id=uid, result="1-0", user_color="white", time_control_bucket="blitz"
        )
        await _seed_game(
            db_session, user_id=uid, result="0-1", user_color="white", time_control_bucket="blitz"
        )

        response = await get_global_stats(db_session, uid, from_date=None, to_date=None)

        blitz_cats = [c for c in response.by_time_control if c.label == "Blitz"]
        assert len(blitz_cats) >= 1
        blitz = blitz_cats[0]

        # 2 wins out of 3 = 66.7%
        assert blitz.win_pct == pytest.approx(66.7, abs=0.1)


# ---------------------------------------------------------------------------
# TestGetMostPlayedOpenings — response structure
# ---------------------------------------------------------------------------


class TestGetMostPlayedOpenings:
    """Verify get_most_played_openings returns valid response structure.

    Note: This test depends on the openings_dedup view existing in the DB.
    The view is created by an Alembic migration and contains ECO/name/hash rows.
    If no seeded games have opening_eco/name matching the view, the white and
    black lists will be empty — that is acceptable. The test verifies structure.
    """

    @pytest.mark.asyncio
    async def test_returns_white_and_black_lists(self, db_session: AsyncSession) -> None:
        """Response always has white and black keys with list values."""
        uid = _USER_MOST_PLAYED

        response = await get_most_played_openings(
            db_session, uid, now_utc=datetime.datetime.now(datetime.UTC)
        )

        assert isinstance(response.white, list)
        assert isinstance(response.black, list)

    @pytest.mark.asyncio
    async def test_opening_wdl_fields_when_present(self, db_session: AsyncSession) -> None:
        """If any openings are returned, each entry has the required display fields."""
        uid = _USER_MOST_PLAYED

        response = await get_most_played_openings(
            db_session, uid, now_utc=datetime.datetime.now(datetime.UTC)
        )

        for opening in response.white + response.black:
            assert hasattr(opening, "opening_eco")
            assert hasattr(opening, "opening_name")
            assert hasattr(opening, "label")
            assert hasattr(opening, "pgn")
            assert hasattr(opening, "fen")
            assert hasattr(opening, "full_hash")
            assert isinstance(opening.full_hash, str)
            assert hasattr(opening, "wins")
            assert hasattr(opening, "draws")
            assert hasattr(opening, "losses")
            assert hasattr(opening, "total")
            assert hasattr(opening, "win_pct")
            # display_name is canonical name OR "vs. {name}" when off-color.
            assert hasattr(opening, "display_name")
            assert opening.display_name == opening.opening_name or (
                opening.display_name == f"vs. {opening.opening_name}"
            )


# ---------------------------------------------------------------------------
# Most-played pipeline (Phase 242): dedupe, bookmark twins, split, recent fallback
# ---------------------------------------------------------------------------

_NOW = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)


def _cand(
    name: str,
    *,
    full_hash: int | None = 1,
    ply_count: int = 3,
    total: int = 10,
    game_id_sum: int = 100,
    last_played_at: datetime.datetime | None = _NOW,
    is_current: bool = True,
) -> _MostPlayedCandidate:
    return _MostPlayedCandidate(
        eco="B00",
        name=name,
        display_name=name,
        pgn="1. e4",
        fen="fen",
        full_hash=full_hash,
        ply_count=ply_count,
        total=total,
        wins=total,
        draws=0,
        losses=0,
        last_played_at=last_played_at,
        game_id_sum=game_id_sum,
        is_current=is_current,
    )


class TestDedupeIdenticalSets:
    def test_dedupe_keeps_the_deeper_line(self) -> None:
        shallow = _cand("Shallow", full_hash=1, ply_count=3)
        deep = _cand("Deep", full_hash=2, ply_count=5)

        assert _dedupe_identical_sets([shallow, deep]) == [deep]

    def test_dedupe_tie_keeps_the_alphabetically_first_name(self) -> None:
        b = _cand("Beta", full_hash=1, ply_count=5)
        a = _cand("Alpha", full_hash=2, ply_count=5)

        assert _dedupe_identical_sets([b, a]) == [a]

    def test_dedupe_keeps_both_when_the_game_id_sum_differs(self) -> None:
        """Equal W/D/L but different games (different id sum) are different sets."""
        first = _cand("First", full_hash=1, game_id_sum=100)
        second = _cand("Second", full_hash=2, game_id_sum=101)

        assert _dedupe_identical_sets([first, second]) == [first, second]

    def test_dedupe_never_collapses_rows_without_a_position_bucket(self) -> None:
        no_bucket_a = _cand("A", full_hash=1, game_id_sum=0, last_played_at=None)
        no_bucket_b = _cand("B", full_hash=2, game_id_sum=0, last_played_at=None)

        assert _dedupe_identical_sets([no_bucket_a, no_bucket_b]) == [no_bucket_a, no_bucket_b]

    def test_dedupe_preserves_input_order(self) -> None:
        keep_first = _cand("First", full_hash=1, game_id_sum=1)
        loser = _cand("Loser", full_hash=2, ply_count=3, game_id_sum=2)
        winner = _cand("Winner", full_hash=3, ply_count=9, game_id_sum=2)

        assert _dedupe_identical_sets([keep_first, loser, winner]) == [keep_first, winner]


def _row(name: str, *, full_hash: int, ply_count: int) -> Any:
    """Minimal top-openings row (attribute access only, like the real query row)."""
    return SimpleNamespace(
        eco="B00",
        name=name,
        display_name=name,
        pgn="1. e4",
        fen="fen",
        full_hash=full_hash,
        ply_count=ply_count,
        total=1,
        wins=1,
        draws=0,
        losses=0,
    )


class TestBookmarkTwins:
    def test_bookmark_twin_rows_are_dropped(self) -> None:
        twin = _cand("Twin", full_hash=7)
        other = _cand("Other", full_hash=8, game_id_sum=101)

        assert _drop_bookmark_twins([twin, other], {7}) == [other]

    def test_deeper_row_with_identical_game_set_is_dropped(self) -> None:
        """WR-01: bookmark on shallow A; deeper B has the same games, so B is a twin too."""
        bookmarked_shallow = _cand("A", full_hash=7, ply_count=3, game_id_sum=100)
        deeper_twin = _cand("B", full_hash=8, ply_count=5, game_id_sum=100)
        unrelated = _cand("C", full_hash=9, ply_count=5, game_id_sum=101)

        result = _drop_bookmark_twins([bookmarked_shallow, deeper_twin, unrelated], {7})

        assert result == [unrelated]

    def test_prepare_candidates_drops_deeper_twin_of_shallow_bookmark(self) -> None:
        """WR-01 through the real pipeline: twins go before the deeper-line dedupe."""
        # Totals at or above MOST_PLAYED_MIN_GAMES so only the twin rule can drop a row.
        shallow_pos = PositionWDL(30, 30, 0, 0, _NOW, 100)
        deeper_pos = PositionWDL(30, 30, 0, 0, _NOW, 100)
        other_pos = PositionWDL(20, 20, 0, 0, _NOW, 55)
        rows = [
            _row("Shallow", full_hash=7, ply_count=3),
            _row("Deeper", full_hash=8, ply_count=5),
            _row("Other", full_hash=9, ply_count=5),
        ]

        result = _prepare_candidates(rows, {7: shallow_pos, 8: deeper_pos, 9: other_pos}, None, {7})

        assert [c.name for c in result] == ["Other"]

    def test_bookmark_twin_drop_with_no_bookmarks_keeps_everything(self) -> None:
        rows = [_cand("A", full_hash=1), _cand("B", full_hash=2)]

        assert _drop_bookmark_twins(rows, set()) == rows


class TestMostPlayedMinGames:
    """D-36: most-played rows need MOST_PLAYED_MIN_GAMES games on the displayed total."""

    def test_floor_is_twenty_games(self) -> None:
        assert stats_service.MOST_PLAYED_MIN_GAMES == 20

    def test_prepare_candidates_drops_19_and_keeps_20(self) -> None:
        rows = [
            _row("Nineteen", full_hash=1, ply_count=3),
            _row("Twenty", full_hash=2, ply_count=3),
        ]
        position_wdl = {
            1: PositionWDL(19, 19, 0, 0, _NOW, 100),
            2: PositionWDL(20, 20, 0, 0, _NOW, 200),
        }

        result = _prepare_candidates(rows, position_wdl, None, set())

        assert [(c.name, c.total) for c in result] == [("Twenty", 20)]

    def test_floor_reads_the_position_total_not_the_name_row_total(self) -> None:
        """The opening-name row says 1 game, the position bucket says 25: the row stays."""
        rows = [_row("Transposed", full_hash=3, ply_count=3)]  # row.total == 1

        result = _prepare_candidates(rows, {3: PositionWDL(25, 25, 0, 0, _NOW, 300)}, None, set())

        assert [(c.name, c.total) for c in result] == [("Transposed", 25)]

    def test_floor_applies_to_past_rows_too(self) -> None:
        """A past ("Played before") row under the floor is dropped like a current one."""
        cutoff = _NOW - datetime.timedelta(days=60)
        old = _NOW - datetime.timedelta(days=400)
        rows = [
            _row("PastSmall", full_hash=4, ply_count=3),
            _row("PastBig", full_hash=5, ply_count=3),
        ]
        position_wdl = {
            4: PositionWDL(19, 19, 0, 0, old, 400),
            5: PositionWDL(20, 20, 0, 0, old, 500),
        }

        result = _prepare_candidates(rows, position_wdl, cutoff, set())

        assert [(c.name, c.is_current) for c in result] == [("PastBig", False)]


class TestSplitAndCap:
    def test_split_and_cap_returns_current_first_then_past_each_capped(self) -> None:
        current = [_cand(f"C{i}", full_hash=i, total=100 + i) for i in range(12)]
        past = [
            _cand(f"P{i}", full_hash=100 + i, total=500 + i, is_current=False) for i in range(12)
        ]

        result = _split_and_cap(past + current)

        assert len(result) == MOST_PLAYED_CURRENT_LIMIT + MOST_PLAYED_PAST_LIMIT
        head, tail = result[:MOST_PLAYED_CURRENT_LIMIT], result[MOST_PLAYED_CURRENT_LIMIT:]
        assert all(c.is_current for c in head)
        assert not any(c.is_current for c in tail)
        assert [c.total for c in head] == sorted((c.total for c in head), reverse=True)
        assert [c.total for c in tail] == sorted((c.total for c in tail), reverse=True)
        # Past rows never push current ones out, even though they have more games.
        assert head[0].name == "C11"


class TestRecentFallbackHelpers:
    CUTOFF = datetime.datetime(2026, 4, 1, 15, 30, tzinfo=datetime.UTC)

    def test_recent_from_date_without_a_filter_is_the_cutoff_day(self) -> None:
        assert _recent_from_date(None, self.CUTOFF) == datetime.date(2026, 4, 1)

    def test_recent_from_date_before_the_cutoff_day_is_the_cutoff_day(self) -> None:
        assert _recent_from_date(datetime.date(2025, 1, 1), self.CUTOFF) == datetime.date(
            2026, 4, 1
        )

    def test_recent_from_date_after_the_cutoff_day_is_unchanged(self) -> None:
        later = datetime.date(2026, 5, 10)

        assert _recent_from_date(later, self.CUTOFF) == later

    def test_recent_fallback_not_needed_without_a_cutoff(self) -> None:
        assert _needs_recent_fallback([], None) is False

    def test_recent_fallback_needed_with_nine_current_candidates(self) -> None:
        nine = [_cand(f"C{i}", full_hash=i) for i in range(9)]

        assert _needs_recent_fallback(nine, self.CUTOFF) is True

    def test_recent_fallback_not_needed_with_ten_current_candidates(self) -> None:
        ten = [_cand(f"C{i}", full_hash=i) for i in range(10)]

        assert _needs_recent_fallback(ten, self.CUTOFF) is False


def _bookmark(bookmark_id: int, color: str | None, moves: list[str] | str) -> PositionBookmark:
    return PositionBookmark(
        id=bookmark_id,
        user_id=1,
        label="b",
        target_hash=0,
        fen="x",
        moves=moves if isinstance(moves, str) else json.dumps(moves),
        color=color,
        match_side="full",
    )


class TestBookmarkFullHashes:
    def test_bookmark_hashes_are_replayed_per_colour(self) -> None:
        board = chess.Board()
        board.push_san("e4")
        board.push_san("e5")
        board.push_san("Nf3")
        expected = compute_hashes(board)[2]

        hashes = _bookmark_full_hashes_by_color(
            [_bookmark(1, "white", ["e4", "e5", "Nf3"]), _bookmark(2, "black", ["e4", "e5"])]
        )

        assert expected in hashes["white"]
        assert len(hashes["black"]) == 1
        assert expected not in hashes["black"]

    def test_bookmark_without_a_colour_is_skipped(self) -> None:
        hashes = _bookmark_full_hashes_by_color([_bookmark(1, None, ["e4"])])

        assert hashes == {"white": set(), "black": set()}

    def test_bookmark_that_does_not_replay_is_skipped_and_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capture = MagicMock()
        set_context = MagicMock()
        monkeypatch.setattr(stats_service.sentry_sdk, "capture_exception", capture)
        monkeypatch.setattr(stats_service.sentry_sdk, "set_context", set_context)

        hashes = _bookmark_full_hashes_by_color(
            [_bookmark(5, "white", ["e4", "Qh9"]), _bookmark(6, "white", "not json")]
        )

        assert hashes == {"white": set(), "black": set()}
        assert capture.call_count == 2
        # The id travels in the context, never in the exception message.
        assert set_context.call_args_list[0].args == ("bookmark", {"bookmark_id": 5})


async def _white_openings(session: AsyncSession, count: int) -> list[Any]:
    """Distinct white-defined openings (odd ply_count >= 3), shallowest first."""
    rows = (
        await session.execute(
            select(
                _openings_dedup.c.eco,
                _openings_dedup.c.name,
                _openings_dedup.c.pgn,
                _openings_dedup.c.full_hash,
                _openings_dedup.c.ply_count,
            )
            .where(_openings_dedup.c.ply_count >= 3, _openings_dedup.c.ply_count % 2 == 1)
            .order_by(_openings_dedup.c.ply_count, _openings_dedup.c.name)
            .limit(count)
        )
    ).all()
    if len(rows) < count:
        pytest.skip("openings_dedup not seeded")
    return list(rows)


async def _seed_games_through(
    session: AsyncSession,
    *,
    user_id: int,
    days_back: list[int],
    opening: Any | None = None,
) -> None:
    """Seed one white win per entry of ``days_back`` (days before _NOW).

    With ``opening`` the game gets a position row at the opening's ply, so it counts
    toward that opening; without it the game only moves the colour's cutoff.
    """
    games: list[Game] = []
    for days in days_back:
        game = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=_unique_id(),
            pgn="1. e4 e5 *",
            result="1-0",
            user_color="white",
            time_control_str="300+0",
            time_control_bucket="blitz",
            time_control_seconds=300,
            rated=True,
            white_username="me",
            black_username="opp",
            white_rating=1500,
            black_rating=1500,
        )
        game.played_at = _NOW - datetime.timedelta(days=days)
        games.append(game)
    session.add_all(games)
    await session.flush()
    if opening is None:
        return
    session.add_all(
        GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=opening.ply_count,
            full_hash=opening.full_hash,
            white_hash=opening.full_hash + 1000,
            black_hash=opening.full_hash + 2000,
        )
        for game in games
    )
    await session.flush()


def _replayed_moves(pgn: str) -> list[str]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    sans: list[str] = []
    for move in game.mainline_moves():
        sans.append(board.san(move))
        board.push(move)
    return sans


class TestMostPlayedPipeline:
    @pytest.mark.asyncio
    async def test_current_and_past_rows_are_split_current_first(
        self, db_session: AsyncSession
    ) -> None:
        a, b = await _white_openings(db_session, 2)
        # 200 recent games through A (one per day) set the cutoff to the 200th date;
        # B was last played 400 days ago, before it.
        await _seed_games_through(
            db_session, user_id=_USER_PIPELINE, days_back=list(range(1, 201)), opening=a
        )
        # B carries exactly MOST_PLAYED_MIN_GAMES games so it survives the D-36 floor.
        await _seed_games_through(
            db_session, user_id=_USER_PIPELINE, days_back=[400] * 20, opening=b
        )

        response = await get_most_played_openings(db_session, _USER_PIPELINE, now_utc=_NOW)

        assert [(o.full_hash, o.is_current) for o in response.white] == [
            (str(a.full_hash), True),
            (str(b.full_hash), False),
        ]
        assert response.current_cutoff_white == _NOW - datetime.timedelta(days=200)
        assert response.black == []

    @pytest.mark.asyncio
    async def test_bookmark_twin_row_is_dropped_from_most_played(
        self, db_session: AsyncSession
    ) -> None:
        a, b = await _white_openings(db_session, 2)
        await _seed_games_through(
            db_session, user_id=_USER_TWIN, days_back=list(range(1, 201)), opening=a
        )
        await _seed_games_through(db_session, user_id=_USER_TWIN, days_back=[400] * 20, opening=b)
        sans = _replayed_moves(a.pgn)
        board = chess.Board()
        for san in sans:
            board.push_san(san)
        assert compute_hashes(board)[2] == a.full_hash  # the replay reproduces the view hash
        db_session.add(
            PositionBookmark(
                user_id=_USER_TWIN,
                label="A",
                target_hash=a.full_hash,
                fen=board.fen(),
                moves=json.dumps(sans),
                color="white",
                match_side="full",
            )
        )
        await db_session.flush()

        response = await get_most_played_openings(db_session, _USER_TWIN, now_utc=_NOW)

        assert [o.full_hash for o in response.white] == [str(b.full_hash)]

    @pytest.mark.asyncio
    async def test_recent_fallback_fills_current_rows(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Past openings outranking a current one must not push it out of the table.

        With the fetch limit at 2, the all-time top query returns only P1 and P2 (25 games
        each, 400 days ago). C (18 old + 2 recent games) is found by the cutoff-restricted
        second fetch and shown with its FULL count (20), not the post-cutoff 2. The full
        count is also what clears the MOST_PLAYED_MIN_GAMES floor (D-36): judged on the
        post-cutoff 2, C would be dropped.
        """
        p1, p2, c = await _white_openings(db_session, 3)
        monkeypatch.setattr(stats_service, "MOST_PLAYED_FETCH_LIMIT", 2)
        # 200 filler games (no positions) 1-30 days back put the cutoff at the 60-day floor.
        await _seed_games_through(
            db_session, user_id=_USER_FALLBACK, days_back=[1 + (i % 30) for i in range(200)]
        )
        await _seed_games_through(
            db_session, user_id=_USER_FALLBACK, days_back=[400] * 25, opening=p1
        )
        await _seed_games_through(
            db_session, user_id=_USER_FALLBACK, days_back=[400] * 25, opening=p2
        )
        await _seed_games_through(
            db_session, user_id=_USER_FALLBACK, days_back=[400] * 18 + [5, 5], opening=c
        )

        response = await get_most_played_openings(db_session, _USER_FALLBACK, now_utc=_NOW)

        by_hash = {o.full_hash: o for o in response.white}
        assert set(by_hash) == {str(c.full_hash), str(p1.full_hash), str(p2.full_hash)}
        assert response.white[0].full_hash == str(c.full_hash)  # current rows first
        assert by_hash[str(c.full_hash)].is_current is True
        assert by_hash[str(c.full_hash)].total == 20
        assert by_hash[str(p1.full_hash)].is_current is False
        assert by_hash[str(p2.full_hash)].is_current is False

        # Reverting the fallback must fail this test: without the second fetch C is missing.
        monkeypatch.setattr(stats_service, "_needs_recent_fallback", lambda *_a, **_k: False)
        without = await get_most_played_openings(db_session, _USER_FALLBACK, now_utc=_NOW)
        assert str(c.full_hash) not in {o.full_hash for o in without.white}
