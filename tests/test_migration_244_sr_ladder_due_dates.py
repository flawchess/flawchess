"""Data-correctness test for the Phase 244 SR-ladder due-date push (revision e2a7c4f9b244).

Seeds one user with a single-weekday schedule, one bare game and one `drill_items` row per
case on distinct plies, plus completed `drill_sessions` (one per distinct solve day) holding
the SR solves at noon UTC. "today" is read from the DB (`now() AT TIME ZONE 'UTC'`), the same
instant the SQL uses. Cases and expected outcome:

  A  ACTIVE streak 1, SR correct 2d ago, due today+1       -> today+8 (floor = 2d ago + 10)
  B  ACTIVE streak 1, SR correct 2d ago, due today+20      -> unchanged (never pulled earlier)
  C  ACTIVE streak 1, SR correct 30d ago, due 27d ago      -> unchanged (floor already past,
                                                              D-09: overdue keeps its priority)
  D  ACTIVE streak 0, SR fail 1d ago, due today            -> today+3 (floor = 1d ago + 4)
  E  ACTIVE streak 0, SR fail 10d, correct 8d, fail 2d ago -> today+2 (the LATEST fail wins)
  F  ACTIVE streak 0, no solves, due today                 -> unchanged (never attempted)
  G  ACTIVE streak 0, SR fail 10d ago + RED_HERRING solve
     (wrong) 1d ago on the same game/ply, due 6d ago       -> unchanged (non-SR solves ignored)
  H  MASTERED streak 2 and PARKED fail_count 3, each with a
     recent SR solve and due 5d ago                        -> unchanged (only ACTIVE moves)
  I1 ACTIVE streak 0, SR fail 4d ago, due 4d ago           -> unchanged (floor == today, D-09)
  I2 ACTIVE streak 1, SR correct 9d ago, due 6d ago        -> today+1 (first future floor)
  K  ACTIVE streak 0, SR fail 1d ago + an unsolved SR row in
     an OPEN session today                                 -> today+3; the open session and its
                                                              unsolved row are untouched (D-10)
  L  ACTIVE streak 1, SR fail 2d ago + RED_HERRING correct
     1d ago, no SR correct solve, due 3d ago               -> unchanged (streak>=1 floor needs an
                                                              SR correct solve; never falls back
                                                              to the fail floor)

Streak, status, fail_count and ever_correct never change (D-06), and no expected due date falls
on the scheduled weekday (D-08: no snapping). Runs the exact SQL `upgrade()` executes
(`PUSH_DUE_DATES_SQL`), loaded from the revision by path.
"""

from __future__ import annotations

import datetime
import importlib.util
import pathlib
import uuid
from types import ModuleType

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_item import DrillItem, DrillStatus
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillSolve, DrillSource
from app.models.game import Game
from app.repositories import train_repository
from tests.conftest import ensure_test_user

_TEST_USER_ID = 99480

_MIGRATION_PATH = (
    pathlib.Path(__file__).parent.parent
    / "alembic"
    / "versions"
    / "20261102_120000_e2a7c4f9b244_phase_244_sr_ladder_due_date_push.py"
)

# Day offsets relative to the DB's UTC "today" (negative = in the past).
_CORRECT_RETRY = 10
_FAIL_RETRY = 4
_SCHEDULE_PROBE_OFFSET = 5  # the one scheduled weekday = (today + 5 days).weekday()
_SOLVE_HOUR_UTC = 12

_PLY_A, _PLY_B, _PLY_C, _PLY_D, _PLY_E, _PLY_F, _PLY_G = 1, 2, 3, 4, 5, 6, 7
_PLY_H_MASTERED, _PLY_H_PARKED, _PLY_I1, _PLY_I2, _PLY_K, _PLY_L = 8, 9, 10, 11, 12, 13

_PGN = "1. e4 e5 2. Nf3 Nc6 *"


def _load_migration_module() -> ModuleType:
    """Load the revision by path (alembic/versions is not an importable package)."""
    spec = importlib.util.spec_from_file_location("_phase_244_migration", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _TEST_USER_ID)


class _Seeder:
    """Seeds drill_items / drill_solves for one user; one session per distinct solve day."""

    def __init__(self, db: AsyncSession, today: datetime.date, game_id: int) -> None:
        self.db = db
        self.today = today
        self.game_id = game_id
        self._sessions: dict[int, tuple[int, int]] = {}  # day_offset -> (session_id, next_pos)

    async def item(
        self,
        ply: int,
        *,
        due_offset: int,
        streak: int = 0,
        status: DrillStatus = DrillStatus.ACTIVE,
        fail_count: int = 0,
        ever_correct: bool = False,
    ) -> None:
        self.db.add(
            DrillItem(
                user_id=_TEST_USER_ID,
                game_id=self.game_id,
                ply=ply,
                status=int(status),
                streak=streak,
                due_date=self.today + datetime.timedelta(days=due_offset),
                fail_count=fail_count,
                ever_correct=ever_correct,
            )
        )
        await self.db.flush()

    async def _session_for(self, day_offset: int, *, status: str) -> tuple[int, int]:
        if day_offset not in self._sessions:
            day = self.today + datetime.timedelta(days=day_offset)
            drill_session = DrillSession(
                user_id=_TEST_USER_ID,
                session_date=day,
                status=status,
                puzzle_count=1,
                expires_on=day + datetime.timedelta(days=1),
            )
            self.db.add(drill_session)
            await self.db.flush()
            self._sessions[day_offset] = (drill_session.id, 0)
        session_id, position = self._sessions[day_offset]
        self._sessions[day_offset] = (session_id, position + 1)
        return session_id, position

    async def solve(
        self,
        ply: int,
        *,
        day_offset: int,
        correct: bool | None,
        source: DrillSource = DrillSource.SR_ITEM,
        open_session: bool = False,
    ) -> None:
        """Add one solve; `correct=None` seeds an UNSOLVED row (solved_at NULL)."""
        session_id, position = await self._session_for(
            day_offset, status="open" if open_session else "completed"
        )
        solved_at = (
            None
            if correct is None
            else datetime.datetime.combine(
                self.today + datetime.timedelta(days=day_offset),
                datetime.time(_SOLVE_HOUR_UTC),
                tzinfo=datetime.UTC,
            )
        )
        self.db.add(
            DrillSolve(
                session_id=session_id,
                position=position,
                user_id=_TEST_USER_ID,
                game_id=self.game_id,
                ply=ply,
                source=int(source),
                correct_move=correct,
                solved_at=solved_at,
            )
        )
        await self.db.flush()


async def _seed_game(db: AsyncSession) -> int:
    game = Game(
        user_id=_TEST_USER_ID,
        platform="lichess",
        platform_game_id=f"mig244-{uuid.uuid4().hex[:8]}",
        platform_url="https://lichess.org/test",
        pgn=_PGN,
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=4,
    )
    db.add(game)
    await db.flush()
    game_id: int = game.id
    return game_id


async def _db_today(db: AsyncSession) -> datetime.date:
    return (await db.execute(text("SELECT (now() AT TIME ZONE 'UTC')::date"))).scalar_one()


async def _seed_cases(db: AsyncSession) -> tuple[datetime.date, int]:
    """Seed every case; returns (today, scheduled_weekday_mask)."""
    today = await _db_today(db)
    schedule_mask = 1 << (today + datetime.timedelta(days=_SCHEDULE_PROBE_OFFSET)).weekday()
    await train_repository.upsert_settings(
        db,
        user_id=_TEST_USER_ID,
        timezone="UTC",
        weekday_mask=schedule_mask,
        puzzles_per_session=6,
        reminder_enabled=False,
        reminder_hour=18,
        reminder_intent_at=None,
        now_utc=datetime.datetime.now(datetime.UTC),
    )
    s = _Seeder(db, today, await _seed_game(db))

    await s.item(_PLY_A, due_offset=1, streak=1, ever_correct=True)
    await s.solve(_PLY_A, day_offset=-2, correct=True)

    await s.item(_PLY_B, due_offset=20, streak=1, ever_correct=True)
    await s.solve(_PLY_B, day_offset=-2, correct=True)

    await s.item(_PLY_C, due_offset=-27, streak=1, ever_correct=True)
    await s.solve(_PLY_C, day_offset=-30, correct=True)

    await s.item(_PLY_D, due_offset=0, fail_count=1)
    await s.solve(_PLY_D, day_offset=-1, correct=False)

    await s.item(_PLY_E, due_offset=-2, fail_count=2, ever_correct=True)
    await s.solve(_PLY_E, day_offset=-10, correct=False)
    await s.solve(_PLY_E, day_offset=-8, correct=True)
    await s.solve(_PLY_E, day_offset=-2, correct=False)

    await s.item(_PLY_F, due_offset=0)

    await s.item(_PLY_G, due_offset=-6, fail_count=1)
    await s.solve(_PLY_G, day_offset=-10, correct=False)
    await s.solve(_PLY_G, day_offset=-1, correct=False, source=DrillSource.RED_HERRING)

    await s.item(
        _PLY_H_MASTERED, due_offset=-5, streak=2, status=DrillStatus.MASTERED, ever_correct=True
    )
    await s.solve(_PLY_H_MASTERED, day_offset=-1, correct=True)
    await s.item(_PLY_H_PARKED, due_offset=-5, status=DrillStatus.PARKED, fail_count=3)
    await s.solve(_PLY_H_PARKED, day_offset=-1, correct=False)

    await s.item(_PLY_I1, due_offset=-4, fail_count=1)
    await s.solve(_PLY_I1, day_offset=-_FAIL_RETRY, correct=False)
    await s.item(_PLY_I2, due_offset=-6, streak=1, ever_correct=True)
    await s.solve(_PLY_I2, day_offset=-(_CORRECT_RETRY - 1), correct=True)

    await s.item(_PLY_K, due_offset=0, fail_count=1)
    await s.solve(_PLY_K, day_offset=-1, correct=False)
    await s.solve(_PLY_K, day_offset=0, correct=None, open_session=True)

    await s.item(_PLY_L, due_offset=-3, streak=1, fail_count=1, ever_correct=True)
    await s.solve(_PLY_L, day_offset=-2, correct=False)
    await s.solve(_PLY_L, day_offset=-1, correct=True, source=DrillSource.RED_HERRING)
    return today, schedule_mask


async def _items_by_ply(db: AsyncSession) -> dict[int, DrillItem]:
    rows = (
        (await db.execute(select(DrillItem).where(DrillItem.user_id == _TEST_USER_ID)))
        .scalars()
        .all()
    )
    for row in rows:
        await db.refresh(row)
    return {row.ply: row for row in rows}


def _snapshot(items: dict[int, DrillItem]) -> dict[int, tuple[object, ...]]:
    return {
        ply: (row.status, row.streak, row.fail_count, row.ever_correct, row.due_date)
        for ply, row in items.items()
    }


@pytest.mark.asyncio
async def test_push_due_dates_per_case(db_session: AsyncSession) -> None:
    migration = _load_migration_module()
    today, schedule_mask = await _seed_cases(db_session)
    before = _snapshot(await _items_by_ply(db_session))

    await db_session.execute(text(migration.PUSH_DUE_DATES_SQL))
    items = await _items_by_ply(db_session)

    def day(offset: int) -> datetime.date:
        return today + datetime.timedelta(days=offset)

    expected_due = {
        _PLY_A: day(8),
        _PLY_B: day(20),
        _PLY_C: day(-27),
        _PLY_D: day(3),
        _PLY_E: day(2),
        _PLY_F: day(0),
        _PLY_G: day(-6),
        _PLY_H_MASTERED: day(-5),
        _PLY_H_PARKED: day(-5),
        _PLY_I1: day(-4),
        _PLY_I2: day(1),
        _PLY_K: day(3),
        _PLY_L: day(-3),
    }
    messages = {
        _PLY_A: "D-07: streak>=1 pushes to last correct + 10",
        _PLY_B: "D-07: never pulled earlier than the current due_date",
        _PLY_C: "D-09: floor already past keeps the overdue due_date",
        _PLY_D: "D-07: streak 0 pushes to last fail + 4",
        _PLY_E: "D-07: the LATEST fail determines the floor",
        _PLY_F: "D-07: never-attempted items stay due immediately",
        _PLY_G: "non-SR (herring) solves must be ignored",
        _PLY_H_MASTERED: "D-07: MASTERED rows are untouched",
        _PLY_H_PARKED: "D-07: PARKED rows are untouched",
        _PLY_I1: "D-09 boundary: floor == today does not move the item",
        _PLY_I2: "D-07: first future floor moves the item",
        _PLY_K: "D-10: an open session's unsolved row does not affect the push",
        _PLY_L: "D-07: streak>=1 without an SR correct solve must not use the fail floor",
    }
    for ply, expected in expected_due.items():
        assert items[ply].due_date == expected, messages[ply]
    # D-08: pushed dates are raw offsets, never snapped to the one scheduled weekday.
    for ply in (_PLY_A, _PLY_D, _PLY_E, _PLY_I2, _PLY_K):
        assert schedule_mask & (1 << items[ply].due_date.weekday()) == 0

    # D-06: only due_date may change.
    after = _snapshot(items)
    for ply, state_before in before.items():
        assert after[ply][:4] == state_before[:4], (
            f"ply {ply}: streak/status/fail_count/ever_correct"
        )

    # D-10: the open session and its unsolved row are untouched.
    unsolved = (
        (
            await db_session.execute(
                select(DrillSolve).where(
                    DrillSolve.user_id == _TEST_USER_ID, DrillSolve.solved_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(unsolved) == 1
    assert unsolved[0].correct_move is None
    open_sessions = (
        (
            await db_session.execute(
                select(DrillSession).where(
                    DrillSession.user_id == _TEST_USER_ID, DrillSession.status == "open"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(open_sessions) == 1


@pytest.mark.asyncio
async def test_push_due_dates_rerun_is_noop(db_session: AsyncSession) -> None:
    migration = _load_migration_module()
    await _seed_cases(db_session)

    await db_session.execute(text(migration.PUSH_DUE_DATES_SQL))
    after_first = _snapshot(await _items_by_ply(db_session))

    rerun = await db_session.execute(text(migration.PUSH_DUE_DATES_SQL))
    rerun_count = rerun.rowcount  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount
    assert rerun_count == 0, "a second run must find nothing left to push"
    assert _snapshot(await _items_by_ply(db_session)) == after_first
