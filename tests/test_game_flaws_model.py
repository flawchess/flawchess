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
from sqlalchemy import inspect as sa_inspect, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

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
    """Return an unsaved GameFlaw instance with representative column values.

    Phase 112 (D-07): es_before, es_after, move_san removed from game_flaws.
    Only fen is kept as denormalized display data (game_positions has no FEN column).
    """
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
        assert "rnbqkb1r" in row.fen  # board_fen prefix
        # Phase 112 (D-07): es_before, es_after, move_san dropped — sourced via join
        assert not hasattr(row, "es_before"), "GameFlaw must not have es_before after Phase 112"
        assert not hasattr(row, "es_after"), "GameFlaw must not have es_after after Phase 112"
        assert not hasattr(row, "move_san"), "GameFlaw must not have move_san after Phase 112"


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


# ---------------------------------------------------------------------------
# TestDeferredBlobLeak (Phase 141 — D-02c regression)
# ---------------------------------------------------------------------------


class TestDeferredBlobLeak:
    """Regression guard: allowed_pv_lines / missed_pv_lines must not load on stats scans.

    D-02 structural guard: both columns are declared `deferred=True` on GameFlaw.
    This class verifies two properties:

    1. Unloaded-attribute proof: a representative stats-style `select(GameFlaw)` does
       NOT load the blob columns.  The inspection API is used because an implicit async
       deferred access would raise MissingGreenlet (the fail-loud signal for a real leak).

    2. undefer() round-trip proof: the Phase 143 opt-in path loads the blobs without
       error when `undefer()` is requested explicitly.

    3. Compiled-SQL check (no session): the default `select(GameFlaw)` SQL statement
       does not contain the blob column names — mirrors the established pattern in
       tests/test_query_utils.py.
    """

    def test_deferred_columns_absent_from_default_select_sql(self) -> None:
        """Compiled default select(GameFlaw) must omit the deferred blob column names."""
        # No session needed — pure statement compilation.  The deferred mapper
        # configuration means SQLAlchemy excludes these columns from the default
        # column list emitted in the SELECT clause.
        sql = str(select(GameFlaw).compile(compile_kwargs={"literal_binds": True}))
        assert "allowed_pv_lines" not in sql, (
            "allowed_pv_lines must not appear in default select(GameFlaw) SQL — "
            "deferred=True guard broken"
        )
        assert "missed_pv_lines" not in sql, (
            "missed_pv_lines must not appear in default select(GameFlaw) SQL — "
            "deferred=True guard broken"
        )

    @pytest.mark.asyncio
    async def test_blob_attrs_unloaded_after_stats_select(self, db_session: AsyncSession) -> None:
        """A stats-style select(GameFlaw) must leave both blob attrs in the unloaded set."""
        game = await _seed_game(db_session)
        db_session.add(_make_flaw_row(game, ply=10))
        await db_session.flush()

        # Representative stats-style select: no options(), no undefer() — mirrors every
        # existing select(GameFlaw) site in library_repository.py.
        flaw = (
            await db_session.execute(
                select(GameFlaw).where(
                    GameFlaw.user_id == game.user_id,
                    GameFlaw.game_id == game.id,
                    GameFlaw.ply == 10,
                )
            )
        ).scalar_one()

        # Use the SQLAlchemy inspection API — do NOT touch the attributes directly.
        # An implicit async deferred access raises MissingGreenlet (the fail-loud signal).
        unloaded = sa_inspect(flaw).unloaded
        assert "allowed_pv_lines" in unloaded, (
            "allowed_pv_lines must be in unloaded after a stats select — "
            "deferred=True guard broken (D-02)"
        )
        assert "missed_pv_lines" in unloaded, (
            "missed_pv_lines must be in unloaded after a stats select — "
            "deferred=True guard broken (D-02)"
        )

    @pytest.mark.asyncio
    async def test_undefer_round_trip_loads_both_blob_attrs(self, db_session: AsyncSession) -> None:
        """undefer() opt-in (Phase 143 path) loads both blob attrs without error.

        Both columns are NULL on a freshly seeded row — the assertion is that loading
        succeeds (no MissingGreenlet / attribute error) and returns None (the expected
        default for a row with no PV blobs written yet).
        """
        game = await _seed_game(db_session)
        db_session.add(_make_flaw_row(game, ply=10))
        await db_session.flush()

        flaw = (
            await db_session.execute(
                select(GameFlaw)
                .options(
                    undefer(GameFlaw.allowed_pv_lines),
                    undefer(GameFlaw.missed_pv_lines),
                )
                .where(
                    GameFlaw.user_id == game.user_id,
                    GameFlaw.game_id == game.id,
                    GameFlaw.ply == 10,
                )
            )
        ).scalar_one()

        # Both attrs must be accessible (not in unloaded) and return None (no blob written).
        unloaded = sa_inspect(flaw).unloaded
        assert "allowed_pv_lines" not in unloaded, (
            "allowed_pv_lines should be loaded after explicit undefer()"
        )
        assert "missed_pv_lines" not in unloaded, (
            "missed_pv_lines should be loaded after explicit undefer()"
        )
        # Verify the loaded values are None (freshly seeded row has no blobs).
        assert flaw.allowed_pv_lines is None
        assert flaw.missed_pv_lines is None
