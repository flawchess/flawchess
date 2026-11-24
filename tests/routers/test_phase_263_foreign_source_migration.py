"""Round trip of the Phase 263 migration that widens ck_drill_solves_source to 0..3.

The migration's own SQL runs inside a transaction that is rolled back, so nothing outside this
test changes. The upgrade must accept a source 3 row; the downgrade must delete such rows BEFORE
narrowing the CHECK (otherwise the narrower CHECK aborts on a committed row, the Phase 206 lesson)
and leave every other source untouched.
"""

from __future__ import annotations

import datetime
import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261202_120000_b3d5f7a9c264_phase_263_foreign_blunder_source.py"
)
_FOREIGN_SOURCE = 3
_SR_SOURCE = 0


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase_263_foreign_source", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_chains_from_the_previous_head() -> None:
    module = _load_migration()
    assert module.revision == "b3d5f7a9c264"
    assert module.down_revision == "e5c1b7d3a9f2"


async def _seed_session_with_two_solves(conn) -> int:
    """A user, one session and one SR plus one foreign solve row; returns the session id."""
    user_id = (
        await conn.execute(
            sa.text(
                "INSERT INTO users (email, hashed_password, is_active, is_superuser, is_verified) "
                "VALUES ('mig263-' || gen_random_uuid() || '@example.com', 'x', true, false, false) "
                "RETURNING id"
            )
        )
    ).scalar_one()
    session_id = (
        await conn.execute(
            sa.text(
                "INSERT INTO drill_sessions (user_id, session_date, status, puzzle_count, "
                "requested_count, expires_on) "
                "VALUES (:uid, :day, 'open', 2, 2, :expires) RETURNING id"
            ),
            {
                "uid": user_id,
                "day": datetime.date(2031, 1, 1),
                "expires": datetime.date(2031, 1, 2),
            },
        )
    ).scalar_one()
    for position, source in enumerate((_SR_SOURCE, _FOREIGN_SOURCE)):
        await conn.execute(
            sa.text(
                "INSERT INTO drill_solves (session_id, position, user_id, ply, source) "
                "VALUES (:sid, :pos, :uid, :ply, :src)"
            ),
            {"sid": session_id, "pos": position, "uid": user_id, "ply": position, "src": source},
        )
    return int(session_id)


async def test_downgrade_deletes_foreign_rows_before_narrowing_and_upgrade_restores(
    test_engine,
) -> None:
    module = _load_migration()
    async with test_engine.connect() as conn:
        async with conn.begin() as transaction:
            session_id = await _seed_session_with_two_solves(conn)
            for statement in module.DOWNGRADE_STATEMENTS:
                await conn.execute(sa.text(statement))
            sources = (
                (
                    await conn.execute(
                        sa.text("SELECT source FROM drill_solves WHERE session_id = :sid"),
                        {"sid": session_id},
                    )
                )
                .scalars()
                .all()
            )
            assert sources == [_SR_SOURCE]
            for statement in module.UPGRADE_STATEMENTS:
                await conn.execute(sa.text(statement))
            await conn.execute(
                sa.text(
                    "INSERT INTO drill_solves (session_id, position, user_id, ply, source) "
                    "SELECT session_id, 5, user_id, 5, :src FROM drill_solves "
                    "WHERE session_id = :sid"
                ),
                {"sid": session_id, "src": _FOREIGN_SOURCE},
            )
            await transaction.rollback()


async def test_narrow_check_rejects_a_foreign_row(test_engine) -> None:
    module = _load_migration()
    async with test_engine.connect() as conn:
        async with conn.begin() as transaction:
            session_id = await _seed_session_with_two_solves(conn)
            # Downgrade statements minus the DELETE: the narrower CHECK must abort on the row.
            raised = False
            try:
                async with conn.begin_nested():
                    for statement in module.DOWNGRADE_STATEMENTS[1:]:
                        await conn.execute(sa.text(statement))
            except IntegrityError:
                raised = True
            assert raised, (
                f"narrowing the CHECK must fail while a source 3 row exists ({session_id})"
            )
            await transaction.rollback()
