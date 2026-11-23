"""Round-trip test of the blunder-check points_possible migration (quick 261123-lb8, D-04).

The scenario is produced by the real API on the new points scale (sessions A and B), plus one
unended blunder window of a completed session (C). The migration's own SQL then runs inside a
transaction that is rolled back, so nothing outside this test changes: the downgrade must restore
the old points_possible formula on exactly the unended blunder windows of open sessions (no points
are touched in either direction), and the upgrade must bring every value back.
"""

from __future__ import annotations

import datetime
import importlib.util
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.blunder_check import BlunderCheckWindow, WindowCase
from tests.blunder_check_seed import (
    delete_blunder_check_sessions,
    register_user,
    seed_completed_blunder_check_session,
)
from tests.routers.test_blunder_check_drill import (
    _BLUNDER_AT_ONE,
    _BLUNDER_AT_THREE,
    _T0,
    _Clock,
    _ok,
    _setup,
    _started,
)

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261201_120000_e5c1b7d3a9f2_quick_261123_lb8_blunder_check_points_rescale.py"
)
_COMPLETED_SESSION_POINTS = 2
_COMPLETED_SESSION_AGE_DAYS = 3
_COMPLETED_BLUNDER_POSITION = 2
_COMPLETED_BLUNDER_PLY = 12

# (session_id, position, outcome, points_scored, points_possible) per window.
WindowSnapshot = list[tuple[int, int, int | None, int, int]]
# (session_id, position, move_index, points_awarded, points_forfeited) per answer row.
AnswerSnapshot = list[tuple[int, int, int, int, int]]

_WINDOWS_SQL = sa.text(
    "SELECT session_id, position, outcome, points_scored, points_possible "
    "FROM blunder_check_windows WHERE session_id IN :ids ORDER BY session_id, position"
).bindparams(sa.bindparam("ids", expanding=True))
_ANSWERS_SQL = sa.text(
    "SELECT w.session_id, w.position, a.move_index, a.points_awarded, a.points_forfeited "
    "FROM blunder_check_answers a JOIN blunder_check_windows w ON w.id = a.window_id "
    "WHERE w.session_id IN :ids ORDER BY w.session_id, w.position, a.move_index"
).bindparams(sa.bindparam("ids", expanding=True))


@pytest.fixture
def clock() -> Iterator[_Clock]:
    c = _Clock()
    app.dependency_overrides[dev_now_utc] = lambda: c.now
    yield c
    app.dependency_overrides.pop(dev_now_utc, None)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lb8_points_rescale", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _snapshot(conn, session_ids: list[int]) -> tuple[WindowSnapshot, AnswerSnapshot]:
    windows = (await conn.execute(_WINDOWS_SQL, {"ids": session_ids})).all()
    answers = (await conn.execute(_ANSWERS_SQL, {"ids": session_ids})).all()
    return [tuple(row) for row in windows], [tuple(row) for row in answers]


async def _make_unended_blunder_window(test_engine, session_id: int) -> None:
    """Turn the seeded herring of a completed session into an unended blunder window."""
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            await session.execute(
                update(BlunderCheckWindow)
                .where(BlunderCheckWindow.session_id == session_id)
                .values(
                    outcome=None,
                    blunder_position=_COMPLETED_BLUNDER_POSITION,
                    blunder_ply=_COMPLETED_BLUNDER_PLY,
                    window_case=int(WindowCase.ALLOWED),
                )
            )


def test_migration_chains_from_the_previous_head() -> None:
    module = _load_migration()
    assert module.revision == "e5c1b7d3a9f2"
    assert module.down_revision == "a7c3e5f9b261"


@pytest.mark.asyncio
async def test_migration_round_trips_on_open_unended_blunder_windows_only(
    test_engine, clock
) -> None:
    migration = _load_migration()
    completed_id: int | None = None
    specs = [_BLUNDER_AT_ONE, _BLUNDER_AT_THREE, _BLUNDER_AT_ONE]
    async with _setup(test_engine, specs) as a:
        user_b = await register_user("bc-points-migration", beta=True, test_engine=test_engine)
        async with _setup(test_engine, [_BLUNDER_AT_THREE], user_id_token=user_b) as b:
            # Session A: window 0 caught (ended), window 1 two safe calls with move 3 open.
            await _started(a, 0)
            await _ok(a, 1, "blunder", position=0)
            await _started(a, 1)
            await _ok(a, 1, "safe", position=1)
            await _ok(a, 2, "safe", position=1)
            # Session B: one safe call, then a timeout on a good move (pot 1 -> 0).
            await _started(b, 0)
            await _ok(b, 1, "safe")
            await _ok(b, 2, "timeout")
            # Session C: an unended blunder window of a session that is not open.
            completed_id = await seed_completed_blunder_check_session(
                test_engine,
                user_id=a.user_id,
                session_date=_T0.date() - datetime.timedelta(days=_COMPLETED_SESSION_AGE_DAYS),
                points=_COMPLETED_SESSION_POINTS,
            )
            try:
                await _make_unended_blunder_window(test_engine, completed_id)
                session_ids = [a.session_id, b.session_id, completed_id]

                async with test_engine.connect() as conn:
                    async with conn.begin() as transaction:
                        before = await _snapshot(conn, session_ids)
                        for statement in migration.DOWNGRADE_STATEMENTS:
                            await conn.execute(sa.text(statement))
                        old_windows, old_answers = await _snapshot(conn, session_ids)
                        for statement in migration.UPGRADE_STATEMENTS:
                            await conn.execute(sa.text(statement))
                        after = await _snapshot(conn, session_ids)
                        await transaction.rollback()
            finally:
                await delete_blunder_check_sessions(test_engine, [completed_id])

            assert completed_id is not None
            windows_new, answers_new = before
            a_id, b_id = a.session_id, b.session_id
            completed_before = next(row for row in windows_new if row[0] == completed_id)
            # Pre-test snapshot, on the new formula (produced through the API): (blunder position
            # - 1) + 2 + 1 as points_possible, the points as scored.
            assert (a_id, 0, 1, 2, 3) in windows_new
            assert (a_id, 1, None, 2, 5) in windows_new
            assert (a_id, 2, None, 0, 3) in windows_new
            assert (b_id, 0, None, 0, 5) in windows_new
            assert (a_id, 1, 1, 1, 0) in answers_new and (a_id, 1, 2, 1, 0) in answers_new
            assert (b_id, 0, 1, 1, 0) in answers_new and (b_id, 0, 2, 0, 1) in answers_new
            assert completed_before[2] is None and completed_before[3] == _COMPLETED_SESSION_POINTS

            # After the downgrade: unended blunder windows of open sessions are back on the old
            # formula, (position - 1) + 3 + 2; nothing else moves, points included.
            old_scale = {row[:2]: row for row in old_windows}
            assert old_scale[(a_id, 1)] == (a_id, 1, None, 2, 7)
            assert old_scale[(a_id, 2)] == (a_id, 2, None, 0, 5)
            assert old_scale[(b_id, 0)] == (b_id, 0, None, 0, 7)
            # The ended window of A and the unended window of the completed session are untouched.
            assert old_scale[(a_id, 0)] == (a_id, 0, 1, 2, 3)
            assert old_scale[(completed_id, 0)] == completed_before
            assert old_answers == answers_new

            # The upgrade restores every value, windows and answer rows.
            assert after == before
            assert old_windows != before[0]
