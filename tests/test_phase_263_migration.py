"""Chain, round-trip and data-step tests for the two Phase 263 migrations.

b3d5f7a9c264 widens `ck_drill_solves_source` to admit `source = 3`; c4e6a8b0d375 deletes untouched
open sessions holding an unsolved retired filler row and drops `drill_sessions.is_warmup` and
`drill_solves.sharp_puzzle_id`. Each test runs the migration's own statement tuples inside the
rolled-back `db_session` transaction (Postgres DDL is transactional), so nothing outside the test
changes and no committed row needs cleanup.

The schema under test is the migrated head, so the dropped columns are absent unless a test first
runs the downgrade statements.
"""

from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillSolve, DrillSource
from tests.conftest import ensure_test_user

_VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"
_FOREIGN_SOURCE_PATH = (
    _VERSIONS_DIR / "20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py"
)
_RETIRE_PATH = (
    _VERSIONS_DIR / "20261202_130000_c4e6a8b0d375_phase_263_retire_warmup_and_filler_identity.py"
)

_PREVIOUS_HEAD = "e5c1b7d3a9f2"
_FOREIGN_SOURCE_REVISION = "b3d5f7a9c264"
_RETIRE_REVISION = "c4e6a8b0d375"

_USER_UNTOUCHED = 9326301
_USER_TOUCHED = 9326302
_USER_NO_LEGACY = 9326303
_USER_COMPLETED = 9326304
_NOW = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
_TODAY = datetime.date(2026, 1, 15)

_COLUMN_EXISTS_SQL = sa.text(
    "SELECT count(*) FROM information_schema.columns "
    "WHERE table_name = :table_name AND column_name = :column_name"
)


def _load_migration(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _run(db_session: AsyncSession, statements: tuple[str, ...]) -> None:
    for statement in statements:
        await db_session.execute(sa.text(statement))


async def _column_exists(db_session: AsyncSession, table_name: str, column_name: str) -> bool:
    result = await db_session.execute(
        _COLUMN_EXISTS_SQL, {"table_name": table_name, "column_name": column_name}
    )
    return result.scalar_one() == 1


async def _seed_session(
    db_session: AsyncSession,
    user_id: int,
    *,
    status: str,
    rows: list[tuple[int, bool]],
) -> int:
    """One session for `user_id` with a `(source, solved)` drill_solves row per entry."""
    await ensure_test_user(db_session, user_id)
    drill_session = DrillSession(
        user_id=user_id,
        session_date=_TODAY,
        status=status,
        puzzle_count=len(rows),
        expires_on=_TODAY + datetime.timedelta(days=1),
    )
    db_session.add(drill_session)
    await db_session.flush()
    for position, (source, solved) in enumerate(rows):
        db_session.add(
            DrillSolve(
                session_id=drill_session.id,
                position=position,
                user_id=user_id,
                game_id=None,
                ply=0,
                source=source,
                solved_at=_NOW if solved else None,
            )
        )
    await db_session.flush()
    return drill_session.id


async def _surviving(db_session: AsyncSession, session_ids: list[int]) -> set[int]:
    result = await db_session.execute(
        sa.text("SELECT id FROM drill_sessions WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": session_ids},
    )
    return {row[0] for row in result}


def test_migration_chain() -> None:
    foreign = _load_migration(_FOREIGN_SOURCE_PATH, "phase_263_foreign_source")
    retire = _load_migration(_RETIRE_PATH, "phase_263_retire")
    assert foreign.revision == _FOREIGN_SOURCE_REVISION
    assert foreign.down_revision == _PREVIOUS_HEAD
    assert retire.revision == _RETIRE_REVISION
    assert retire.down_revision == _FOREIGN_SOURCE_REVISION


@pytest.mark.asyncio
async def test_foreign_source_check_round_trip(db_session: AsyncSession) -> None:
    migration = _load_migration(_FOREIGN_SOURCE_PATH, "phase_263_foreign_source")
    session_id = await _seed_session(
        db_session,
        _USER_COMPLETED,
        status="completed",
        rows=[(int(DrillSource.SR_ITEM), True), (int(DrillSource.FOREIGN_BLUNDER), True)],
    )

    await _run(db_session, migration.DOWNGRADE_STATEMENTS)

    # The downgrade deleted the source 3 row before narrowing the CHECK; the source 0 row stays.
    remaining = await db_session.execute(
        sa.text("SELECT source FROM drill_solves WHERE session_id = :sid ORDER BY position"),
        {"sid": session_id},
    )
    assert [row[0] for row in remaining] == [int(DrillSource.SR_ITEM)]

    insert_foreign = sa.text(
        "INSERT INTO drill_solves (session_id, position, user_id, ply, source) "
        "VALUES (:sid, 5, :uid, 0, 3)"
    )
    params = {"sid": session_id, "uid": _USER_COMPLETED}
    # The narrowed CHECK rejects source 3 (a savepoint keeps the transaction usable).
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(insert_foreign, params)

    await _run(db_session, migration.UPGRADE_STATEMENTS)
    await db_session.execute(insert_foreign, params)


@pytest.mark.asyncio
async def test_untouched_open_sessions_with_unsolved_legacy_filler_are_deleted(
    db_session: AsyncSession,
) -> None:
    migration = _load_migration(_RETIRE_PATH, "phase_263_retire")
    legacy = int(DrillSource.LEGACY_SHARP_FILLER)
    sr = int(DrillSource.SR_ITEM)
    # Untouched open session with an unsolved legacy row: the only one that goes.
    untouched = await _seed_session(
        db_session, _USER_UNTOUCHED, status="open", rows=[(sr, False), (legacy, False)]
    )
    # Touched open session (one solve) with an unsolved legacy row: stays.
    touched = await _seed_session(
        db_session, _USER_TOUCHED, status="open", rows=[(sr, True), (legacy, False)]
    )
    # Untouched open session without any legacy row: stays.
    no_legacy = await _seed_session(
        db_session, _USER_NO_LEGACY, status="open", rows=[(sr, False), (sr, False)]
    )
    # Completed and expired sessions holding an unsolved legacy row and no solve at all, so only
    # the status guard keeps them: both stay.
    completed = await _seed_session(
        db_session, _USER_COMPLETED, status="completed", rows=[(sr, False), (legacy, False)]
    )
    expired = await _seed_session(
        db_session, _USER_COMPLETED, status="expired", rows=[(sr, False), (legacy, False)]
    )
    session_ids = [untouched, touched, no_legacy, completed, expired]

    # Only the data statement: the column drops are covered by the round-trip test below.
    await db_session.execute(sa.text(migration.UPGRADE_STATEMENTS[0]))

    assert await _surviving(db_session, session_ids) == {touched, no_legacy, completed, expired}
    # drill_solves cascade with the deleted session and nothing else.
    untouched_rows = await db_session.execute(
        sa.text("SELECT count(*) FROM drill_solves WHERE session_id = :sid"), {"sid": untouched}
    )
    assert untouched_rows.scalar_one() == 0
    kept_rows = await db_session.execute(
        sa.text("SELECT count(*) FROM drill_solves WHERE session_id = :sid"), {"sid": touched}
    )
    assert kept_rows.scalar_one() == 2


@pytest.mark.asyncio
async def test_retire_columns_round_trip(db_session: AsyncSession) -> None:
    migration = _load_migration(_RETIRE_PATH, "phase_263_retire")
    session_id = await _seed_session(
        db_session, _USER_COMPLETED, status="completed", rows=[(int(DrillSource.SR_ITEM), True)]
    )
    assert not await _column_exists(db_session, "drill_sessions", "is_warmup")
    assert not await _column_exists(db_session, "drill_solves", "sharp_puzzle_id")

    await _run(db_session, migration.DOWNGRADE_STATEMENTS)

    assert await _column_exists(db_session, "drill_sessions", "is_warmup")
    assert await _column_exists(db_session, "drill_solves", "sharp_puzzle_id")
    # Existing rows get the restored defaults: is_warmup false (NOT NULL), sharp_puzzle_id NULL.
    warmup = await db_session.execute(
        sa.text("SELECT is_warmup FROM drill_sessions WHERE id = :sid"), {"sid": session_id}
    )
    assert warmup.scalar_one() is False
    sharp = await db_session.execute(
        sa.text("SELECT sharp_puzzle_id FROM drill_solves WHERE session_id = :sid"),
        {"sid": session_id},
    )
    assert sharp.scalar_one() is None

    await _run(db_session, migration.UPGRADE_STATEMENTS)

    assert not await _column_exists(db_session, "drill_sessions", "is_warmup")
    assert not await _column_exists(db_session, "drill_solves", "sharp_puzzle_id")
