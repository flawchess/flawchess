"""Tests for Phase 117 Alembic migration: eval_jobs table, new columns, D-117-10 backfill.

Regression suite for the migration that adds:
- `game_positions.best_move VARCHAR(5) NULL` (EVAL-04 / D-117-01/03)
- `game_positions.pv TEXT NULL` (EVAL-04 / D-117-02)
- `games.lichess_evals_at TIMESTAMPTZ NULL` (D-117-06 provenance)
- `games.full_pv_completed_at TIMESTAMPTZ NULL` (D-117-12)
- partial index `ix_games_full_pv_pending ON games(id) WHERE full_pv_completed_at IS NULL`
- `eval_jobs` table with columns: id, tier, user_id, game_id, status, leased_by,
  lease_expiry, created_at, completed_at
- partial unique `uq_eval_jobs_game_active ON eval_jobs(game_id) WHERE status IN ('pending','leased')`
- `ix_eval_jobs_pick ON eval_jobs(tier, user_id, created_at) WHERE status='pending'`
- `ix_eval_jobs_leased ON eval_jobs(lease_expiry) WHERE status='leased'`
- D-117-10 backfill: SET lichess_evals_at = COALESCE(imported_at, NOW())
  WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL

Structure mirrors tests/test_migration_116_full_evals.py exactly: each test drives Alembic
via asyncio.to_thread, runs against this run's private per-run database, downgrades to the
previous revision, asserts absence, then upgrades to assert presence. DDL tests are NOT
transactionally isolated — safe because each run owns its own database and always ends at head.

Uses a dedicated test user ID range (999_200-999_299) to avoid FK collisions with the 116
migration test suite (which uses 999_101-999_102).
"""

import asyncio
import datetime

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

# ─── Constants (CLAUDE.md: no magic numbers) ─────────────────────────────────
TARGET_REVISION: str = "20260613120000"
BASE_REVISION: str = "20260612120000"  # down_revision of our migration (Phase 116 head)

# Index names added by this migration
GAMES_PV_PENDING_INDEX: str = "ix_games_full_pv_pending"
EVAL_JOBS_GAME_ACTIVE_INDEX: str = "uq_eval_jobs_game_active"
EVAL_JOBS_PICK_INDEX: str = "ix_eval_jobs_pick"
EVAL_JOBS_LEASED_INDEX: str = "ix_eval_jobs_leased"

# Test user ID range: 999_200-999_299 (dedicated to avoid FK collision with 116 test suite)
_TEST_USER_ANALYZED: int = 999_200
_TEST_USER_UNANALYZED: int = 999_201

MINIMAL_PGN: str = "1. e4 e5 *"

pytestmark = pytest.mark.asyncio


def _make_alembic_cfg() -> AlembicConfig:
    """Build an AlembicConfig for this run's per-run test database.

    alembic/env.py overrides sqlalchemy.url from settings.DATABASE_URL at load
    time, which test_engine has patched to this run's private clone.
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


# ─── Schema existence helpers ─────────────────────────────────────────────────


async def _column_exists(engine, table: str, column: str) -> bool:
    """Return True if the named column exists on the given table."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = :tbl "
                "AND column_name = :col"
            ),
            {"tbl": table, "col": column},
        )
        return bool(result.scalar())


async def _table_exists(engine, table: str) -> bool:
    """Return True if the named table exists in the public schema."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name = :tbl"
            ),
            {"tbl": table},
        )
        return bool(result.scalar())


async def _index_exists(engine, indexname: str) -> bool:
    """Return True if the named index exists in the public schema."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = :idx"
            ),
            {"idx": indexname},
        )
        return bool(result.scalar())


async def _eval_jobs_columns_exist(engine) -> bool:
    """Return True if the eval_jobs table has all expected columns."""
    expected = {
        "id",
        "tier",
        "user_id",
        "game_id",
        "status",
        "leased_by",
        "lease_expiry",
        "created_at",
        "completed_at",
    }
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'eval_jobs'"
            )
        )
        found = {row[0] for row in result.fetchall()}
    return expected.issubset(found)


# ─── Fixture helpers ──────────────────────────────────────────────────────────


async def _insert_user(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "email": f"migration117-test-{user_id}@example.com"},
        )


async def _insert_game(
    engine,
    user_id: int,
    game_id_label: str,
    white_blunders: int | None = None,
) -> int:
    """Insert a minimal game row. Returns the generated id."""
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
        game_id = int(row[0])

    if white_blunders is not None:
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE games SET white_blunders = :wb WHERE id = :gid AND user_id = :uid"),
                {"wb": white_blunders, "gid": game_id, "uid": user_id},
            )

    return game_id


async def _get_lichess_evals_at(engine, user_id: int, game_id: int) -> datetime.datetime | None:
    """Fetch lichess_evals_at for a specific game (only valid after upgrade)."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT lichess_evals_at FROM games WHERE id = :gid AND user_id = :uid"),
            {"gid": game_id, "uid": user_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        ts = row[0]
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        return ts


async def _cleanup(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM game_positions WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await conn.execute(text("DELETE FROM games WHERE user_id = :uid"), {"uid": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


# ─── Tests ────────────────────────────────────────────────────────────────────


async def test_migration_adds_columns_and_eval_jobs_table(test_engine) -> None:
    """After upgrade, all four new columns + eval_jobs table exist; after downgrade, all gone.

    Covers:
    - game_positions.best_move and game_positions.pv (EVAL-04 / D-117-01/02/03)
    - games.lichess_evals_at (D-117-06)
    - games.full_pv_completed_at (D-117-12)
    - eval_jobs table with all expected columns (QUEUE-01/06)
    """
    # Ensure we are at head
    await _run_upgrade(TARGET_REVISION)

    # All four columns must exist after upgrade
    assert await _column_exists(test_engine, "game_positions", "best_move"), (
        "Expected game_positions.best_move after upgrade"
    )
    assert await _column_exists(test_engine, "game_positions", "pv"), (
        "Expected game_positions.pv after upgrade"
    )
    assert await _column_exists(test_engine, "games", "lichess_evals_at"), (
        "Expected games.lichess_evals_at after upgrade"
    )
    assert await _column_exists(test_engine, "games", "full_pv_completed_at"), (
        "Expected games.full_pv_completed_at after upgrade"
    )

    # eval_jobs table must exist with all expected columns
    assert await _table_exists(test_engine, "eval_jobs"), "Expected eval_jobs table after upgrade"
    assert await _eval_jobs_columns_exist(test_engine), (
        "Expected eval_jobs to have all required columns after upgrade"
    )

    # Downgrade — all gone
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine, "game_positions", "best_move"), (
        "game_positions.best_move should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "game_positions", "pv"), (
        "game_positions.pv should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "games", "lichess_evals_at"), (
        "games.lichess_evals_at should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "games", "full_pv_completed_at"), (
        "games.full_pv_completed_at should be absent after downgrade"
    )
    assert not await _table_exists(test_engine, "eval_jobs"), (
        "eval_jobs table should be absent after downgrade"
    )

    # Re-upgrade to restore schema for subsequent tests
    await _run_upgrade(TARGET_REVISION)

    assert await _column_exists(test_engine, "game_positions", "best_move"), (
        "Expected game_positions.best_move after re-upgrade"
    )
    assert await _column_exists(test_engine, "games", "lichess_evals_at"), (
        "Expected games.lichess_evals_at after re-upgrade"
    )
    assert await _table_exists(test_engine, "eval_jobs"), (
        "Expected eval_jobs table after re-upgrade"
    )


async def test_migration_adds_all_indexes(test_engine) -> None:
    """After upgrade, all four new partial indexes exist; after downgrade, all gone."""
    await _run_upgrade(TARGET_REVISION)

    assert await _index_exists(test_engine, GAMES_PV_PENDING_INDEX), (
        f"Expected index '{GAMES_PV_PENDING_INDEX}' after upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_GAME_ACTIVE_INDEX), (
        f"Expected index '{EVAL_JOBS_GAME_ACTIVE_INDEX}' after upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_PICK_INDEX), (
        f"Expected index '{EVAL_JOBS_PICK_INDEX}' after upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_LEASED_INDEX), (
        f"Expected index '{EVAL_JOBS_LEASED_INDEX}' after upgrade"
    )

    await _run_downgrade(BASE_REVISION)

    assert not await _index_exists(test_engine, GAMES_PV_PENDING_INDEX), (
        f"Index '{GAMES_PV_PENDING_INDEX}' should be absent after downgrade"
    )
    assert not await _index_exists(test_engine, EVAL_JOBS_GAME_ACTIVE_INDEX), (
        f"Index '{EVAL_JOBS_GAME_ACTIVE_INDEX}' should be absent after downgrade"
    )
    assert not await _index_exists(test_engine, EVAL_JOBS_PICK_INDEX), (
        f"Index '{EVAL_JOBS_PICK_INDEX}' should be absent after downgrade"
    )
    assert not await _index_exists(test_engine, EVAL_JOBS_LEASED_INDEX), (
        f"Index '{EVAL_JOBS_LEASED_INDEX}' should be absent after downgrade"
    )

    # Restore
    await _run_upgrade(TARGET_REVISION)

    assert await _index_exists(test_engine, GAMES_PV_PENDING_INDEX), (
        f"Expected index '{GAMES_PV_PENDING_INDEX}' after re-upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_GAME_ACTIVE_INDEX), (
        f"Expected index '{EVAL_JOBS_GAME_ACTIVE_INDEX}' after re-upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_PICK_INDEX), (
        f"Expected index '{EVAL_JOBS_PICK_INDEX}' after re-upgrade"
    )
    assert await _index_exists(test_engine, EVAL_JOBS_LEASED_INDEX), (
        f"Expected index '{EVAL_JOBS_LEASED_INDEX}' after re-upgrade"
    )


async def test_backfill_sets_lichess_evals_at_for_analyzed_game(test_engine) -> None:
    """D-117-10: game with white_blunders IS NOT NULL gets lichess_evals_at set by backfill.

    Strategy:
    1. Downgrade to base (lichess_evals_at column absent).
    2. Insert user + game with white_blunders set.
    3. Upgrade to head — backfill runs.
    4. Assert lichess_evals_at IS NOT NULL for that game.
    5. Cleanup.
    """
    user_id = _TEST_USER_ANALYZED

    await _run_downgrade(BASE_REVISION)

    await _insert_user(test_engine, user_id)
    game_id = await _insert_game(
        test_engine, user_id, "migration117-analyzed-game", white_blunders=2
    )

    # Upgrade — triggers D-117-10 backfill
    await _run_upgrade(TARGET_REVISION)

    ts = await _get_lichess_evals_at(test_engine, user_id, game_id)
    assert ts is not None, (
        "Expected lichess_evals_at to be set for game with white_blunders IS NOT NULL"
    )

    await _cleanup(test_engine, user_id)


async def test_backfill_leaves_lichess_evals_at_null_for_unanalyzed_game(test_engine) -> None:
    """D-117-10: game with white_blunders IS NULL is NOT touched by the backfill.

    Strategy:
    1. Downgrade to base.
    2. Insert user + game without white_blunders (white_blunders IS NULL).
    3. Upgrade to head — backfill runs.
    4. Assert lichess_evals_at IS NULL for that game.
    5. Cleanup.
    """
    user_id = _TEST_USER_UNANALYZED

    await _run_downgrade(BASE_REVISION)

    await _insert_user(test_engine, user_id)
    game_id = await _insert_game(
        test_engine, user_id, "migration117-unanalyzed-game", white_blunders=None
    )

    # Upgrade — backfill should skip this game
    await _run_upgrade(TARGET_REVISION)

    ts = await _get_lichess_evals_at(test_engine, user_id, game_id)
    assert ts is None, (
        f"Expected lichess_evals_at IS NULL for game with white_blunders IS NULL, got {ts}"
    )

    await _cleanup(test_engine, user_id)


async def test_downgrade_removes_all_migration_artifacts(test_engine) -> None:
    """After downgrade -1, all migration artifacts (columns, table, indexes) are absent."""
    await _run_upgrade(TARGET_REVISION)
    await _run_downgrade(BASE_REVISION)

    # Columns gone
    assert not await _column_exists(test_engine, "game_positions", "best_move"), (
        "game_positions.best_move should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "game_positions", "pv"), (
        "game_positions.pv should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "games", "lichess_evals_at"), (
        "games.lichess_evals_at should be absent after downgrade"
    )
    assert not await _column_exists(test_engine, "games", "full_pv_completed_at"), (
        "games.full_pv_completed_at should be absent after downgrade"
    )

    # Table + indexes gone
    assert not await _table_exists(test_engine, "eval_jobs"), (
        "eval_jobs table should be absent after downgrade"
    )
    assert not await _index_exists(test_engine, GAMES_PV_PENDING_INDEX), (
        f"Index '{GAMES_PV_PENDING_INDEX}' should be absent after downgrade"
    )
    assert not await _index_exists(test_engine, EVAL_JOBS_GAME_ACTIVE_INDEX), (
        f"Index '{EVAL_JOBS_GAME_ACTIVE_INDEX}' should be absent after downgrade"
    )

    # Restore schema
    await _run_upgrade(TARGET_REVISION)
