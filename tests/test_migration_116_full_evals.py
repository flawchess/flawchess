"""Tests for Phase 116 Alembic migration: full_evals_completed_at column + indexes + backfill.

Regression suite for the migration that adds:
- `games.full_evals_completed_at TIMESTAMPTZ NULL` (EVAL-05 / D-116-05)
- partial index `ix_games_full_evals_pending ON games(id) WHERE full_evals_completed_at IS NULL`
- partial index `ix_gp_full_hash_opening ON game_positions(full_hash) WHERE ply <= 20` (EVAL-03)
- verified backfill (D-116-06): marks games where every non-terminal ply has eval coverage

Structure mirrors test_migration_91_evals_completed_at.py: each test drives Alembic via
asyncio.to_thread, runs against this run's private per-run database (flawchess_test_<pid|worker>),
downgrades to the previous revision, asserts the downgraded state, then upgrades again to assert
the upgraded state.

Warning: these tests are NOT transactionally isolated — they perform real DDL on the
per-run database. They are safe to run in CI because they always end with
`alembic upgrade head`, and each run owns its own database.
"""

import asyncio
import datetime

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

# ─── Constants (CLAUDE.md: no magic numbers) ─────────────────────────────────
MIGRATION_COLUMN_NAME: str = "full_evals_completed_at"
GAMES_INDEX_NAME: str = "ix_games_full_evals_pending"
GP_INDEX_NAME: str = "ix_gp_full_hash_opening"
TARGET_REVISION: str = "head"
BASE_REVISION: str = "07994baf3b15"  # down_revision of our migration

# Minimal PGN to satisfy NOT NULL constraint on games.pgn
MINIMAL_PGN: str = "1. e4 e5 *"

pytestmark = pytest.mark.asyncio


def _make_alembic_cfg() -> AlembicConfig:
    """Build an AlembicConfig for this run's per-run test database.

    alembic/env.py overrides sqlalchemy.url from settings.DATABASE_URL at load
    time, which test_engine has patched to this run's private clone. Derives
    the sync URL from settings for clarity even though env.py would override it.
    """
    from app.core.config import settings

    cfg = AlembicConfig("alembic.ini")
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


async def _run_upgrade(revision: str = TARGET_REVISION) -> None:
    """Run alembic upgrade in a thread (alembic calls asyncio.run internally)."""
    cfg = _make_alembic_cfg()
    await asyncio.to_thread(alembic_command.upgrade, cfg, revision)


async def _run_downgrade(revision: str = BASE_REVISION) -> None:
    """Run alembic downgrade in a thread."""
    cfg = _make_alembic_cfg()
    await asyncio.to_thread(alembic_command.downgrade, cfg, revision)


async def _column_exists(engine) -> bool:
    """Return True if games.full_evals_completed_at column exists."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'games' "
                "AND column_name = :col"
            ),
            {"col": MIGRATION_COLUMN_NAME},
        )
        return bool(result.scalar())


async def _games_index_exists(engine) -> bool:
    """Return True if ix_games_full_evals_pending partial index exists."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'games' "
                "AND indexname = :idx"
            ),
            {"idx": GAMES_INDEX_NAME},
        )
        return bool(result.scalar())


async def _gp_index_exists(engine) -> bool:
    """Return True if ix_gp_full_hash_opening partial index exists."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'game_positions' "
                "AND indexname = :idx"
            ),
            {"idx": GP_INDEX_NAME},
        )
        return bool(result.scalar())


async def _get_full_evals_completed_at(
    engine, user_id: int, game_id: int
) -> datetime.datetime | None:
    """Fetch full_evals_completed_at for a specific game."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT full_evals_completed_at FROM games WHERE id = :gid AND user_id = :uid"),
            {"gid": game_id, "uid": user_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        ts = row[0]
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts


async def _insert_user(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "email": f"migration116-test-{user_id}@example.com"},
        )


async def _insert_game(engine, user_id: int, game_id_label: str) -> int:
    """Insert a minimal game row and return its generated id."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO games "
                "(user_id, platform, platform_game_id, pgn, result, user_color, rated, is_computer_game) "
                "VALUES (:uid, 'lichess', :pgid, :pgn, '1/2-1/2', 'white', true, false) "
                "RETURNING id"
            ),
            {"uid": user_id, "pgid": game_id_label, "pgn": MINIMAL_PGN},
        )
        row = result.fetchone()
        assert row is not None
        return int(row[0])


async def _insert_game_position(
    engine,
    user_id: int,
    game_id: int,
    ply: int,
    eval_cp: int | None,
    eval_mate: int | None,
    move_san: str | None,
) -> None:
    """Insert a minimal game_positions row.

    move_san is required (no default): the backfill anti-join uses
    `move_san IS NOT NULL` as the non-terminal marker (CR-01), so every
    fixture row must state explicitly whether it models a non-terminal ply
    (move_san set) or the terminal-position row (move_san None — the import
    pipeline appends one such row, with NULL evals, to EVERY game).
    """
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO game_positions "
                "(user_id, game_id, ply, full_hash, white_hash, black_hash, move_san) "
                "VALUES (:uid, :gid, :ply, :fh, :wh, :bh, :ms) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "uid": user_id,
                "gid": game_id,
                "ply": ply,
                "fh": 12345 + ply,
                "wh": 67890 + ply,
                "bh": 11111 + ply,
                "ms": move_san,
            },
        )
        if eval_cp is not None or eval_mate is not None:
            await conn.execute(
                text(
                    "UPDATE game_positions SET eval_cp = :cp, eval_mate = :mt "
                    "WHERE user_id = :uid AND game_id = :gid AND ply = :ply"
                ),
                {"cp": eval_cp, "mt": eval_mate, "uid": user_id, "gid": game_id, "ply": ply},
            )


async def _cleanup(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM game_positions WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await conn.execute(text("DELETE FROM games WHERE user_id = :uid"), {"uid": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


async def test_migration_adds_column_and_indexes(test_engine) -> None:
    """After upgrade head, column + both indexes exist; after downgrade, all gone.

    Pattern: starts at head (already applied by conftest), downgrades to base,
    asserts absence, then upgrades to head, asserts presence.
    """
    await _run_upgrade(TARGET_REVISION)

    # Column and both indexes should exist at head
    assert await _column_exists(test_engine), (
        f"Expected column '{MIGRATION_COLUMN_NAME}' after upgrade head"
    )
    assert await _games_index_exists(test_engine), (
        f"Expected index '{GAMES_INDEX_NAME}' after upgrade head"
    )
    assert await _gp_index_exists(test_engine), (
        f"Expected index '{GP_INDEX_NAME}' after upgrade head"
    )

    # Downgrade to base revision
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine), (
        f"Column '{MIGRATION_COLUMN_NAME}' should be absent after downgrade"
    )
    assert not await _games_index_exists(test_engine), (
        f"Index '{GAMES_INDEX_NAME}' should be absent after downgrade"
    )
    assert not await _gp_index_exists(test_engine), (
        f"Index '{GP_INDEX_NAME}' should be absent after downgrade"
    )

    # Re-upgrade to restore schema for subsequent tests
    await _run_upgrade(TARGET_REVISION)

    assert await _column_exists(test_engine), (
        f"Expected column '{MIGRATION_COLUMN_NAME}' after re-upgrade"
    )
    assert await _games_index_exists(test_engine), (
        f"Expected index '{GAMES_INDEX_NAME}' after re-upgrade"
    )
    assert await _gp_index_exists(test_engine), f"Expected index '{GP_INDEX_NAME}' after re-upgrade"


async def test_backfill_marks_fully_covered_game(test_engine) -> None:
    """D-116-06: a game whose every non-terminal ply has eval coverage is marked.

    The fixture mirrors real process_game_pgn output (CR-01 regression guard):
    every imported game carries a terminal-position row with move_san IS NULL
    and eval_cp/eval_mate NULL. The backfill must NOT let that row disqualify
    the game — only non-terminal (move_san IS NOT NULL) rows count.

    Strategy:
    1. Downgrade to base.
    2. Insert a user + game + 2 non-terminal rows (both with eval_cp set)
       + 1 terminal row (move_san NULL, evals NULL).
    3. Upgrade to head — backfill UPDATE runs.
    4. Assert the game has full_evals_completed_at set (non-NULL).
    5. Cleanup.
    """
    test_user_id = 999_101

    # Downgrade (column absent)
    await _run_downgrade(BASE_REVISION)

    await _insert_user(test_engine, test_user_id)
    game_id = await _insert_game(test_engine, test_user_id, "migration116-covered-game")
    # Insert 2 non-terminal positions both with eval_cp set (no NULL evals)
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=0, eval_cp=50, eval_mate=None, move_san="e4"
    )
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=1, eval_cp=-30, eval_mate=None, move_san="e5"
    )
    # Terminal row: move_san NULL + NULL evals — present in EVERY imported game.
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=2, eval_cp=None, eval_mate=None, move_san=None
    )

    # Upgrade — triggers backfill
    await _run_upgrade(TARGET_REVISION)

    ts = await _get_full_evals_completed_at(test_engine, test_user_id, game_id)
    assert ts is not None, (
        "Expected full_evals_completed_at to be set for game with all evals covered"
    )

    await _cleanup(test_engine, test_user_id)


async def test_backfill_skips_game_with_null_eval(test_engine) -> None:
    """D-116-06: a game with a NULL-eval NON-TERMINAL ply is NOT marked.

    The uncovered ply carries move_san (non-terminal) so it legitimately
    disqualifies the game; the terminal row is also present so the fixture
    matches real import-pipeline output (CR-01 regression guard).

    Strategy:
    1. Downgrade to base.
    2. Insert a user + game + 2 non-terminal rows (one with NULL evals)
       + 1 terminal row.
    3. Upgrade to head — backfill UPDATE runs.
    4. Assert the game has full_evals_completed_at IS NULL (not marked).
    5. Cleanup.
    """
    test_user_id = 999_102

    await _run_downgrade(BASE_REVISION)

    await _insert_user(test_engine, test_user_id)
    game_id = await _insert_game(test_engine, test_user_id, "migration116-uncovered-game")
    # ply 0 has eval_cp set; ply 1 is non-terminal (move_san set) with no eval (NULL)
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=0, eval_cp=50, eval_mate=None, move_san="e4"
    )
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=1, eval_cp=None, eval_mate=None, move_san="e5"
    )
    # Terminal row: must not be the reason the game is skipped.
    await _insert_game_position(
        test_engine, test_user_id, game_id, ply=2, eval_cp=None, eval_mate=None, move_san=None
    )

    await _run_upgrade(TARGET_REVISION)

    ts = await _get_full_evals_completed_at(test_engine, test_user_id, game_id)
    assert ts is None, (
        f"Expected full_evals_completed_at IS NULL for game with uncovered eval, got {ts}"
    )

    await _cleanup(test_engine, test_user_id)


async def test_downgrade_removes_column_and_indexes(test_engine) -> None:
    """After downgrade -1, all migration artifacts are absent."""
    await _run_upgrade(TARGET_REVISION)
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine), (
        f"Column '{MIGRATION_COLUMN_NAME}' should be absent after downgrade"
    )
    assert not await _games_index_exists(test_engine), (
        f"Index '{GAMES_INDEX_NAME}' should be absent after downgrade"
    )
    assert not await _gp_index_exists(test_engine), (
        f"Index '{GP_INDEX_NAME}' should be absent after downgrade"
    )

    # Restore schema
    await _run_upgrade(TARGET_REVISION)
