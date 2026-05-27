"""Tests for bulk_insert_positions in game_repository.

Covers: column coverage, round-trip, NULL optional fields, empty-batch no-op,
rollback atomicity, and chunking across the chunk_size boundary.
Uses the test Postgres DB (`flawchess_test`) via the `db_session` fixture,
which auto-rolls-back each test (no DB mocks).
"""

import datetime
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.game_repository import bulk_insert_games, bulk_insert_positions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 1700


def _make_game_row(user_id: int) -> dict:
    """Return a minimal valid games row dict."""
    return {
        "user_id": user_id,
        "platform": "chess.com",
        "platform_game_id": f"game-{uuid.uuid4().hex}",
        "platform_url": None,
        "pgn": "[Event 'Test']\n\n1. e4 e5 *",
        "result": "1/2-1/2",
        "user_color": "white",
        "time_control_str": "600+0",
        "time_control_bucket": "blitz",
        "time_control_seconds": 600,
        "rated": True,
        "white_username": "Alice",
        "black_username": "Bob",
        "white_rating": 1500,
        "black_rating": 1500,
        "opening_name": None,
        "opening_eco": None,
        "played_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    }


def _make_full_position_row(game_id: int, user_id: int, ply: int) -> dict:
    """Return a position row with every non-id column populated."""
    base = ply * 1000
    return {
        "game_id": game_id,
        "user_id": user_id,
        "ply": ply,
        "full_hash": base + 1,
        "white_hash": base + 2,
        "black_hash": base + 3,
        "move_san": f"e{ply + 1}" if ply < 8 else None,
        "clock_seconds": float(600 - ply * 5),
        "material_count": 32 - ply,
        "material_signature": f"KQRBNPkqrbnp-{ply}",
        "material_imbalance": ply % 3,
        "has_opposite_color_bishops": ply % 2 == 0,
        "piece_count": max(0, 14 - ply),
        "backrank_sparse": ply > 10,
        "mixedness": ply * 3,
        "phase": 0,
        "eval_cp": 10 * ply,
        "eval_mate": None,
        "endgame_class": None,
    }


def _make_required_only_row(game_id: int, user_id: int, ply: int) -> dict:
    """Return a position row with only the required FK+hash columns."""
    return {
        "game_id": game_id,
        "user_id": user_id,
        "ply": ply,
        "full_hash": 0xABCD0000 + ply,
        "white_hash": 0xBBBB0000 + ply,
        "black_hash": 0xCCCC0000 + ply,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_insert_positions_column_coverage() -> None:
    """The _POSITION_COPY_COLUMNS tuple must exactly match GamePosition non-id columns."""
    import app.repositories.game_repository as repo_module

    assert hasattr(repo_module, "_POSITION_COPY_COLUMNS"), (
        "_POSITION_COPY_COLUMNS must be a module-level constant in game_repository"
    )
    columns = repo_module._POSITION_COPY_COLUMNS  # noqa: SLF001
    model_columns = {c.name for c in GamePosition.__table__.columns if c.name != "id"}
    assert set(columns) == model_columns, (
        f"_POSITION_COPY_COLUMNS is missing or has extra columns.\n"
        f"  In tuple only: {set(columns) - model_columns}\n"
        f"  In model only: {model_columns - set(columns)}"
    )
    assert "id" not in columns, "id must NOT be in _POSITION_COPY_COLUMNS"


@pytest.mark.asyncio
async def test_bulk_insert_positions_round_trip(db_session: AsyncSession) -> None:
    """Insert 3 fully-populated rows, SELECT them back, assert every column round-trips."""
    from tests.conftest import ensure_test_user

    user_id = 2001
    await ensure_test_user(db_session, user_id)

    game_ids = await bulk_insert_games(db_session, [_make_game_row(user_id)])
    game_id = game_ids[0]

    rows = [_make_full_position_row(game_id, user_id, ply) for ply in range(3)]
    await bulk_insert_positions(db_session, rows)
    await db_session.flush()

    result = await db_session.execute(
        select(GamePosition).where(GamePosition.game_id == game_id).order_by(GamePosition.ply)
    )
    db_rows = result.scalars().all()

    import app.repositories.game_repository as repo_module

    assert len(db_rows) == 3, f"Expected 3 rows, got {len(db_rows)}"
    for expected, actual in zip(rows, db_rows, strict=True):
        for col in repo_module._POSITION_COPY_COLUMNS:  # noqa: SLF001
            exp_val = expected.get(col)
            act_val = getattr(actual, col)
            # Float comparison: clock_seconds stored as REAL (4-byte float)
            if col == "clock_seconds" and exp_val is not None and act_val is not None:
                assert abs(act_val - exp_val) < 0.01, (
                    f"col={col}: expected {exp_val!r}, got {act_val!r}"
                )
            else:
                assert act_val == exp_val, f"col={col}: expected {exp_val!r}, got {act_val!r}"


@pytest.mark.asyncio
async def test_bulk_insert_positions_null_optional_fields(db_session: AsyncSession) -> None:
    """Insert 2 rows with only required keys; every optional column must read back as None."""
    from tests.conftest import ensure_test_user

    user_id = 2002
    await ensure_test_user(db_session, user_id)

    game_ids = await bulk_insert_games(db_session, [_make_game_row(user_id)])
    game_id = game_ids[0]

    rows = [_make_required_only_row(game_id, user_id, ply) for ply in range(2)]
    await bulk_insert_positions(db_session, rows)
    await db_session.flush()

    result = await db_session.execute(
        select(GamePosition).where(GamePosition.game_id == game_id).order_by(GamePosition.ply)
    )
    db_rows = result.scalars().all()
    assert len(db_rows) == 2, f"Expected 2 rows, got {len(db_rows)}"

    optional_cols = {
        "move_san",
        "clock_seconds",
        "material_count",
        "material_signature",
        "material_imbalance",
        "has_opposite_color_bishops",
        "piece_count",
        "backrank_sparse",
        "mixedness",
        "phase",
        "eval_cp",
        "eval_mate",
        "endgame_class",
    }
    for row in db_rows:
        for col in optional_cols:
            val = getattr(row, col)
            assert val is None, f"col={col} should be None for required-only row, got {val!r}"


@pytest.mark.asyncio
async def test_bulk_insert_positions_empty_batch_noop(db_session: AsyncSession) -> None:
    """Calling bulk_insert_positions([]) must be a no-op and not acquire a DB connection."""
    with patch.object(type(db_session), "connection") as mock_conn:
        await bulk_insert_positions(db_session, [])
        mock_conn.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_insert_positions_rollback_atomicity(test_engine) -> None:  # type: ignore[no-untyped-def]
    """COPY must participate in the session transaction: rollback removes all rows.

    Opens a fresh session (not the rollback-wrapped db_session) so that
    session.rollback() actually abandons the transaction rather than just
    restoring a savepoint.  After rollback a second fresh session reads back
    zero games and zero positions for the test user.
    """
    from tests.conftest import ensure_test_user

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = 2003
    game_id: int | None = None

    # Ensure user exists in a separate committed transaction.
    async with session_maker() as setup_session:
        await ensure_test_user(setup_session, user_id)
        await setup_session.commit()

    # WR-04 fix: clean up the committed test user in a finally block so the
    # session-scoped test_engine doesn't leak user_id=2003 across the rest
    # of the pytest session. The other tests in this file use the
    # rollback-wrapped db_session fixture and auto-clean, but this test
    # bypasses that wrapper (per D-7) to exercise real rollback semantics.
    try:
        try:
            async with session_maker() as session:
                game_ids = await bulk_insert_games(session, [_make_game_row(user_id)])
                game_id = game_ids[0]

                rows = [_make_full_position_row(game_id, user_id, ply) for ply in range(5)]
                await bulk_insert_positions(session, rows)

                # Trigger a constraint violation: duplicate PK insert forces rollback.
                # Use a raw SQL insert of a game with an explicit duplicate id.
                await session.execute(
                    text("INSERT INTO games (id) VALUES (:gid)"),
                    {"gid": game_id},
                )
                # This flush should raise IntegrityError due to duplicate PK
                await session.flush()

        except Exception:
            pass  # expected — the IntegrityError is the point

        # Verify: both games and game_positions rows are gone for this user+game.
        async with session_maker() as verify_session:
            game_count = (
                (await verify_session.execute(select(Game).where(Game.user_id == user_id)))
                .scalars()
                .all()
            )
            pos_count = (
                (
                    await verify_session.execute(
                        select(GamePosition).where(GamePosition.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(game_count) == 0, f"Expected 0 games after rollback, got {len(game_count)}"
            assert len(pos_count) == 0, f"Expected 0 positions after rollback, got {len(pos_count)}"
    finally:
        # Clean up the committed user so it doesn't leak across the session.
        async with session_maker() as cleanup_session:
            await cleanup_session.execute(
                text("DELETE FROM users WHERE id = :uid"),
                {"uid": user_id},
            )
            await cleanup_session.commit()


@pytest.mark.asyncio
async def test_bulk_insert_positions_chunking_across_chunk_size(
    db_session: AsyncSession,
) -> None:
    """Insert chunk_size + 1 (1701) rows; all 1701 must land in the table."""
    from tests.conftest import ensure_test_user

    user_id = 2004
    await ensure_test_user(db_session, user_id)

    game_ids = await bulk_insert_games(db_session, [_make_game_row(user_id)])
    game_id = game_ids[0]

    n_rows = _CHUNK_SIZE + 1  # 1701 — spans exactly two chunks
    # Use values within signed int64 range: 0x7F00000000000000 | ply is safe.
    rows = [
        {
            "game_id": game_id,
            "user_id": user_id,
            "ply": ply,
            "full_hash": 0x7F00000000000000 | ply,  # unique per ply, within int64
            "white_hash": 0x5A00000000000000 | ply,
            "black_hash": 0x3B00000000000000 | ply,
        }
        for ply in range(n_rows)
    ]
    await bulk_insert_positions(db_session, rows)
    await db_session.flush()

    result = await db_session.execute(select(GamePosition).where(GamePosition.game_id == game_id))
    inserted = result.scalars().all()
    assert len(inserted) == n_rows, f"Expected {n_rows} rows after chunking, got {len(inserted)}"
