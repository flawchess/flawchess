"""Tests for the Phase 240 Plan 01 Alembic migration: reveal_tour_stage.

Regression suite for the migration that (D-09/D-10/D-12):
- adds `train_settings.reveal_tour_stage` (SmallInteger NOT NULL DEFAULT 0) with
  the CHECK `ck_train_settings_reveal_tour_stage` (0..3),
- backfills stage 3 wherever the Phase 222 walkthrough timestamp was non-null
  (the user finished the old single tour) and leaves every other row on 0 (a
  user mid-onboarding at deploy starts the split tour at part 1),
- drops the Phase 222 walkthrough timestamp column.

One-way data note: the original walkthrough completion instant is lost by the
upgrade (owner accepted in discuss, D-10). The downgrade restores the column
schema-wise and stamps an approximate `now()` for stage-3 rows, which the
downgrade test pins.

Structure mirrors tests/test_migration_186_user_import_settings.py: each test
drives Alembic via asyncio.to_thread against this run's private per-run
database, downgrades to the previous revision, asserts the data shape, then
upgrades back to head. DDL tests are NOT transactionally isolated, which is
safe because each run owns its own database and always ends at head.

Uses a dedicated test user ID range (999_600-999_602) to avoid FK collisions
with other migration test suites (999_5xx is the phase 186 range).
"""

import asyncio

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

TARGET_REVISION: str = "head"
BASE_REVISION: str = "778c806092fb"  # down_revision of the reveal_tour_stage migration

TABLE: str = "train_settings"
STAGE_COLUMN: str = "reveal_tour_stage"
# The Phase 222 column the migration retires; named here only to assert it is gone.
RETIRED_COLUMN: str = "reveal_walkthrough_seen_at"
CHECK_CONSTRAINT: str = "ck_train_settings_reveal_tour_stage"

_TEST_USER_STAMPED: int = 999_600
_TEST_USER_UNSTAMPED: int = 999_601
_TEST_USER_CHECK: int = 999_602

# Stage bounds enforced by the CHECK (the migration's literal bound is 0..3).
_STAGE_ABOVE_MAX: int = 4
_STAGE_BELOW_MIN: int = -1

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


# --- Schema existence helpers ------------------------------------------------


async def _column_exists(engine, table: str, column: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :tbl AND column_name = :col"
            ),
            {"tbl": table, "col": column},
        )
        return bool(result.scalar())


async def _check_constraint_exists(engine, name: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        )
        return bool(result.scalar())


# --- Fixture helpers ---------------------------------------------------------


async def _insert_user(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "email": f"migration240-test-{user_id}@example.com"},
        )


async def _insert_settings_at_base(engine, user_id: int, *, stamped: bool) -> None:
    """Insert a train_settings row at the BASE revision (old column present).

    Names only `user_id` and the retired timestamp; every other column has a
    server default.
    """
    stamp_sql = "now()" if stamped else "NULL"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                f"INSERT INTO train_settings (user_id, {RETIRED_COLUMN}) VALUES (:uid, {stamp_sql})"
            ),
            {"uid": user_id},
        )


async def _get_stage(engine, user_id: int) -> int | None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT {STAGE_COLUMN} FROM train_settings WHERE user_id = :uid"),
            {"uid": user_id},
        )
        row = result.fetchone()
    return None if row is None else row[0]


async def _get_retired_value_is_set(engine, user_id: int) -> bool | None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT {RETIRED_COLUMN} IS NOT NULL FROM train_settings WHERE user_id = :uid"),
            {"uid": user_id},
        )
        row = result.fetchone()
    return None if row is None else bool(row[0])


async def _cleanup(engine, *user_ids: int) -> None:
    async with engine.begin() as conn:
        for user_id in user_ids:
            await conn.execute(
                text("DELETE FROM train_settings WHERE user_id = :uid"), {"uid": user_id}
            )
            await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


# --- Tests -------------------------------------------------------------------


async def test_backfills_stage_three_from_old_timestamp_and_drops_old_column(test_engine) -> None:
    """D-10/D-12: a row whose old walkthrough timestamp was set lands on stage 3,
    a row whose timestamp was NULL lands on stage 0, and the old column is gone."""
    await _run_downgrade(BASE_REVISION)
    try:
        await _insert_user(test_engine, _TEST_USER_STAMPED)
        await _insert_user(test_engine, _TEST_USER_UNSTAMPED)
        await _insert_settings_at_base(test_engine, _TEST_USER_STAMPED, stamped=True)
        await _insert_settings_at_base(test_engine, _TEST_USER_UNSTAMPED, stamped=False)
        assert await _column_exists(test_engine, TABLE, RETIRED_COLUMN)
        assert not await _column_exists(test_engine, TABLE, STAGE_COLUMN)

        await _run_upgrade(TARGET_REVISION)

        assert await _get_stage(test_engine, _TEST_USER_STAMPED) == 3
        assert await _get_stage(test_engine, _TEST_USER_UNSTAMPED) == 0
        assert not await _column_exists(test_engine, TABLE, RETIRED_COLUMN), (
            "The Phase 222 walkthrough timestamp column should be dropped at head"
        )
        assert await _column_exists(test_engine, TABLE, STAGE_COLUMN)
    finally:
        await _run_upgrade(TARGET_REVISION)
        await _cleanup(test_engine, _TEST_USER_STAMPED, _TEST_USER_UNSTAMPED)


async def test_check_constraint_rejects_out_of_range_stage(test_engine) -> None:
    """D-09 defense-in-depth: the DB CHECK rejects a stage outside 0..3, on both
    an INSERT above the bound and an UPDATE below it."""
    await _run_upgrade(TARGET_REVISION)
    assert await _check_constraint_exists(test_engine, CHECK_CONSTRAINT)
    await _insert_user(test_engine, _TEST_USER_CHECK)

    try:
        with pytest.raises(IntegrityError):
            async with test_engine.begin() as conn:
                await conn.execute(
                    text(
                        f"INSERT INTO train_settings (user_id, {STAGE_COLUMN}) "
                        "VALUES (:uid, :stage)"
                    ),
                    {"uid": _TEST_USER_CHECK, "stage": _STAGE_ABOVE_MAX},
                )

        # A valid row, then an out-of-range UPDATE against it.
        async with test_engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO train_settings (user_id) VALUES (:uid)"),
                {"uid": _TEST_USER_CHECK},
            )
        with pytest.raises(IntegrityError):
            async with test_engine.begin() as conn:
                await conn.execute(
                    text(f"UPDATE train_settings SET {STAGE_COLUMN} = :stage WHERE user_id = :uid"),
                    {"uid": _TEST_USER_CHECK, "stage": _STAGE_BELOW_MIN},
                )
        assert await _get_stage(test_engine, _TEST_USER_CHECK) == 0
    finally:
        await _cleanup(test_engine, _TEST_USER_CHECK)


async def test_downgrade_restores_old_column_and_removes_stage(test_engine) -> None:
    """D-10: the downgrade restores the retired column (set for a stage-3 row,
    NULL for a stage-0 row) and removes the stage column and its CHECK; a
    re-upgrade returns to head."""
    await _run_upgrade(TARGET_REVISION)
    await _insert_user(test_engine, _TEST_USER_STAMPED)
    await _insert_user(test_engine, _TEST_USER_UNSTAMPED)
    async with test_engine.begin() as conn:
        await conn.execute(
            text(f"INSERT INTO train_settings (user_id, {STAGE_COLUMN}) VALUES (:uid, 3)"),
            {"uid": _TEST_USER_STAMPED},
        )
        await conn.execute(
            text("INSERT INTO train_settings (user_id) VALUES (:uid)"),
            {"uid": _TEST_USER_UNSTAMPED},
        )

    try:
        await _run_downgrade(BASE_REVISION)

        assert await _column_exists(test_engine, TABLE, RETIRED_COLUMN)
        assert not await _column_exists(test_engine, TABLE, STAGE_COLUMN)
        assert not await _check_constraint_exists(test_engine, CHECK_CONSTRAINT)
        assert await _get_retired_value_is_set(test_engine, _TEST_USER_STAMPED) is True
        assert await _get_retired_value_is_set(test_engine, _TEST_USER_UNSTAMPED) is False
    finally:
        await _run_upgrade(TARGET_REVISION)
        await _cleanup(test_engine, _TEST_USER_STAMPED, _TEST_USER_UNSTAMPED)

    assert await _column_exists(test_engine, TABLE, STAGE_COLUMN)
    assert await _check_constraint_exists(test_engine, CHECK_CONSTRAINT)
