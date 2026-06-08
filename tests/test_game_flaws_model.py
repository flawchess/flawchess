"""Integration tests for the GameFlaw ORM model (Phase 108 Plan 01).

Wave 0 model round-trip test for downstream plans. Tests the GameFlaw table
created by the SEED-038 migration: insert/read, composite PK uniqueness,
and CASCADE delete on both game_id and user_id FKs.

Coverage:
- Insert a GameFlaw row and read back with correct typed columns (round-trip).
- Composite PK rejects a duplicate (user_id, game_id, ply) with IntegrityError.
- Deleting the parent game CASCADE-removes its game_flaws rows.
- Deleting the parent user CASCADE-removes that user's game_flaws rows.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_flaw import GameFlaw


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [77001, 77002]:
        await ensure_test_user(db_session, uid)


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 77001,
) -> Game:
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


def _make_flaw_row(game: Game, ply: int = 10) -> GameFlaw:
    """Return an unsaved GameFlaw instance with representative column values."""
    return GameFlaw(
        user_id=game.user_id,
        game_id=game.id,
        ply=ply,
        severity=2,  # blunder
        tempo=0,  # low-clock
        phase=1,  # middlegame
        is_miss=True,
        is_lucky=False,
        is_reversed=True,
        is_squandered=True,
        es_before=0.75,
        es_after=0.45,
        move_san="Qxf7+",
        fen="rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R",
    )


# ---------------------------------------------------------------------------
# TestGameFlawRoundTrip
# ---------------------------------------------------------------------------


class TestGameFlawRoundTrip:
    """Verify that a GameFlaw row persists and reads back with correct values."""

    @pytest.mark.asyncio
    async def test_insert_and_read_back(self, db_session: AsyncSession) -> None:
        """A GameFlaw row inserts and round-trips all typed columns correctly."""
        game = await _seed_game(db_session)
        flaw = _make_flaw_row(game, ply=10)
        db_session.add(flaw)
        await db_session.flush()

        # Re-fetch from the DB (within the same rolled-back transaction).
        result = await db_session.execute(
            select(GameFlaw).where(
                GameFlaw.user_id == game.user_id,
                GameFlaw.game_id == game.id,
                GameFlaw.ply == 10,
            )
        )
        row = result.scalar_one()

        assert row.severity == 2
        assert row.tempo == 0
        assert row.phase == 1
        assert row.is_miss is True
        assert row.is_lucky is False
        assert row.is_reversed is True
        assert row.is_squandered is True
        assert abs(row.es_before - 0.75) < 1e-6
        assert abs(row.es_after - 0.45) < 1e-6
        assert row.move_san == "Qxf7+"
        assert "rnbqkb1r" in row.fen  # board_fen prefix


# ---------------------------------------------------------------------------
# TestGameFlawCompositePK
# ---------------------------------------------------------------------------


class TestGameFlawCompositePK:
    """Composite PK rejects a duplicate (user_id, game_id, ply)."""

    @pytest.mark.asyncio
    async def test_duplicate_pk_raises_integrity_error(self, db_session: AsyncSession) -> None:
        """Inserting two rows with the same (user_id, game_id, ply) raises IntegrityError."""
        game = await _seed_game(db_session)
        flaw1 = _make_flaw_row(game, ply=5)
        flaw2 = _make_flaw_row(game, ply=5)  # same PK

        db_session.add(flaw1)
        await db_session.flush()

        db_session.add(flaw2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


# ---------------------------------------------------------------------------
# TestGameFlawCascadeDelete
# ---------------------------------------------------------------------------


class TestGameFlawCascadeDelete:
    """CASCADE delete propagates from both parent tables."""

    @pytest.mark.asyncio
    async def test_game_delete_cascades_to_game_flaws(self, db_session: AsyncSession) -> None:
        """Deleting the parent game removes its game_flaws rows (FK CASCADE)."""
        game = await _seed_game(db_session)

        for ply in [10, 20, 30]:
            db_session.add(_make_flaw_row(game, ply=ply))
        await db_session.flush()

        # Verify rows exist before deletion.
        before = (
            (await db_session.execute(select(GameFlaw).where(GameFlaw.game_id == game.id)))
            .scalars()
            .all()
        )
        assert len(before) == 3

        # Delete the parent game — CASCADE must remove the flaw rows.
        await db_session.execute(delete(Game).where(Game.id == game.id))
        await db_session.flush()

        after = (
            (await db_session.execute(select(GameFlaw).where(GameFlaw.game_id == game.id)))
            .scalars()
            .all()
        )
        assert len(after) == 0, f"Expected 0 game_flaws after game delete, got {len(after)}"

    @pytest.mark.asyncio
    async def test_user_delete_cascades_to_game_flaws(self, db_session: AsyncSession) -> None:
        """Deleting the parent user removes that user's game_flaws rows (FK CASCADE)."""
        from app.models.user import User

        game = await _seed_game(db_session, user_id=77001)

        for ply in [15, 25]:
            db_session.add(_make_flaw_row(game, ply=ply))
        await db_session.flush()

        # Verify rows exist before user deletion.
        before = (
            (await db_session.execute(select(GameFlaw).where(GameFlaw.user_id == 77001)))
            .scalars()
            .all()
        )
        assert len(before) == 2

        # Delete the user — both user_id FK and game_id FK (via games → game_flaws)
        # must cascade. user → games → game_flaws chain also covered by FK ON CASCADE.
        await db_session.execute(delete(User).where(User.id == 77001))
        await db_session.flush()

        after = (
            (await db_session.execute(select(GameFlaw).where(GameFlaw.user_id == 77001)))
            .scalars()
            .all()
        )
        assert len(after) == 0, f"Expected 0 game_flaws after user delete, got {len(after)}"
