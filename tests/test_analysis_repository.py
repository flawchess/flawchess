"""Integration tests for the analysis repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage:
- ANL-02: match_side routes to correct hash column (white/black/full)
- FLT-01: time_control filter
- FLT-02: rated filter
- FLT-03: recency filter
- FLT-04: color filter
- Combined filters (intersection behavior)
- Transposition deduplication (game counted once even with multi-ply match)
- Pagination (offset, limit, total count)
- MEXP-04: query_next_moves returns per-move W/D/L aggregation
- MEXP-05: transposition dedup (same game at multiple plies counted once per move)
- MEXP-10: query_transposition_counts returns batch {hash: count}
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.analysis_repository import (
    HASH_COLUMN_MAP,
    query_all_results,
    query_matching_games,
)


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user
    for uid in [1, 2]:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------

_COUNTER = 0


def _unique_game_id() -> str:
    """Return a unique platform_game_id for each call."""
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 1,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    rated: bool = True,
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    white_username: str = "testuser",
    black_username: str = "opponent",
    platform_url: str | None = "https://chess.com/game/123",
    full_hash: int = 9999,
    white_hash: int = 1111,
    black_hash: int = 2222,
    move_san: str | None = None,
) -> tuple[Game, GamePosition]:
    """Insert one Game + one GamePosition row and flush to obtain IDs.

    Returns (game, position) so callers can inspect generated IDs or add more
    positions to the same game.
    """
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        platform_url=platform_url,
        pgn="1. e4 e5 *",
        variant="Standard",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        white_username=white_username,
        black_username=black_username,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()  # obtain game.id

    position = GamePosition(
        game_id=game.id,
        user_id=user_id,
        ply=1,
        full_hash=full_hash,
        white_hash=white_hash,
        black_hash=black_hash,
        move_san=move_san,
    )
    session.add(position)
    await session.flush()

    return game, position


async def _add_position(
    session: AsyncSession,
    game_id: int,
    user_id: int,
    ply: int,
    full_hash: int,
    white_hash: int = 0,
    black_hash: int = 0,
    move_san: str | None = None,
) -> GamePosition:
    """Insert an additional GamePosition for an existing game and flush."""
    position = GamePosition(
        game_id=game_id,
        user_id=user_id,
        ply=ply,
        full_hash=full_hash,
        white_hash=white_hash,
        black_hash=black_hash,
        move_san=move_san,
    )
    session.add(position)
    await session.flush()
    return position


# ---------------------------------------------------------------------------
# TestMatchSide — ANL-02
# ---------------------------------------------------------------------------


class TestMatchSide:
    """Verify that match_side routes queries to the correct hash column."""

    @pytest.mark.asyncio
    async def test_match_side_white(self, db_session: AsyncSession) -> None:
        """Query on white_hash column returns the matching game."""
        await _seed_game(db_session, white_hash=1234, black_hash=0, full_hash=0)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["white"],
            target_hash=1234,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1

    @pytest.mark.asyncio
    async def test_match_side_black(self, db_session: AsyncSession) -> None:
        """Query on black_hash column returns the matching game."""
        await _seed_game(db_session, white_hash=0, black_hash=5678, full_hash=0)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["black"],
            target_hash=5678,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1

    @pytest.mark.asyncio
    async def test_match_side_full(self, db_session: AsyncSession) -> None:
        """Query on full_hash column returns the matching game."""
        await _seed_game(db_session, white_hash=0, black_hash=0, full_hash=9876)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=9876,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1

    @pytest.mark.asyncio
    async def test_match_side_no_match(self, db_session: AsyncSession) -> None:
        """Querying a hash that does not exist returns 0 results."""
        await _seed_game(db_session, full_hash=1111)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=9999999,  # hash that was never inserted
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 0
        assert len(games) == 0


# ---------------------------------------------------------------------------
# TestFilters — FLT-01 through FLT-04
# ---------------------------------------------------------------------------

TARGET_HASH = 42424242  # shared hash value for filter tests


class TestFilters:
    """Verify each filter narrows results correctly."""

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        """FLT-01: Only games matching the requested time_control bucket returned."""
        await _seed_game(db_session, time_control_bucket="bullet", full_hash=TARGET_HASH)
        await _seed_game(db_session, time_control_bucket="blitz", full_hash=TARGET_HASH)
        await _seed_game(db_session, time_control_bucket="rapid", full_hash=TARGET_HASH)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TARGET_HASH,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1
        assert games[0].time_control_bucket == "blitz"

    @pytest.mark.asyncio
    async def test_rated_filter(self, db_session: AsyncSession) -> None:
        """FLT-02: Only rated (or unrated) games returned when filter applied."""
        await _seed_game(db_session, rated=True, full_hash=TARGET_HASH)
        await _seed_game(db_session, rated=False, full_hash=TARGET_HASH)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TARGET_HASH,
            time_control=None,
            platform=None,
            rated=True,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1
        assert games[0].rated is True

    @pytest.mark.asyncio
    async def test_recency_filter(self, db_session: AsyncSession) -> None:
        """FLT-03: Games played before the cutoff are excluded."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        two_years_ago = now - datetime.timedelta(days=730)
        cutoff = now - datetime.timedelta(days=30)

        await _seed_game(db_session, played_at=now, full_hash=TARGET_HASH)
        await _seed_game(db_session, played_at=two_years_ago, full_hash=TARGET_HASH)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TARGET_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=cutoff,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1

    @pytest.mark.asyncio
    async def test_color_filter(self, db_session: AsyncSession) -> None:
        """FLT-04: Only games where user played the requested color returned."""
        await _seed_game(db_session, user_color="white", full_hash=TARGET_HASH)
        await _seed_game(db_session, user_color="black", full_hash=TARGET_HASH)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TARGET_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color="white",
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1
        assert games[0].user_color == "white"

    @pytest.mark.asyncio
    async def test_combined_filters(self, db_session: AsyncSession) -> None:
        """Multiple filters applied simultaneously narrow to the intersection."""
        # Matches all three filters
        await _seed_game(
            db_session,
            time_control_bucket="blitz",
            rated=True,
            user_color="white",
            full_hash=TARGET_HASH,
        )
        # Misses time_control
        await _seed_game(
            db_session,
            time_control_bucket="bullet",
            rated=True,
            user_color="white",
            full_hash=TARGET_HASH,
        )
        # Misses rated
        await _seed_game(
            db_session,
            time_control_bucket="blitz",
            rated=False,
            user_color="white",
            full_hash=TARGET_HASH,
        )
        # Misses color
        await _seed_game(
            db_session,
            time_control_bucket="blitz",
            rated=True,
            user_color="black",
            full_hash=TARGET_HASH,
        )

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TARGET_HASH,
            time_control=["blitz"],
            platform=None,
            rated=True,
            opponent_type="both",
            recency_cutoff=None,
            color="white",
            offset=0,
            limit=50,
        )

        assert total == 1
        assert len(games) == 1


# ---------------------------------------------------------------------------
# TestDeduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Verify that transpositions are counted once per game."""

    @pytest.mark.asyncio
    async def test_transposition_counts_once(self, db_session: AsyncSession) -> None:
        """A game whose target hash appears at two different plies is counted once."""
        DEDUP_HASH = 77777777

        game = Game(
            user_id=1,
            platform="chess.com",
            platform_game_id=_unique_game_id(),
            platform_url=None,
            pgn="1. e4 e5 2. Nf3 *",
            variant="Standard",
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            rated=True,
            white_username="testuser",
            black_username="opp",
        )
        game.played_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db_session.add(game)
        await db_session.flush()

        # Two positions at different plies with the SAME hash
        for ply in (2, 4):
            pos = GamePosition(
                game_id=game.id,
                user_id=1,
                ply=ply,
                full_hash=DEDUP_HASH,
                white_hash=0,
                black_hash=0,
            )
            db_session.add(pos)
        await db_session.flush()

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=DEDUP_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=0,
            limit=50,
        )

        assert total == 1, "Game with transposition should be counted once"
        assert len(games) == 1

        # Also verify query_all_results de-duplicates
        rows = await query_all_results(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=DEDUP_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# TestPagination
# ---------------------------------------------------------------------------

PAGINATION_HASH = 55555555


class TestPagination:
    """Verify offset/limit pagination and total count accuracy."""

    @pytest.mark.asyncio
    async def test_pagination_offset_limit(self, db_session: AsyncSession) -> None:
        """Seed 5 games, request 2 at offset 2 — returns 2 with total=5."""
        for _ in range(5):
            await _seed_game(db_session, full_hash=PAGINATION_HASH)

        games, total = await query_matching_games(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=PAGINATION_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
            offset=2,
            limit=2,
        )

        assert total == 5
        assert len(games) == 2


# ---------------------------------------------------------------------------
# TestTimeSeries — BKM-03, BKM-04
# ---------------------------------------------------------------------------

TS_HASH = 12345  # fixed Zobrist hash for all time-series tests


class TestTimeSeries:
    """Verify query_time_series returns correct monthly (month_dt, result, user_color) tuples."""

    @pytest.mark.asyncio
    async def test_returns_monthly_buckets(self, db_session: AsyncSession) -> None:
        """BKM-03: 3 games in Jan 2025 (2W 1L) and 2 games in Mar 2025 (1W 1D) → 2 rows."""
        from app.repositories.analysis_repository import query_time_series

        jan = datetime.datetime(2025, 1, 15, tzinfo=datetime.timezone.utc)
        mar = datetime.datetime(2025, 3, 10, tzinfo=datetime.timezone.utc)

        # Jan: 2 wins, 1 loss
        await _seed_game(db_session, played_at=jan, result="1-0", user_color="white", full_hash=TS_HASH)
        await _seed_game(db_session, played_at=jan, result="1-0", user_color="white", full_hash=TS_HASH)
        await _seed_game(db_session, played_at=jan, result="0-1", user_color="white", full_hash=TS_HASH)
        # Mar: 1 win, 1 draw
        await _seed_game(db_session, played_at=mar, result="1-0", user_color="white", full_hash=TS_HASH)
        await _seed_game(db_session, played_at=mar, result="1/2-1/2", user_color="white", full_hash=TS_HASH)

        rows = await query_time_series(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TS_HASH,
            color=None,
        )

        # Group by month
        from collections import defaultdict
        by_month: dict[str, list] = defaultdict(list)
        for month_dt, result, user_color in rows:
            key = month_dt.strftime("%Y-%m")
            by_month[key].append((result, user_color))

        assert set(by_month.keys()) == {"2025-01", "2025-03"}
        assert len(by_month["2025-01"]) == 3
        assert len(by_month["2025-03"]) == 2

        # Verify win_rate for Jan: 2/3 ≈ 0.667
        jan_wins = sum(1 for r, c in by_month["2025-01"] if r == "1-0" and c == "white")
        assert jan_wins == 2

    @pytest.mark.asyncio
    async def test_gap_months(self, db_session: AsyncSession) -> None:
        """BKM-04: Feb 2025 has no games — it must NOT appear in results."""
        from app.repositories.analysis_repository import query_time_series

        jan = datetime.datetime(2025, 1, 20, tzinfo=datetime.timezone.utc)
        mar = datetime.datetime(2025, 3, 5, tzinfo=datetime.timezone.utc)

        await _seed_game(db_session, played_at=jan, full_hash=TS_HASH)
        await _seed_game(db_session, played_at=mar, full_hash=TS_HASH)

        rows = await query_time_series(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TS_HASH,
            color=None,
        )

        months = {row[0].strftime("%Y-%m") for row in rows}
        assert "2025-02" not in months, "Feb gap month must not appear in results"

    @pytest.mark.asyncio
    async def test_user_isolation(self, db_session: AsyncSession) -> None:
        """Games belonging to user B do not appear in user A's time series."""
        from app.repositories.analysis_repository import query_time_series

        played = datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc)

        # User A game
        await _seed_game(db_session, user_id=1, played_at=played, full_hash=TS_HASH)
        # User B game (different user_id)
        await _seed_game(db_session, user_id=2, played_at=played, full_hash=TS_HASH)

        rows = await query_time_series(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TS_HASH,
            color=None,
        )

        assert len(rows) == 1, "Only user A's game should be returned"

    @pytest.mark.asyncio
    async def test_color_filter(self, db_session: AsyncSession) -> None:
        """When color='white', only games where user_color='white' are counted."""
        from app.repositories.analysis_repository import query_time_series

        played = datetime.datetime(2025, 7, 1, tzinfo=datetime.timezone.utc)

        await _seed_game(db_session, played_at=played, user_color="white", full_hash=TS_HASH)
        await _seed_game(db_session, played_at=played, user_color="black", full_hash=TS_HASH)

        rows = await query_time_series(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["full"],
            target_hash=TS_HASH,
            color="white",
        )

        assert len(rows) == 1
        _, _, user_color = rows[0]
        assert user_color == "white"

    @pytest.mark.asyncio
    async def test_match_side_white(self, db_session: AsyncSession) -> None:
        """hash_column=GamePosition.white_hash: only games with matching white_hash returned."""
        from app.repositories.analysis_repository import query_time_series

        played = datetime.datetime(2025, 8, 15, tzinfo=datetime.timezone.utc)

        # Game with matching white_hash
        await _seed_game(db_session, played_at=played, white_hash=TS_HASH, full_hash=0, black_hash=0)
        # Game without matching white_hash
        await _seed_game(db_session, played_at=played, white_hash=99999, full_hash=0, black_hash=0)

        rows = await query_time_series(
            db_session,
            user_id=1,
            hash_column=HASH_COLUMN_MAP["white"],
            target_hash=TS_HASH,
            color=None,
        )

        assert len(rows) == 1


# ---------------------------------------------------------------------------
# TestNextMoves — MEXP-04
# ---------------------------------------------------------------------------

NM_SOURCE_HASH = 100  # queried source position hash
NM_E4_HASH = 200      # result hash after e4
NM_D4_HASH = 300      # result hash after d4


class TestNextMoves:
    """MEXP-04: query_next_moves returns per-move W/D/L aggregation."""

    @pytest.mark.asyncio
    async def test_basic_next_moves(self, db_session: AsyncSession) -> None:
        """3 games at same position: 2 play e4 (1W 1D), 1 plays d4 (1L).

        Expected:
        - e4: game_count=2, wins=1, draws=1, losses=0, result_hash=NM_E4_HASH
        - d4: game_count=1, wins=0, draws=0, losses=1, result_hash=NM_D4_HASH
        """
        from app.repositories.analysis_repository import query_next_moves

        # Game 1: e4 → win
        game1, _ = await _seed_game(
            db_session,
            result="1-0",
            user_color="white",
            full_hash=NM_SOURCE_HASH,
            move_san="e4",
        )
        await _add_position(
            db_session, game1.id, 1, ply=2, full_hash=NM_E4_HASH
        )

        # Game 2: e4 → draw
        game2, _ = await _seed_game(
            db_session,
            result="1/2-1/2",
            user_color="white",
            full_hash=NM_SOURCE_HASH,
            move_san="e4",
        )
        await _add_position(
            db_session, game2.id, 1, ply=2, full_hash=NM_E4_HASH
        )

        # Game 3: d4 → loss
        game3, _ = await _seed_game(
            db_session,
            result="0-1",
            user_color="white",
            full_hash=NM_SOURCE_HASH,
            move_san="d4",
        )
        await _add_position(
            db_session, game3.id, 1, ply=2, full_hash=NM_D4_HASH
        )

        rows = await query_next_moves(
            db_session,
            user_id=1,
            target_hash=NM_SOURCE_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        # Build lookup by move_san
        by_move = {row.move_san: row for row in rows}

        assert len(by_move) == 2, f"Expected 2 moves, got {len(by_move)}: {list(by_move.keys())}"

        e4 = by_move["e4"]
        assert e4.game_count == 2
        assert e4.wins == 1
        assert e4.draws == 1
        assert e4.losses == 0
        assert e4.result_hash == NM_E4_HASH

        d4 = by_move["d4"]
        assert d4.game_count == 1
        assert d4.wins == 0
        assert d4.draws == 0
        assert d4.losses == 1
        assert d4.result_hash == NM_D4_HASH


# ---------------------------------------------------------------------------
# TestNextMovesTranspositions — MEXP-05
# ---------------------------------------------------------------------------

NM_TRANS_SOURCE_HASH = 400
NM_TRANS_RESULT_HASH = 401


class TestNextMovesTranspositions:
    """MEXP-05: game with same move_san at multiple plies counted once per move."""

    @pytest.mark.asyncio
    async def test_transposition_counted_once(self, db_session: AsyncSession) -> None:
        """1 game visits source_hash at ply 2 and ply 6, plays 'Nf3' both times.

        query_next_moves must return game_count=1 for 'Nf3', not 2.
        """
        from app.repositories.analysis_repository import query_next_moves

        game = Game(
            user_id=1,
            platform="chess.com",
            platform_game_id=_unique_game_id(),
            platform_url=None,
            pgn="1. Nf3 Nf6 2. Nf3 Nf6 *",
            variant="Standard",
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            rated=True,
            white_username="testuser",
            black_username="opp",
        )
        game.played_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db_session.add(game)
        await db_session.flush()

        # Same source position at ply 2 and ply 6
        await _add_position(db_session, game.id, 1, ply=2, full_hash=NM_TRANS_SOURCE_HASH, move_san="Nf3")
        await _add_position(db_session, game.id, 1, ply=3, full_hash=NM_TRANS_RESULT_HASH)  # result at ply 3
        await _add_position(db_session, game.id, 1, ply=6, full_hash=NM_TRANS_SOURCE_HASH, move_san="Nf3")
        await _add_position(db_session, game.id, 1, ply=7, full_hash=NM_TRANS_RESULT_HASH)  # result at ply 7

        rows = await query_next_moves(
            db_session,
            user_id=1,
            target_hash=NM_TRANS_SOURCE_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        assert len(rows) == 1
        assert rows[0].move_san == "Nf3"
        assert rows[0].game_count == 1, f"Expected game_count=1, got {rows[0].game_count}"


# ---------------------------------------------------------------------------
# TestNextMovesFilters — MEXP-04 filter application
# ---------------------------------------------------------------------------

NM_FILTER_HASH = 500
NM_FILTER_RESULT_HASH = 501


class TestNextMovesFilters:
    """Filter application narrows next-moves results correctly."""

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        """2 games at same position (blitz vs rapid), filter blitz → only blitz counted."""
        from app.repositories.analysis_repository import query_next_moves

        # Blitz game plays e4
        game_blitz, _ = await _seed_game(
            db_session,
            time_control_bucket="blitz",
            full_hash=NM_FILTER_HASH,
            move_san="e4",
        )
        await _add_position(db_session, game_blitz.id, 1, ply=2, full_hash=NM_FILTER_RESULT_HASH)

        # Rapid game plays e4
        game_rapid, _ = await _seed_game(
            db_session,
            time_control_bucket="rapid",
            full_hash=NM_FILTER_HASH,
            move_san="e4",
        )
        await _add_position(db_session, game_rapid.id, 1, ply=2, full_hash=NM_FILTER_RESULT_HASH)

        rows = await query_next_moves(
            db_session,
            user_id=1,
            target_hash=NM_FILTER_HASH,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        assert len(rows) == 1
        assert rows[0].game_count == 1

    @pytest.mark.asyncio
    async def test_rated_filter(self, db_session: AsyncSession) -> None:
        """2 games at same position (rated vs unrated), filter rated=True → only rated counted."""
        from app.repositories.analysis_repository import query_next_moves

        # Rated game
        game_rated, _ = await _seed_game(
            db_session,
            rated=True,
            full_hash=NM_FILTER_HASH,
            move_san="d4",
        )
        await _add_position(db_session, game_rated.id, 1, ply=2, full_hash=NM_FILTER_RESULT_HASH + 1)

        # Unrated game plays same move
        game_unrated, _ = await _seed_game(
            db_session,
            rated=False,
            full_hash=NM_FILTER_HASH,
            move_san="d4",
        )
        await _add_position(db_session, game_unrated.id, 1, ply=2, full_hash=NM_FILTER_RESULT_HASH + 1)

        rows = await query_next_moves(
            db_session,
            user_id=1,
            target_hash=NM_FILTER_HASH,
            time_control=None,
            platform=None,
            rated=True,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        # Only the rated game should be counted for d4
        by_move = {row.move_san: row for row in rows}
        assert "d4" in by_move
        assert by_move["d4"].game_count == 1


# ---------------------------------------------------------------------------
# TestTranspositionCounts — MEXP-10
# ---------------------------------------------------------------------------

TC_RESULT_HASH = 600


class TestTranspositionCounts:
    """MEXP-10: query_transposition_counts returns batch {result_hash: count}."""

    @pytest.mark.asyncio
    async def test_batch_transposition_count(self, db_session: AsyncSession) -> None:
        """2 games both reach result_hash=600 (via different source positions).

        query_transposition_counts([600]) must return {600: 2}.
        """
        from app.repositories.analysis_repository import query_transposition_counts

        # Game A: plays e4 from source_hash=100 → result_hash=600
        game_a, _ = await _seed_game(
            db_session, full_hash=100, move_san="e4"
        )
        await _add_position(db_session, game_a.id, 1, ply=2, full_hash=TC_RESULT_HASH)

        # Game B: plays c4 from source_hash=150 → result_hash=600 (transposition)
        game_b = Game(
            user_id=1,
            platform="chess.com",
            platform_game_id=_unique_game_id(),
            platform_url=None,
            pgn="1. c4 e5 *",
            variant="Standard",
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            rated=True,
            white_username="testuser",
            black_username="opp",
        )
        game_b.played_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db_session.add(game_b)
        await db_session.flush()

        await _add_position(db_session, game_b.id, 1, ply=1, full_hash=150, move_san="c4")
        await _add_position(db_session, game_b.id, 1, ply=2, full_hash=TC_RESULT_HASH)

        counts = await query_transposition_counts(
            db_session,
            user_id=1,
            result_hash_list=[TC_RESULT_HASH],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        assert TC_RESULT_HASH in counts
        assert counts[TC_RESULT_HASH] == 2, f"Expected 2, got {counts[TC_RESULT_HASH]}"

    @pytest.mark.asyncio
    async def test_empty_hash_list(self, db_session: AsyncSession) -> None:
        """Empty result_hash_list returns empty dict."""
        from app.repositories.analysis_repository import query_transposition_counts

        counts = await query_transposition_counts(
            db_session,
            user_id=1,
            result_hash_list=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        assert counts == {}


# ---------------------------------------------------------------------------
# TestNextMovesNullMoveExcluded — NULL move_san excluded
# ---------------------------------------------------------------------------

NM_NULL_HASH = 700


class TestNextMovesNullMoveExcluded:
    """NULL move_san rows (final position) must not appear in next-moves results."""

    @pytest.mark.asyncio
    async def test_null_move_san_excluded(self, db_session: AsyncSession) -> None:
        """Seed a game where position at NM_NULL_HASH has move_san=None.

        query_next_moves must return no rows for this source hash.
        """
        from app.repositories.analysis_repository import query_next_moves

        # Game with only a NULL move_san position (final position)
        game, _ = await _seed_game(
            db_session,
            full_hash=NM_NULL_HASH,
            move_san=None,  # explicitly NULL — final position
        )

        rows = await query_next_moves(
            db_session,
            user_id=1,
            target_hash=NM_NULL_HASH,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            color=None,
        )

        assert rows == [], f"Expected no rows, got: {rows}"
