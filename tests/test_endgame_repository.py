"""Integration tests for the endgame repository.

All tests use a real PostgreSQL database through the db_session fixture,
which wraps each test in a rolled-back transaction for isolation.

Coverage:
- query_endgame_entry_rows: returns empty list for user with no endgame positions
- query_endgame_entry_rows: returns one row per game (MIN ply deduplication)
- query_endgame_entry_rows: time_control filter returns only matching games
- query_endgame_entry_rows: platform filter returns only matching games
- query_endgame_games: returns paginated GameRecord-shaped rows for a given endgame class
- query_endgame_games: returns empty list for unknown endgame class
"""

import datetime
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition

# Tests will fail with ImportError until Task 2 creates the repository module (RED phase — expected).
from app.repositories.endgame_repository import (
    ENDGAME_MATERIAL_THRESHOLD,
    query_endgame_entry_rows,
    query_endgame_games,
)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_game_id() -> str:
    """Return a unique platform_game_id for each call."""
    return str(uuid.uuid4())


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [2, 99999]:
        await ensure_test_user(db_session, uid)


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 99999,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    time_control_bucket: str | None = "blitz",
    played_at: datetime.datetime | None = None,
    rated: bool = True,
    is_computer_game: bool = False,
) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_game_id(),
        platform_url=f"https://{platform}/game/123",
        pgn="1. e4 e5 *",
        variant="Standard",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        is_computer_game=is_computer_game,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()
    return game


async def _seed_game_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    material_count: int,
    material_signature: str = "KR_KR",
    material_imbalance: int = 0,
) -> GamePosition:
    """Insert a GamePosition row with endgame-relevant metadata."""
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),  # deterministic unique hash
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=None,
        material_count=material_count,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
    )
    session.add(pos)
    await session.flush()
    return pos


# ---------------------------------------------------------------------------
# TestQueryEndgameEntryRows
# ---------------------------------------------------------------------------


class TestQueryEndgameEntryRows:
    """Tests for query_endgame_entry_rows repository function."""

    @pytest.mark.asyncio
    async def test_no_games_returns_empty(self, db_session: AsyncSession) -> None:
        """User with no games returns empty list."""
        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_no_endgame_positions_returns_empty(self, db_session: AsyncSession) -> None:
        """Game with no positions below the endgame threshold returns empty."""
        game = await _seed_game(db_session)
        # Position with material_count above threshold — not an endgame position
        await _seed_game_position(
            db_session,
            game=game,
            ply=10,
            material_count=ENDGAME_MATERIAL_THRESHOLD + 100,
            material_signature="KQRB_KQRB",
        )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_returns_one_row_per_game_min_ply(self, db_session: AsyncSession) -> None:
        """When a game has multiple endgame positions, only the first (MIN ply) is returned."""
        game = await _seed_game(db_session)
        # Two positions below the endgame threshold at different plies
        await _seed_game_position(
            db_session, game=game, ply=30, material_count=2400, material_signature="KR_KR"
        )
        await _seed_game_position(
            db_session, game=game, ply=40, material_count=2200, material_signature="KR_K"
        )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        # Should return exactly one row for this game
        assert len(rows) == 1
        game_id, result, user_color, material_signature, user_material_imbalance = rows[0]
        assert game_id == game.id
        # Material signature should be from ply=30 (the first endgame position)
        assert material_signature == "KR_KR"

    @pytest.mark.asyncio
    async def test_time_control_filter(self, db_session: AsyncSession) -> None:
        """time_control filter returns only games with matching time_control_bucket."""
        blitz_game = await _seed_game(db_session, time_control_bucket="blitz")
        rapid_game = await _seed_game(db_session, time_control_bucket="rapid")

        for game in [blitz_game, rapid_game]:
            await _seed_game_position(
                db_session, game=game, ply=30, material_count=2400, material_signature="KR_KR"
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=["blitz"],
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert blitz_game.id in game_ids
        assert rapid_game.id not in game_ids

    @pytest.mark.asyncio
    async def test_platform_filter(self, db_session: AsyncSession) -> None:
        """platform filter returns only games from the specified platform."""
        chesscom_game = await _seed_game(db_session, platform="chess.com")
        lichess_game = await _seed_game(db_session, platform="lichess")

        for game in [chesscom_game, lichess_game]:
            await _seed_game_position(
                db_session, game=game, ply=30, material_count=2400, material_signature="KR_KR"
            )

        rows = await query_endgame_entry_rows(
            db_session,
            user_id=99999,
            time_control=None,
            platform=["lichess"],
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
        )
        assert len(rows) == 1
        game_ids = [r[0] for r in rows]
        assert lichess_game.id in game_ids
        assert chesscom_game.id not in game_ids


# ---------------------------------------------------------------------------
# TestQueryEndgameGames
# ---------------------------------------------------------------------------


class TestQueryEndgameGames:
    """Tests for query_endgame_games repository function."""

    @pytest.mark.asyncio
    async def test_returns_games_for_rook_endgame(self, db_session: AsyncSession) -> None:
        """query_endgame_games returns GameRecord-shaped rows for rook endgame class."""
        game = await _seed_game(db_session)
        await _seed_game_position(
            db_session, game=game, ply=30, material_count=2400, material_signature="KR_KR"
        )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="rook",
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 1
        assert len(games) == 1
        # Verify it returns game objects with expected attributes
        returned_game = games[0]
        assert returned_game.id == game.id

    @pytest.mark.asyncio
    async def test_unknown_endgame_class_returns_empty(self, db_session: AsyncSession) -> None:
        """Unknown endgame class (not rook/minor_piece/pawn/queen/mixed/pawnless) returns empty."""
        game = await _seed_game(db_session)
        await _seed_game_position(
            db_session, game=game, ply=30, material_count=2400, material_signature="KR_KR"
        )

        games, matched_count = await query_endgame_games(
            db_session,
            user_id=99999,
            endgame_class="nonexistent_class",
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="both",
            recency_cutoff=None,
            offset=0,
            limit=20,
        )
        assert matched_count == 0
        assert games == []
