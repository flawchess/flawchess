"""Tests for Phase 91 Alembic migration: evals_completed_at column + partial index + backfill.

Regression suite for the migration that adds `games.evals_completed_at TIMESTAMPTZ NULL`,
the partial index `ix_games_evals_pending ON games(id) WHERE evals_completed_at IS NULL`,
and a one-shot backfill of pre-existing rows.

Structure: each test drives Alembic via asyncio.to_thread (alembic.command is synchronous
and calls asyncio.run() internally via env.py; it cannot be called directly inside an
already-running event loop). Tests run against this run's private per-run database
(flawchess_test_<pid|worker>) via the session-scoped test_engine fixture (conftest.py);
alembic/env.py picks it up from settings.DATABASE_URL, which test_engine patches.

Since the test session starts with `alembic upgrade head` already applied, each test
downgrades to the previous revision, asserts the downgraded state, then upgrades again
to assert the upgraded state.

Warning: these tests are NOT transactionally isolated — they perform real DDL on the
per-run database. They are safe to run in CI because they always end with
`alembic upgrade head` (restoring the schema), and each run owns its own database.
"""

import asyncio
import datetime

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

# ─── Constants (CLAUDE.md: no magic numbers) ─────────────────────────────────
EXPECTED_NULL_COUNT_POST_BACKFILL: int = 0
NOW_TOLERANCE_SECONDS: int = 5
MIGRATION_COLUMN_NAME: str = "evals_completed_at"
MIGRATION_INDEX_NAME: str = "ix_games_evals_pending"
TARGET_REVISION: str = "head"
BASE_REVISION: str = "e925558020b9"  # previous head — down_revision of our migration

pytestmark = pytest.mark.asyncio


def _make_alembic_cfg() -> AlembicConfig:
    """Build an AlembicConfig for this run's per-run test database.

    NOTE: alembic/env.py overrides sqlalchemy.url from settings.DATABASE_URL at
    load time (RESEARCH Pitfall 1), which test_engine has patched to this run's
    private clone (flawchess_test_<pid|worker>). So these migrations run against
    the per-run clone, NOT a shared static DB. We derive the URL from that same
    settings.DATABASE_URL for clarity even though env.py would override it.
    Alembic needs a sync (non-asyncpg) URL because its env.py calls
    asyncio.run() internally.
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
    """Return True if games.evals_completed_at column exists."""
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


async def _index_exists(engine) -> bool:
    """Return True if ix_games_evals_pending partial index exists."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'games' "
                "AND indexname = :idx"
            ),
            {"idx": MIGRATION_INDEX_NAME},
        )
        return bool(result.scalar())


async def _null_evals_count(engine) -> int:
    """Return count of games rows where evals_completed_at IS NULL."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM games WHERE evals_completed_at IS NULL")
        )
        return result.scalar() or 0


async def _index_predicate(engine) -> str:
    """Return the indexdef string for ix_games_evals_pending."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND tablename = 'games' "
                "AND indexname = :idx"
            ),
            {"idx": MIGRATION_INDEX_NAME},
        )
        return result.scalar() or ""


async def test_migration_adds_column_and_index(test_engine) -> None:
    """After upgrade head, games has evals_completed_at column + ix_games_evals_pending.

    Pattern: starts at head (already applied by conftest), downgrades to base,
    asserts absence, then upgrades to head, asserts presence.
    """
    # Ensure we are at head (conftest guarantees this, but be explicit)
    await _run_upgrade(TARGET_REVISION)

    # Column and index should exist at head
    assert await _column_exists(test_engine), (
        f"Expected column '{MIGRATION_COLUMN_NAME}' to exist after upgrade head"
    )
    assert await _index_exists(test_engine), (
        f"Expected index '{MIGRATION_INDEX_NAME}' to exist after upgrade head"
    )

    # Verify index predicate contains our IS NULL clause
    indexdef = await _index_predicate(test_engine)
    assert "evals_completed_at IS NULL" in indexdef, (
        f"Expected 'evals_completed_at IS NULL' in indexdef: {indexdef}"
    )

    # Downgrade to previous revision
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine), (
        f"Expected column '{MIGRATION_COLUMN_NAME}' absent after downgrade"
    )
    assert not await _index_exists(test_engine), (
        f"Expected index '{MIGRATION_INDEX_NAME}' absent after downgrade"
    )

    # Re-upgrade to restore schema for subsequent tests
    await _run_upgrade(TARGET_REVISION)

    assert await _column_exists(test_engine), (
        f"Expected column '{MIGRATION_COLUMN_NAME}' present after re-upgrade"
    )
    assert await _index_exists(test_engine), (
        f"Expected index '{MIGRATION_INDEX_NAME}' present after re-upgrade"
    )


async def test_backfill_leaves_no_pending_rows(test_engine) -> None:
    """After upgrade, all pre-existing games rows have evals_completed_at set.

    Strategy:
    1. Downgrade to base (column absent).
    2. Insert 3 games with known imported_at values via raw SQL.
    3. Upgrade to head — backfill UPDATE runs.
    4. Assert zero NULL rows; assert the 3 rows have evals_completed_at = imported_at.
    5. Clean up inserted rows.
    """
    test_user_id = 999_001
    fixed_ts_1 = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    fixed_ts_2 = datetime.datetime(2025, 3, 15, 8, 30, 0, tzinfo=datetime.timezone.utc)
    fixed_ts_3 = datetime.datetime(2025, 6, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    # Downgrade to base revision (drops the column)
    await _run_downgrade(BASE_REVISION)

    # Insert test user and 3 games without evals_completed_at (column doesn't exist yet)
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": test_user_id, "email": f"migration-test-{test_user_id}@example.com"},
        )
        for i, ts in enumerate([fixed_ts_1, fixed_ts_2, fixed_ts_3], start=1):
            await conn.execute(
                text(
                    "INSERT INTO games "
                    "(user_id, platform, platform_game_id, pgn, result, user_color, rated, is_computer_game, imported_at) "
                    "VALUES (:uid, 'lichess', :pgid, '1. e4 e5 *', '1/2-1/2', 'white', true, false, :ts)"
                ),
                {"uid": test_user_id, "pgid": f"migration-test-backfill-{i}", "ts": ts},
            )

    # Upgrade — triggers backfill: UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW())
    await _run_upgrade(TARGET_REVISION)

    # Assert zero NULL rows in entire table
    null_count = await _null_evals_count(test_engine)
    assert null_count == EXPECTED_NULL_COUNT_POST_BACKFILL, (
        f"Expected {EXPECTED_NULL_COUNT_POST_BACKFILL} NULL evals rows post-backfill, got {null_count}"
    )

    # Assert our 3 inserted rows have evals_completed_at == imported_at
    async with test_engine.connect() as conn:
        for i, expected_ts in enumerate([fixed_ts_1, fixed_ts_2, fixed_ts_3], start=1):
            result = await conn.execute(
                text(
                    "SELECT evals_completed_at FROM games "
                    "WHERE user_id = :uid AND platform_game_id = :pgid"
                ),
                {"uid": test_user_id, "pgid": f"migration-test-backfill-{i}"},
            )
            row = result.fetchone()
            assert row is not None, f"Expected game migration-test-backfill-{i} to exist"
            actual_ts = row[0]
            if actual_ts is not None and actual_ts.tzinfo is None:
                actual_ts = actual_ts.replace(tzinfo=datetime.timezone.utc)
            assert actual_ts == expected_ts, (
                f"Expected evals_completed_at={expected_ts}, got {actual_ts} for game {i}"
            )

    # Clean up inserted rows
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM games WHERE user_id = :uid"), {"uid": test_user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": test_user_id})


async def test_downgrade_removes_column_and_index(test_engine) -> None:
    """After downgrade -1, evals_completed_at column and ix_games_evals_pending are absent."""
    # Ensure at head
    await _run_upgrade(TARGET_REVISION)

    # Downgrade one step
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine), (
        f"Column '{MIGRATION_COLUMN_NAME}' should be absent after downgrade"
    )
    assert not await _index_exists(test_engine), (
        f"Index '{MIGRATION_INDEX_NAME}' should be absent after downgrade"
    )

    # Re-upgrade to restore schema
    await _run_upgrade(TARGET_REVISION)


async def test_backfill_uses_now_when_imported_at_null(test_engine) -> None:
    """When imported_at IS NULL, COALESCE falls back to NOW() — evals_completed_at is non-null.

    Bypasses the ORM's NOT NULL constraint via a temporary ALTER TABLE to drop/restore
    the NOT NULL constraint on imported_at, allowing us to insert a NULL value.
    See RESEARCH.md R-04 for the risk context.
    """
    test_user_id = 999_002
    platform_game_id = "migration-test-now-fallback"

    # Downgrade to base (column absent)
    await _run_downgrade(BASE_REVISION)

    before_ts = datetime.datetime.now(datetime.timezone.utc)

    async with test_engine.begin() as conn:
        # Temporarily allow NULL on imported_at so we can insert a NULL value.
        # We drop the NOT NULL constraint, insert the row, and restore it only AFTER
        # the upgrade (when the backfill has already set evals_completed_at = NOW()
        # for this row, making the imported_at column NOT NULL again safe to restore).
        await conn.execute(text("ALTER TABLE games ALTER COLUMN imported_at DROP NOT NULL"))
        # Ensure test user exists
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": test_user_id, "email": f"migration-test-{test_user_id}@example.com"},
        )
        # Insert game with NULL imported_at
        await conn.execute(
            text(
                "INSERT INTO games "
                "(user_id, platform, platform_game_id, pgn, result, user_color, rated, is_computer_game, imported_at) "
                "VALUES (:uid, 'lichess', :pgid, '1. e4 *', '1/2-1/2', 'white', true, false, NULL)"
            ),
            {"uid": test_user_id, "pgid": platform_game_id},
        )
        # Note: do NOT restore NOT NULL here — the NULL row still exists.
        # We restore it after the upgrade which backfills it to NOW().

    # Upgrade — triggers backfill; NULL imported_at should fall back to NOW()
    await _run_upgrade(TARGET_REVISION)

    # Restore NOT NULL on imported_at: first backfill the NULL imported_at value,
    # then restore the constraint. The backfill sets evals_completed_at but
    # imported_at remains NULL (it was never set during the insert).
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE games SET imported_at = NOW() WHERE user_id = :uid AND imported_at IS NULL"
            ),
            {"uid": test_user_id},
        )
        await conn.execute(text("ALTER TABLE games ALTER COLUMN imported_at SET NOT NULL"))

    after_ts = datetime.datetime.now(datetime.timezone.utc)

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT evals_completed_at FROM games "
                "WHERE user_id = :uid AND platform_game_id = :pgid"
            ),
            {"uid": test_user_id, "pgid": platform_game_id},
        )
        row = result.fetchone()
        assert row is not None, "Expected the test game to exist"
        actual_ts = row[0]
        if actual_ts is not None and actual_ts.tzinfo is None:
            actual_ts = actual_ts.replace(tzinfo=datetime.timezone.utc)

        assert actual_ts is not None, (
            "Expected evals_completed_at to be non-null for game with NULL imported_at"
        )
        # Should be within NOW_TOLERANCE_SECONDS of the upgrade time
        lower = before_ts - datetime.timedelta(seconds=NOW_TOLERANCE_SECONDS)
        upper = after_ts + datetime.timedelta(seconds=NOW_TOLERANCE_SECONDS)
        assert lower <= actual_ts <= upper, (
            f"Expected evals_completed_at in [{lower}, {upper}], got {actual_ts}"
        )

    # Clean up
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM games WHERE user_id = :uid"), {"uid": test_user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": test_user_id})
