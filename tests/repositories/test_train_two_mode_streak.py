"""Repository/service tests for the both-modes streak rule (Phase 251, D-02, D-18).

These drive the repository and service functions directly with explicit `now_utc` values (the
dev clock pattern), so day boundaries are deterministic. Rows are committed through
`test_engine` because `finish_session` and `apply_day_completion` run in their own transactions.

Coverage:
- test_day_completion_bc_finish_ticks_when_puzzles_done : puzzles done, then the blunder-check
  finish credits the day once; a repeated finish is a no-op

The launch-day matrix (CONTEXT Specifics, the D-18 rehearsal substitute, no prod rehearsal
exists):
- test_double_credit_raise_bc_after_puzzles_done : a second completion event for a credited day
  mints no extra freeze (streak_credited_on)
- test_settled_before_launch_day_stays_judged    : days before blunder_check_streak_from keep the
  puzzle-only rule and still count in current_week_completed
- test_streak_holder_launch_day_needs_both       : a holder who does puzzles only on launch day
  loses a freeze when the window closes
- test_off_day_credit_only_needs_both_modes      : an off-day freeze credit also needs both modes
- test_pool_eligible_bc_no_puzzle_material       : a blunder-check-only user gets the eligibility
  watermark stamped, so scheduled days are judged instead of resolving neutral

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
from app.services.train_scheduler import ALL_WEEKDAYS_MASK
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
    weekday_mask: int = ALL_WEEKDAYS_MASK,
) -> None:
    """A streak holder settled through yesterday, eligible since yesterday, UTC (default: every
    day scheduled)."""
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
                weekday_mask=weekday_mask,
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


async def _credit_puzzles_only_day(test_engine, user_id: int, day: datetime.date) -> bool:
    """The puzzle completion event for `day`: seed the completed session, run the eager path."""
    await _seed_completed_puzzle_session(test_engine, user_id, day)
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        return await train_repository.apply_day_completion(
            session, user_id=user_id, day=day, now_utc=_NOW
        )


async def _purge(test_engine, user_id: int, bc_ids: list[int]) -> None:
    maker = _maker(test_engine)
    async with maker() as session, session.begin():
        await session.execute(delete(DrillSession).where(DrillSession.user_id == user_id))
    await delete_blunder_check_sessions(test_engine, bc_ids)


@pytest.mark.asyncio
async def test_double_credit_raise_bc_after_puzzles_done(test_engine) -> None:
    """Blunder check at 0, puzzles done (credited); raising it to 6 and finishing a blunder-check
    session the same day must not mint a second freeze: `streak_credited_on` is the key."""
    user_id, _ = await register_user("two-mode-double", beta=True, test_engine=test_engine)
    await _seed_holder(test_engine, user_id, bc_size=0)
    bc_ids: list[int] = []
    try:
        assert await _credit_puzzles_only_day(test_engine, user_id, _DAY) is True
        after_puzzles = await _read_row(test_engine, user_id)
        assert after_puzzles.streak_count == _STARTING_STREAK + 1
        assert after_puzzles.shield_level == _STARTING_SHIELD + 1
        assert after_puzzles.streak_credited_on == _DAY

        maker = _maker(test_engine)
        async with maker() as session, session.begin():
            await session.execute(
                update(TrainSettings)
                .where(TrainSettings.user_id == user_id)
                .values(blunder_check_per_session=_BC_SIZE)
            )
        bc_ids.append(await _seed_open_finished_bc_session(test_engine, user_id, _DAY))
        await _finish(test_engine, user_id, bc_ids[0])

        after_bc = await _read_row(test_engine, user_id)
        assert after_bc.streak_count == after_puzzles.streak_count
        assert after_bc.shield_level == after_puzzles.shield_level
    finally:
        await _purge(test_engine, user_id, bc_ids)


@pytest.mark.asyncio
async def test_settled_before_launch_day_stays_judged(test_engine) -> None:
    """D-18: a puzzle-only day before the launch day stays fulfilled and keeps counting in the
    week caption; a puzzle-only day on or after it does not (blunder check is required)."""
    user_id, _ = await register_user("two-mode-prelaunch", beta=True, test_engine=test_engine)
    await _seed_holder(test_engine, user_id, streak_from=_DAY)
    await _seed_completed_puzzle_session(test_engine, user_id, _YESTERDAY)
    await _seed_completed_puzzle_session(test_engine, user_id, _DAY)
    try:
        maker = _maker(test_engine)
        async with maker() as session, session.begin():
            progress = await train_repository.get_progress(session, user_id=user_id, now_utc=_NOW)
        # 2026-11-09 (Mon) counts under the old rule; 2026-11-10 (Tue, launch day) does not.
        assert progress.current_week_completed == 1
        assert progress.session_streak_count == _STARTING_STREAK
        assert progress.shield_level == _STARTING_SHIELD
    finally:
        await _purge(test_engine, user_id, [])


@pytest.mark.asyncio
async def test_streak_holder_launch_day_needs_both(test_engine) -> None:
    """A holder with blunder_check_streak_from = today who finishes puzzles only: no credit that
    day, and once the window closes the lazy walk judges it missed (shield -1)."""
    user_id, _ = await register_user("two-mode-launch", beta=True, test_engine=test_engine)
    await _seed_holder(test_engine, user_id, streak_from=_DAY)
    try:
        assert await _credit_puzzles_only_day(test_engine, user_id, _DAY) is False
        assert (await _read_row(test_engine, user_id)).streak_count == _STARTING_STREAK

        next_day = _NOW + datetime.timedelta(days=1)
        maker = _maker(test_engine)
        async with maker() as session, session.begin():
            progress = await train_repository.get_progress(
                session, user_id=user_id, now_utc=next_day
            )
        assert progress.shield_level == _STARTING_SHIELD - 1
        assert progress.session_streak_count == _STARTING_STREAK
    finally:
        await _purge(test_engine, user_id, [])


@pytest.mark.asyncio
async def test_off_day_credit_only_needs_both_modes(test_engine) -> None:
    """On an unscheduled day, puzzles alone credit nothing while blunder check is at 6; the
    blunder-check finish then credits exactly one freeze and leaves the streak count alone."""
    tuesday_off_mask = ALL_WEEKDAYS_MASK & ~(1 << _DAY.weekday())
    user_id, _ = await register_user("two-mode-offday", beta=True, test_engine=test_engine)
    await _seed_holder(test_engine, user_id, weekday_mask=tuesday_off_mask)
    bc_ids: list[int] = []
    try:
        assert await _credit_puzzles_only_day(test_engine, user_id, _DAY) is False
        assert (await _read_row(test_engine, user_id)).shield_level == _STARTING_SHIELD

        bc_ids.append(await _seed_open_finished_bc_session(test_engine, user_id, _DAY))
        await _finish(test_engine, user_id, bc_ids[0])

        row = await _read_row(test_engine, user_id)
        assert row.shield_level == _STARTING_SHIELD + 1
        assert row.streak_count == _STARTING_STREAK
        assert row.streak_settled_through == _YESTERDAY
        assert row.streak_credited_on == _DAY
    finally:
        await _purge(test_engine, user_id, bc_ids)


@pytest.mark.asyncio
async def test_pool_eligible_bc_no_puzzle_material(fresh_test_user, db_session) -> None:
    """No drill items and no pool candidates: blunder check on stamps the eligibility watermark
    (it always has foreign supply); blunder check off leaves it NULL."""
    user_id = fresh_test_user.id
    await train_repository.get_or_create_settings(db_session, user_id=user_id)
    await train_repository.get_progress(db_session, user_id=user_id, now_utc=_NOW)
    row = (
        await db_session.execute(select(TrainSettings).where(TrainSettings.user_id == user_id))
    ).scalar_one()
    assert row.pool_eligible_since == _DAY

    await db_session.execute(
        update(TrainSettings)
        .where(TrainSettings.user_id == user_id)
        .values(pool_eligible_since=None, blunder_check_per_session=0)
    )
    await db_session.flush()
    db_session.expire_all()
    await train_repository.get_progress(db_session, user_id=user_id, now_utc=_NOW)
    off_row = (
        await db_session.execute(select(TrainSettings).where(TrainSettings.user_id == user_id))
    ).scalar_one()
    assert off_row.pool_eligible_since is None
