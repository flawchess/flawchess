"""Tests for the Phase 178 Plan 01 Alembic migration: accuracy/acpl imported columns.

Regression suite for the migration that adds:
- `games.white_accuracy_imported` / `games.black_accuracy_imported` (REAL, nullable)
- `games.white_acpl_imported` / `games.black_acpl_imported` (SmallInteger, nullable)
- Copies the pre-migration platform-provided `white_accuracy` / `black_accuracy` /
  `white_acpl` / `black_acpl` values into the new `*_imported` columns, THEN NULLs
  the canonical columns (D-01/D-02/D-03).

MANDATORY behavioral assertion (not schema/column-presence only): a copy-AFTER-null
ordering bug would silently produce all-NULL `*_imported` columns and would NOT be
caught by a presence check. This suite proves the copy is real by round-tripping
through the SHIPPED down migration: seed a post-migration-shape row (`*_imported`
set, canonical NULL), `alembic downgrade -1` (down migration copies `*_imported`
back into canonical and drops the `*_imported` columns) — assert canonical now
holds the seeded values — then `alembic upgrade head` (up migration re-adds
`*_imported`, copies canonical into it, THEN nulls canonical) — assert `*_imported`
holds the values again AND canonical is NULL. A copy-AFTER-null ordering bug in
either direction fails this test.

Structure mirrors tests/test_migration_117.py: drives Alembic via asyncio.to_thread
against this run's private per-run database (not transactionally isolated — safe
because each run owns its own database and always ends at head).

Uses a dedicated test user ID range (999_300-999_301) to avoid FK collisions with
other migration test suites (116: 999_101-102, 117: 999_200-201, 91: 999_001-002).
"""

import asyncio

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

# ─── Constants (CLAUDE.md: no magic numbers) ─────────────────────────────────
TARGET_REVISION: str = "head"
# down_revision of the Phase 178 Plan 01 migration (the previous head before it).
BASE_REVISION: str = "939c3d99868d"

MINIMAL_PGN: str = "1. e4 e5 *"

# Test user ID range: 999_300-999_301 (dedicated to avoid FK collision with other
# migration test suites in this file's directory / project root).
_TEST_USER_ROUNDTRIP: int = 999_300
_TEST_USER_FRESH_INSERT: int = 999_301

# Seeded values for the copy-survival round-trip assertion.
_SEEDED_WHITE_ACCURACY: float = 84.0
_SEEDED_BLACK_ACCURACY: float = 61.0
_SEEDED_WHITE_ACPL: int = 20
_SEEDED_BLACK_ACPL: int = 55

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


# ─── Schema existence helper ──────────────────────────────────────────────────


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


# ─── Fixture helpers ──────────────────────────────────────────────────────────


async def _insert_user(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES (:id, :email, 'x', true, false, false) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "email": f"migration178-test-{user_id}@example.com"},
        )


async def _insert_game(engine, user_id: int, game_id_label: str) -> int:
    """Insert a minimal game row (no accuracy/acpl values). Returns the generated id."""
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


async def _cleanup(engine, user_id: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM games WHERE user_id = :uid"), {"uid": user_id})
        await conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})


# ─── Tests ────────────────────────────────────────────────────────────────────


async def test_copy_survives_downgrade_and_reupgrade_preserves_copy_before_null(
    test_engine,
) -> None:
    """MANDATORY behavioral copy-survival assertion via the shipped down migration.

    A copy-AFTER-null ordering bug would leave every `*_imported` column NULL,
    which this test would catch at the re-upgrade assertion — a schema/presence
    check alone would NOT catch it.
    """
    user_id = _TEST_USER_ROUNDTRIP

    # Ensure we start at head (the *_imported columns exist).
    await _run_upgrade(TARGET_REVISION)

    await _insert_user(test_engine, user_id)
    game_id = await _insert_game(test_engine, user_id, "migration178-roundtrip-game")

    # Seed the post-migration shape: *_imported set, canonical NULL (already NULL
    # on a fresh insert — set explicitly for clarity/robustness).
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE games SET "
                "white_accuracy_imported = :wa, black_accuracy_imported = :ba, "
                "white_acpl_imported = :wac, black_acpl_imported = :bac, "
                "white_accuracy = NULL, black_accuracy = NULL, "
                "white_acpl = NULL, black_acpl = NULL "
                "WHERE id = :gid"
            ),
            {
                "wa": _SEEDED_WHITE_ACCURACY,
                "ba": _SEEDED_BLACK_ACCURACY,
                "wac": _SEEDED_WHITE_ACPL,
                "bac": _SEEDED_BLACK_ACPL,
                "gid": game_id,
            },
        )

    # Step 1: downgrade -1 — the down migration copies *_imported back into the
    # canonical columns, then drops the *_imported columns.
    await _run_downgrade(BASE_REVISION)

    assert not await _column_exists(test_engine, "games", "white_accuracy_imported"), (
        "white_accuracy_imported should be dropped after downgrade"
    )

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT white_accuracy, black_accuracy, white_acpl, black_acpl "
                "FROM games WHERE id = :gid"
            ),
            {"gid": game_id},
        )
        row = result.fetchone()
    assert row is not None
    assert row[0] == pytest.approx(_SEEDED_WHITE_ACCURACY), (
        f"Expected white_accuracy == {_SEEDED_WHITE_ACCURACY} after downgrade "
        f"(restored from white_accuracy_imported), got {row[0]}"
    )
    assert row[1] == pytest.approx(_SEEDED_BLACK_ACCURACY), (
        f"Expected black_accuracy == {_SEEDED_BLACK_ACCURACY} after downgrade "
        f"(restored from black_accuracy_imported), got {row[1]}"
    )
    assert row[2] == _SEEDED_WHITE_ACPL, (
        f"Expected white_acpl == {_SEEDED_WHITE_ACPL} after downgrade, got {row[2]}"
    )
    assert row[3] == _SEEDED_BLACK_ACPL, (
        f"Expected black_acpl == {_SEEDED_BLACK_ACPL} after downgrade, got {row[3]}"
    )

    # Step 2: upgrade back to head — re-runs the up migration's copy-then-null.
    # The canonical columns (just restored above) get copied into *_imported,
    # THEN nulled. A copy-AFTER-null bug would leave *_imported all NULL here.
    await _run_upgrade(TARGET_REVISION)

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT white_accuracy_imported, black_accuracy_imported, "
                "white_acpl_imported, black_acpl_imported, "
                "white_accuracy, black_accuracy, white_acpl, black_acpl "
                "FROM games WHERE id = :gid"
            ),
            {"gid": game_id},
        )
        row = result.fetchone()
    assert row is not None
    assert row[0] == pytest.approx(_SEEDED_WHITE_ACCURACY), (
        f"Expected white_accuracy_imported == {_SEEDED_WHITE_ACCURACY} after "
        f"re-upgrade (copy precedes null), got {row[0]}"
    )
    assert row[1] == pytest.approx(_SEEDED_BLACK_ACCURACY), (
        f"Expected black_accuracy_imported == {_SEEDED_BLACK_ACCURACY} after "
        f"re-upgrade, got {row[1]}"
    )
    assert row[2] == _SEEDED_WHITE_ACPL, (
        f"Expected white_acpl_imported == {_SEEDED_WHITE_ACPL} after re-upgrade, got {row[2]}"
    )
    assert row[3] == _SEEDED_BLACK_ACPL, (
        f"Expected black_acpl_imported == {_SEEDED_BLACK_ACPL} after re-upgrade, got {row[3]}"
    )
    assert row[4] is None, f"Expected white_accuracy IS NULL after re-upgrade, got {row[4]}"
    assert row[5] is None, f"Expected black_accuracy IS NULL after re-upgrade, got {row[5]}"
    assert row[6] is None, f"Expected white_acpl IS NULL after re-upgrade, got {row[6]}"
    assert row[7] is None, f"Expected black_acpl IS NULL after re-upgrade, got {row[7]}"

    await _cleanup(test_engine, user_id)


async def test_imported_columns_present_and_independently_writable(test_engine) -> None:
    """At head, all four *_imported columns exist and are independently readable/writable."""
    await _run_upgrade(TARGET_REVISION)

    for column in (
        "white_accuracy_imported",
        "black_accuracy_imported",
        "white_acpl_imported",
        "black_acpl_imported",
    ):
        assert await _column_exists(test_engine, "games", column), (
            f"Expected games.{column} to exist at head"
        )

    user_id = _TEST_USER_ROUNDTRIP  # reused range; test runs in isolation via cleanup
    await _insert_user(test_engine, user_id)
    game_id = await _insert_game(test_engine, user_id, "migration178-independent-write-game")

    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE games SET white_accuracy_imported = 77.5, "
                "black_acpl_imported = 42 WHERE id = :gid"
            ),
            {"gid": game_id},
        )

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT white_accuracy_imported, black_accuracy_imported, "
                "white_acpl_imported, black_acpl_imported FROM games WHERE id = :gid"
            ),
            {"gid": game_id},
        )
        row = result.fetchone()
    assert row is not None
    assert row[0] == pytest.approx(77.5)
    assert row[1] is None
    assert row[2] is None
    assert row[3] == 42

    await _cleanup(test_engine, user_id)


async def test_canonical_and_imported_columns_null_on_fresh_insert(test_engine) -> None:
    """A fresh Game insert has all eight accuracy/acpl columns NULL (no server_default)."""
    await _run_upgrade(TARGET_REVISION)

    user_id = _TEST_USER_FRESH_INSERT
    await _insert_user(test_engine, user_id)
    game_id = await _insert_game(test_engine, user_id, "migration178-fresh-insert-game")

    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT white_accuracy, black_accuracy, white_acpl, black_acpl, "
                "white_accuracy_imported, black_accuracy_imported, "
                "white_acpl_imported, black_acpl_imported "
                "FROM games WHERE id = :gid"
            ),
            {"gid": game_id},
        )
        row = result.fetchone()
    assert row is not None
    assert all(value is None for value in row), (
        f"Expected all accuracy/acpl columns NULL on fresh insert, got {row}"
    )

    await _cleanup(test_engine, user_id)
