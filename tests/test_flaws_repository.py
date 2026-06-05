"""Integration tests for app.repositories.flaws_repository.

Uses a real PostgreSQL database through the db_session fixture (rolled-back
transaction per test). Covers:
- fetch_game_positions_ordered: returns [] for unknown game_id
- fetch_game_positions_ordered: returns positions sorted by ply ASC even if inserted out of order
- fetch_game_positions_ordered: user_id ownership guard (different user returns [])
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.flaws_repository import fetch_game_positions_ordered


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [99999, 99998]:
        await ensure_test_user(db_session, uid)


async def _seed_game(session: AsyncSession, *, user_id: int = 99999) -> Game:
    """Insert a Game row and flush to obtain an ID."""
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_position(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Insert a GamePosition row and flush."""
    pos = GamePosition(
        game_id=game.id,
        user_id=game.user_id,
        ply=ply,
        full_hash=hash(f"{game.id}-{ply}"),
        white_hash=hash(f"w-{game.id}-{ply}"),
        black_hash=hash(f"b-{game.id}-{ply}"),
        move_san=move_san,
        clock_seconds=clock_seconds,
        phase=phase,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        piece_count=2,
        material_count=1000,
        material_signature="KP_KP",
        material_imbalance=0,
        endgame_class=None,
    )
    session.add(pos)
    await session.flush()
    return pos


# ---------------------------------------------------------------------------
# TestFetchGamePositionsOrdered
# ---------------------------------------------------------------------------


class TestFetchGamePositionsOrdered:
    """Tests for fetch_game_positions_ordered repository function."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_game(self, db_session: AsyncSession) -> None:
        """An unknown game_id returns an empty list."""
        rows = await fetch_game_positions_ordered(
            db_session,
            game_id=999999999,
            user_id=99999,
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_positions_sorted_by_ply_asc(self, db_session: AsyncSession) -> None:
        """Positions are returned sorted by ply ASC even when inserted out of order."""
        game = await _seed_game(db_session)

        # Insert out of order: ply 2, 0, 1
        await _seed_position(db_session, game=game, ply=2, eval_cp=50)
        await _seed_position(db_session, game=game, ply=0, eval_cp=0)
        await _seed_position(db_session, game=game, ply=1, eval_cp=30)

        rows = await fetch_game_positions_ordered(db_session, game_id=game.id, user_id=99999)
        assert len(rows) == 3
        plies = [r.ply for r in rows]
        assert plies == [0, 1, 2], f"Expected [0,1,2] ply order, got {plies}"

    @pytest.mark.asyncio
    async def test_ownership_guard_different_user_returns_empty(
        self, db_session: AsyncSession
    ) -> None:
        """A different user_id returns [] even though the game_id exists.

        This is the T-105-03 Information Disclosure mitigation: one user cannot
        read another user's game positions via the repository.
        """
        game = await _seed_game(db_session, user_id=99999)
        await _seed_position(db_session, game=game, ply=0)
        await _seed_position(db_session, game=game, ply=1, eval_cp=50)

        # Attempt to fetch game's positions with a different user_id
        rows = await fetch_game_positions_ordered(
            db_session,
            game_id=game.id,
            user_id=99998,  # different user
        )
        assert rows == [], "A different user_id must not be able to fetch another user's positions"
