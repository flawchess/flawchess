"""Tests for the Phase 186 Plan 01 Alembic migration: user_import_settings.

Regression suite for the migration that:
- creates `user_import_settings` (user_id PK/FK CASCADE, tc_bullet/tc_blitz/tc_rapid/
  tc_classical booleans, game_cap SmallInteger CHECK IN (1000,3000,5000), plus three
  nullable backfill-cursor columns reserved for Plan 02).
- grandfathers every user that exists AT MIGRATION TIME to all four TCs enabled +
  game_cap=5000 via a one-time `INSERT ... SELECT` (D-13, checkpoint-confirmed).

Structure mirrors tests/test_migration_117.py: each test drives Alembic via
asyncio.to_thread against this run's private per-run database, downgrades to the
previous revision, asserts absence/grandfathering, then upgrades back to head. DDL
tests are NOT transactionally isolated — safe because each run owns its own database
and always ends at head.

Uses a dedicated test user ID range (999_500-999_501) to avoid FK collisions with
other migration test suites (see the 999_1xx/999_2xx ranges in test_migration_116/117).
"""

import asyncio

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

TARGET_REVISION: str = "head"
BASE_REVISION: str = "411a8de89c4b"  # down_revision of the user_import_settings migration

TABLE: str = "user_import_settings"
CHECK_CONSTRAINT: str = "ck_user_import_settings_cap"

_TEST_USER_GRANDFATHERED: int = 999_500
_TEST_USER_CHECK_CONSTRAINT: int = 999_501

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


async def _table_exists(engine, table: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :tbl"
            ),
            {"tbl": table},
        )
        return bool(result.scalar())


async def _columns_exist(engine, table: str) -> bool:
    expected = {
        "user_id",
        "tc_bullet",
        "tc_blitz",
        "tc_rapid",
        "tc_classical",
        "game_cap",
        "chesscom_backfill_oldest_year",
        "chesscom_backfill_oldest_month",
        "lichess_backfill_oldest_ms",
    }
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :tbl"
            ),
            {"tbl": table},
        )
        found = {row[0] for row in result.fetchall()}
    return expected.issubset(found)


async def _check_constraint_exists(engine, name: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        )
        return bool(result.scalar())


# ─── Fixture helpers ──────────────────────────────────────────────────────────


async def _insert_user(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "email": f"migration186-test-{user_id}@example.com"},
        )


async def _get_settings_row(engine, user_id: int) -> tuple | None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tc_bullet, tc_blitz, tc_rapid, tc_classical, game_cap "
                "FROM user_import_settings WHERE user_id = :uid"
            ),
            {"uid": user_id},
        )
        return result.fetchone()


async def _cleanup(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM user_import_settings WHERE user_id = :uid"), {"uid": user_id}
        )
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


# ─── Tests ────────────────────────────────────────────────────────────────────


async def test_migration_creates_table_with_expected_columns_and_check(test_engine) -> None:
    """After upgrade, user_import_settings + its CHECK constraint exist; after downgrade, gone."""
    await _run_upgrade(TARGET_REVISION)

    assert await _table_exists(test_engine, TABLE), "Expected user_import_settings after upgrade"
    assert await _columns_exist(test_engine, TABLE), (
        "Expected all user_import_settings columns after upgrade"
    )
    assert await _check_constraint_exists(test_engine, CHECK_CONSTRAINT), (
        f"Expected CHECK constraint '{CHECK_CONSTRAINT}' after upgrade"
    )

    await _run_downgrade(BASE_REVISION)

    assert not await _table_exists(test_engine, TABLE), (
        "user_import_settings should be absent after downgrade"
    )

    # Restore schema for subsequent tests.
    await _run_upgrade(TARGET_REVISION)
    assert await _table_exists(test_engine, TABLE), "Expected user_import_settings after re-upgrade"


async def test_grandfathers_existing_user_to_all_tcs_and_cap_5000(test_engine) -> None:
    """D-13 (checkpoint-confirmed): a user present BEFORE the migration runs gets
    tc_bullet=tc_blitz=tc_rapid=tc_classical=true and game_cap=5000.

    Strategy:
    1. Downgrade to base (table absent).
    2. Insert a user directly (simulating a pre-existing account).
    3. Upgrade to head — the grandfathering INSERT ... SELECT runs.
    4. Assert the settings row for that user has all-true TCs + cap 5000.
    5. Cleanup.
    """
    user_id = _TEST_USER_GRANDFATHERED

    await _run_downgrade(BASE_REVISION)
    await _insert_user(test_engine, user_id)

    # Upgrade — triggers the D-13 grandfathering backfill.
    await _run_upgrade(TARGET_REVISION)

    row = await _get_settings_row(test_engine, user_id)
    assert row is not None, "Expected a grandfathered user_import_settings row"
    tc_bullet, tc_blitz, tc_rapid, tc_classical, game_cap = row
    assert (tc_bullet, tc_blitz, tc_rapid, tc_classical) == (True, True, True, True), (
        f"Expected all four TCs enabled for a grandfathered user, got {row}"
    )
    assert game_cap == 5000, f"Expected game_cap=5000 for a grandfathered user, got {game_cap}"

    await _cleanup(test_engine, user_id)


async def test_check_constraint_rejects_invalid_game_cap(test_engine) -> None:
    """T-186-02 defense-in-depth: an invalid game_cap value is rejected at the DB level."""
    await _run_upgrade(TARGET_REVISION)
    user_id = _TEST_USER_CHECK_CONSTRAINT
    await _insert_user(test_engine, user_id)

    try:
        with pytest.raises(IntegrityError):
            async with test_engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO user_import_settings "
                        "(user_id, tc_bullet, tc_blitz, tc_rapid, tc_classical, game_cap) "
                        "VALUES (:uid, true, true, true, true, 2500)"
                    ),
                    {"uid": user_id},
                )
    finally:
        await _cleanup(test_engine, user_id)
