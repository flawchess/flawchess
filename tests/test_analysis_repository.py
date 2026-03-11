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
    opponent_username: str = "opponent",
    platform_url: str | None = "https://chess.com/game/123",
    full_hash: int = 9999,
    white_hash: int = 1111,
    black_hash: int = 2222,
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
        opponent_username=opponent_username,
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
    )
    session.add(position)
    await session.flush()

    return game, position


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
            rated=None,
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
            rated=None,
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
            rated=None,
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
            rated=None,
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
            rated=None,
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
            rated=True,
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
            rated=None,
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
            rated=None,
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
        now = datetime.datetime.now(tz=datetime.timezone.utc)

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
            rated=True,
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
            opponent_username="opp",
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
            rated=None,
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
            rated=None,
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
            rated=None,
            recency_cutoff=None,
            color=None,
            offset=2,
            limit=2,
        )

        assert total == 5
        assert len(games) == 2
