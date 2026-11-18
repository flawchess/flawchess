"""Repository/service tests for the both-modes streak rule (Phase 251, D-02, D-18).

These drive the repository and service functions directly with explicit `now_utc` values (the
dev clock pattern), so day boundaries are deterministic. Rows are committed through
`test_engine` because `finish_session` and `apply_day_completion` run in their own transactions.

Coverage:
- test_day_completion_bc_finish_ticks_when_puzzles_done : puzzles done, then the blunder-check
  finish credits the day once; a repeated finish is a no-op

Every seeded game and session is deleted in `finally` (eval lottery isolation).
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.drill_session import DrillSession
from app.models.train_settings import TrainSettings
from app.repositories import train_repository
from app.services import blunder_check_service
from tests.blunder_check_seed import delete_blunder_check_sessions, register_user

_NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_DAY = datetime.date(2026, 11, 10)
_YESTERDAY = datetime.date(2026, 11, 9)
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_STARTING_STREAK = 3
_STARTING_SHIELD = 2
_BC_SIZE = 6
_WINDOW_POINTS = 3


def _maker(test_engine) -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed_holder(
    test_engine,
    user_id: int,
    *,
    bc_size: int = _BC_SIZE,
    streak_from: datetime.date | None = None,
    puzzles_per_session: int = 6,
) -> None:
    """A streak holder settled through yesterday, eligible since yesterday, UTC, every day scheduled."""
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        await train_repository.get_or_create_settings(session, user_id=user_id)
        await session.execute(
            update(TrainSettings)
            .where(TrainSettings.user_id == user_id)
            .values(
                streak_count=_STARTING_STREAK,
                shield_level=_STARTING_SHIELD,
                streak_settled_through=_YESTERDAY,
                pool_eligible_since=_YESTERDAY,
                blunder_check_per_session=bc_size,
                blunder_check_streak_from=streak_from,
                puzzles_per_session=puzzles_per_session,
            )
        )


async def _seed_completed_puzzle_session(test_engine, user_id: int, day: datetime.date) -> int:
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        row = DrillSession(
            user_id=user_id,
            session_date=day,
            status="completed",
            puzzle_count=1,
            expires_on=day + datetime.timedelta(days=1),
            completed_at=datetime.datetime.combine(day, datetime.time(12), datetime.timezone.utc),
        )
        session.add(row)
        await session.flush()
        return row.id


async def _seed_open_finished_bc_session(test_engine, user_id: int, day: datetime.date) -> int:
    """An OPEN blunder-check session dated `day` whose only window is already ended, so
    `finish_session` can complete it."""
    instant = datetime.datetime.combine(day, datetime.time(12), datetime.timezone.utc)
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        header = BlunderCheckSession(
            user_id=user_id,
            status="open",
            window_count=1,
            started_at=instant,
            session_date=day,
            expires_on=day + datetime.timedelta(days=1),
        )
        session.add(header)
        await session.flush()
        session.add(
            BlunderCheckWindow(
                session_id=header.id,
                position=0,
                user_id=user_id,
                game_id=None,
                is_own=True,
                window_length=3,
                blunder_position=None,
                first_ply=10,
                blunder_ply=None,
                window_case=int(WindowCase.HERRING),
                start_fen=_START_FEN,
                move_ucis="e2e4 e7e5 g1f3",
                lead_in_plies=0,
                points_possible=_WINDOW_POINTS,
                points_scored=_WINDOW_POINTS,
                outcome=int(WindowOutcome.CLEARED),
                started_at=instant,
                ended_at=instant,
            )
        )
        return header.id


async def _read_row(test_engine, user_id: int) -> TrainSettings:
    maker = _maker(test_engine)
    async with maker() as session:
        return (
            await session.execute(select(TrainSettings).where(TrainSettings.user_id == user_id))
        ).scalar_one()


async def _delete_drill_sessions(test_engine, ids: list[int]) -> None:
    if not ids:
        return
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        await session.execute(delete(DrillSession).where(DrillSession.id.in_(ids)))


async def _finish(test_engine, user_id: int, session_id: int) -> None:
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        await blunder_check_service.finish_session(
            session, user_id=user_id, session_id=session_id, now_utc=_NOW
        )


@pytest.mark.asyncio
async def test_day_completion_bc_finish_ticks_when_puzzles_done(test_engine) -> None:
    """Puzzles done, then the blunder-check finish credits the day once; a repeat is a no-op."""
    user_id, _ = await register_user("two-mode-finish", beta=True, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    drill_ids = [await _seed_completed_puzzle_session(test_engine, user_id, _DAY)]
    bc_ids = [await _seed_open_finished_bc_session(test_engine, user_id, _DAY)]
    try:
        # The puzzle completion event runs first: blunder check is still pending, so no credit.
        maker = _maker(test_engine)
        async with maker() as session, session.begin():
            credited = await train_repository.apply_day_completion(
                session, user_id=user_id, day=_DAY, now_utc=_NOW
            )
        assert credited is False
        assert (await _read_row(test_engine, user_id)).streak_count == _STARTING_STREAK

        await _finish(test_engine, user_id, bc_ids[0])
        row = await _read_row(test_engine, user_id)
        assert row.streak_count == _STARTING_STREAK + 1
        assert row.shield_level == _STARTING_SHIELD + 1
        assert row.streak_credited_on == _DAY

        # A second finish call (complete_session now reports False) credits nothing more.
        await _finish(test_engine, user_id, bc_ids[0])
        again = await _read_row(test_engine, user_id)
        assert again.streak_count == _STARTING_STREAK + 1
        assert again.shield_level == _STARTING_SHIELD + 1
    finally:
        await _delete_drill_sessions(test_engine, drill_ids)
        await delete_blunder_check_sessions(test_engine, bc_ids)
