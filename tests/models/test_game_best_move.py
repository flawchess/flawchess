"""DB round-trip + constraint tests for the game_best_moves table (Phase 174-03).

Proves the three must-have truths of the GameBestMove candidate table:
1. A row inserts and reads back with maia_prob / best_cp / second_cp intact
   (continuous storage only — no lossy conversion at write time, D-05).
2. A duplicate (game_id, ply) insert is rejected by the composite primary key.
3. Deleting the parent game cascades — the game_best_moves row is gone.

Uses the per-run DB clone via the rolled-back db_session fixture (the migrated
template auto-includes game_best_moves because the migration is on head). No dev
DB reset (CLAUDE.md "No dev DB reset in plans").
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_best_move import GameBestMove

# Sentinel eval values that must survive the DB round-trip unchanged.
_MAIA_PROB = 0.8125  # exactly representable in REAL, so equality is safe
_BEST_CP = 145
_SECOND_CP = 30
_PLY = 24


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    """Ensure the FK-referenced test user exists (games.user_id -> users.id)."""
    from tests.conftest import ensure_test_user

    await ensure_test_user(db_session, 91740)


async def _seed_game(session: AsyncSession, *, user_id: int = 91740) -> Game:
    """Insert a parent Game and flush to obtain its id."""
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


@pytest.mark.asyncio
async def test_round_trip_preserves_continuous_values(db_session: AsyncSession) -> None:
    """A candidate row reads back with maia_prob / best_cp / second_cp intact."""
    game = await _seed_game(db_session)
    game_id = game.id  # capture before expire_all() to avoid a sync lazy-load
    db_session.add(
        GameBestMove(
            game_id=game_id,
            ply=_PLY,
            maia_prob=_MAIA_PROB,
            best_cp=_BEST_CP,
            best_mate=None,
            second_cp=_SECOND_CP,
            second_mate=None,
        )
    )
    await db_session.flush()
    db_session.expire_all()

    row = (
        await db_session.execute(
            select(GameBestMove).where(GameBestMove.game_id == game_id, GameBestMove.ply == _PLY)
        )
    ).scalar_one()

    assert row.maia_prob == pytest.approx(_MAIA_PROB)
    assert row.best_cp == _BEST_CP
    assert row.second_cp == _SECOND_CP
    assert row.best_mate is None
    assert row.second_mate is None


@pytest.mark.asyncio
async def test_duplicate_game_ply_rejected(db_session: AsyncSession) -> None:
    """A second row with the same (game_id, ply) violates the composite PK."""
    game = await _seed_game(db_session)
    db_session.add(GameBestMove(game_id=game.id, ply=_PLY, maia_prob=_MAIA_PROB))
    await db_session.flush()

    db_session.add(GameBestMove(game_id=game.id, ply=_PLY, maia_prob=0.5))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_parent_delete_cascades(db_session: AsyncSession) -> None:
    """Deleting the parent game removes its game_best_moves rows (ondelete=CASCADE)."""
    game = await _seed_game(db_session)
    game_id = game.id  # capture before expire_all() to avoid a sync lazy-load
    db_session.add(GameBestMove(game_id=game_id, ply=_PLY, maia_prob=_MAIA_PROB))
    await db_session.flush()

    await db_session.execute(delete(Game).where(Game.id == game_id))
    await db_session.flush()
    db_session.expire_all()

    remaining = (
        (await db_session.execute(select(GameBestMove).where(GameBestMove.game_id == game_id)))
        .scalars()
        .all()
    )
    assert remaining == []
