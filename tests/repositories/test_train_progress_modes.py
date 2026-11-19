"""Repository tests for the per-mode read model of `get_progress` (Phase 251, D-09, D-10, D-17,
D-20, D-21).

These call `train_repository.get_progress` directly with explicit `now_utc` values (the dev clock
pattern), so day boundaries are deterministic.

Coverage:
- test_mode_states_puzzles                         : off / pending / in_progress / done
- test_mode_states_blunder_check_done_points       : done day, remaining 0, points_today summed
- test_first_session_done_flags                    : per mode, any completed session ever
- test_needs_level                                 : no rated games and no stored level only
- test_notice_visible_window                       : stamp window, completed-session hide, NULL
- test_day_complete_flag                           : true once both required modes are done

Every seeded game and session is deleted in `finally` (eval lottery isolation).
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillSolve, DrillSource
from app.models.train_settings import TrainSettings
from app.repositories import train_repository
from app.services.train_scheduler import ALL_WEEKDAYS_MASK, BLUNDER_CHECK_NOTICE_DAYS
from tests.blunder_check_seed import (
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_completed_blunder_check_session,
    seed_judged_game,
)

_NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_DAY = datetime.date(2026, 11, 10)
_OLD_DAY = datetime.date(2026, 10, 1)
_PUZZLE_SIZE = 6
_BC_SIZE = 6
_BC_POINTS = 7
_SEED_PLAYOUT_PLIES = 61
_SEED_FLAT_CP = 0


def _maker(test_engine) -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _set_settings(test_engine, user_id: int, **values: object) -> None:
    """Create the settings row if needed, then set UTC plus the given columns."""
    base: dict[str, object] = {
        "timezone": "UTC",
        "weekday_mask": ALL_WEEKDAYS_MASK,
        "puzzles_per_session": _PUZZLE_SIZE,
        "blunder_check_per_session": _BC_SIZE,
    }
    base.update(values)
    async with _maker(test_engine)() as session, session.begin():
        await train_repository.get_or_create_settings(session, user_id=user_id)
        await session.execute(
            update(TrainSettings).where(TrainSettings.user_id == user_id).values(**base)
        )


async def _modes(test_engine, user_id: int, now: datetime.datetime = _NOW):
    async with _maker(test_engine)() as session, session.begin():
        return await train_repository.get_progress(session, user_id=user_id, now_utc=now)


async def _seed_puzzle_session(
    test_engine, user_id: int, *, day: datetime.date, status: str, solved: int = 0
) -> int:
    """A drill session on `day` with `_PUZZLE_SIZE` sharp-filler rows, `solved` of them solved."""
    solved_at = datetime.datetime.combine(day, datetime.time(12), datetime.timezone.utc)
    async with _maker(test_engine)() as session, session.begin():
        row = DrillSession(
            user_id=user_id,
            session_date=day,
            status=status,
            puzzle_count=_PUZZLE_SIZE,
            expires_on=day + datetime.timedelta(days=1),
            completed_at=solved_at if status == "completed" else None,
        )
        session.add(row)
        await session.flush()
        for position in range(_PUZZLE_SIZE):
            session.add(
                DrillSolve(
                    session_id=row.id,
                    position=position,
                    user_id=user_id,
                    game_id=None,
                    ply=position,
                    source=int(DrillSource.SHARP_FILLER),
                    sharp_puzzle_id=f"sharp-progress-{position}",
                    solved_at=solved_at if position < solved else None,
                )
            )
        return row.id


async def _delete_drill_sessions(test_engine, ids: list[int]) -> None:
    if not ids:
        return
    async with _maker(test_engine)() as session, session.begin():
        await session.execute(delete(DrillSession).where(DrillSession.id.in_(ids)))


@pytest.mark.asyncio
async def test_mode_states_puzzles(test_engine) -> None:
    """off at size 0; pending with nothing started; in_progress with 1 of 6 solved; done after."""
    user_id, _ = await register_user("modes-repo-puz", beta=False, test_engine=test_engine)
    await _set_settings(test_engine, user_id)
    drill_ids: list[int] = []
    try:
        assert (await _modes(test_engine, user_id)).modes.puzzles.state == "pending"

        open_id = await _seed_puzzle_session(
            test_engine, user_id, day=_DAY, status="open", solved=1
        )
        drill_ids.append(open_id)
        puzzles = (await _modes(test_engine, user_id)).modes.puzzles
        assert puzzles.state == "in_progress"
        assert puzzles.remaining == _PUZZLE_SIZE - 1

        await _delete_drill_sessions(test_engine, [open_id])
        drill_ids.clear()
        drill_ids.append(
            await _seed_puzzle_session(
                test_engine, user_id, day=_DAY, status="completed", solved=_PUZZLE_SIZE
            )
        )
        done = (await _modes(test_engine, user_id)).modes.puzzles
        assert done.state == "done"
        assert done.remaining == 0
        assert done.pending == 0

        await _set_settings(test_engine, user_id, puzzles_per_session=0)
        off = (await _modes(test_engine, user_id)).modes.puzzles
        assert off.state == "off"
        assert off.size == 0
        assert off.pending == 0
    finally:
        await _delete_drill_sessions(test_engine, drill_ids)


@pytest.mark.asyncio
async def test_mode_states_blunder_check_done_points(test_engine) -> None:
    """A completed session today: done, nothing remaining or pending, points_today summed."""
    user_id, _ = await register_user("modes-repo-bcdone", beta=False, test_engine=test_engine)
    await _set_settings(test_engine, user_id)
    session_id = await seed_completed_blunder_check_session(
        test_engine, user_id=user_id, session_date=_DAY, points=_BC_POINTS
    )
    try:
        bc = (await _modes(test_engine, user_id)).modes.blunder_check
        assert bc.state == "done"
        assert bc.remaining == 0
        assert bc.pending == 0
        assert bc.points_today == _BC_POINTS
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_first_session_done_flags(test_engine) -> None:
    """False for a new user in both modes; true per mode once any session of it completed."""
    user_id, _ = await register_user("modes-repo-first", beta=False, test_engine=test_engine)
    await _set_settings(test_engine, user_id)
    drill_ids: list[int] = []
    bc_ids: list[int] = []
    try:
        fresh = (await _modes(test_engine, user_id)).modes
        assert fresh.puzzles.first_session_done is False
        assert fresh.blunder_check.first_session_done is False

        # An old completed session (long outside today's window) still counts as "ever".
        drill_ids.append(
            await _seed_puzzle_session(
                test_engine, user_id, day=_OLD_DAY, status="completed", solved=_PUZZLE_SIZE
            )
        )
        after_puzzles = (await _modes(test_engine, user_id)).modes
        assert after_puzzles.puzzles.first_session_done is True
        assert after_puzzles.blunder_check.first_session_done is False

        bc_ids.append(
            await seed_completed_blunder_check_session(
                test_engine, user_id=user_id, session_date=_OLD_DAY, points=1
            )
        )
        after_bc = (await _modes(test_engine, user_id)).modes
        assert after_bc.blunder_check.first_session_done is True
    finally:
        await _delete_drill_sessions(test_engine, drill_ids)
        await delete_blunder_check_sessions(test_engine, bc_ids)


@pytest.mark.asyncio
async def test_needs_level(test_engine) -> None:
    """needs_level only without rated games and without a stored level (D-17, D-20)."""
    user_id, _ = await register_user("modes-repo-level", beta=False, test_engine=test_engine)
    await _set_settings(test_engine, user_id)
    game_ids: list[int] = []
    try:
        bare = (await _modes(test_engine, user_id)).modes.blunder_check
        assert bare.has_rated_games is False
        assert bare.needs_level is True

        await _set_settings(test_engine, user_id, blunder_check_level="intermediate")
        chosen = (await _modes(test_engine, user_id)).modes.blunder_check
        assert chosen.has_rated_games is False
        assert chosen.needs_level is False

        await _set_settings(test_engine, user_id, blunder_check_level=None)
        game_ids.append(
            await seed_judged_game(
                test_engine,
                user_id=user_id,
                evals_cp=flat_evals(_SEED_PLAYOUT_PLIES, _SEED_FLAT_CP),
                blunders=[],
            )
        )
        rated = (await _modes(test_engine, user_id)).modes.blunder_check
        assert rated.has_rated_games is True
        assert rated.needs_level is False
    finally:
        await delete_games(test_engine, game_ids)


@pytest.mark.asyncio
async def test_notice_visible_window(test_engine) -> None:
    """D-21: visible inside BLUNDER_CHECK_NOTICE_DAYS of the stamp, hidden after the window or
    once a blunder-check session completed after the stamp; a NULL stamp never shows it."""
    user_id, _ = await register_user("modes-repo-notice", beta=False, test_engine=test_engine)
    stamp = _NOW - datetime.timedelta(days=1)
    await _set_settings(test_engine, user_id, blunder_check_notice_from=stamp)
    bc_ids: list[int] = []
    try:
        assert (await _modes(test_engine, user_id)).blunder_check_notice is True

        edge = stamp + datetime.timedelta(days=BLUNDER_CHECK_NOTICE_DAYS)
        before_edge = edge - datetime.timedelta(minutes=1)
        assert (await _modes(test_engine, user_id, before_edge)).blunder_check_notice is True
        assert (await _modes(test_engine, user_id, edge)).blunder_check_notice is False

        # A session completed BEFORE the stamp does not hide it; one completed after does.
        bc_ids.append(
            await seed_completed_blunder_check_session(
                test_engine, user_id=user_id, session_date=_OLD_DAY, points=1
            )
        )
        assert (await _modes(test_engine, user_id)).blunder_check_notice is True
        bc_ids.append(
            await seed_completed_blunder_check_session(
                test_engine, user_id=user_id, session_date=_DAY, points=1
            )
        )
        assert (await _modes(test_engine, user_id)).blunder_check_notice is False

        await _set_settings(test_engine, user_id, blunder_check_notice_from=None)
        assert (await _modes(test_engine, user_id)).blunder_check_notice is False
    finally:
        await delete_blunder_check_sessions(test_engine, bc_ids)


@pytest.mark.asyncio
async def test_day_complete_flag(test_engine) -> None:
    """day_complete flips to true only when both required modes are done today."""
    user_id, _ = await register_user("modes-repo-daycomplete", beta=False, test_engine=test_engine)
    await _set_settings(test_engine, user_id)
    drill_ids: list[int] = []
    bc_ids: list[int] = []
    try:
        assert (await _modes(test_engine, user_id)).day_complete is False
        drill_ids.append(
            await _seed_puzzle_session(
                test_engine, user_id, day=_DAY, status="completed", solved=_PUZZLE_SIZE
            )
        )
        assert (await _modes(test_engine, user_id)).day_complete is False
        bc_ids.append(
            await seed_completed_blunder_check_session(
                test_engine, user_id=user_id, session_date=_DAY, points=1
            )
        )
        assert (await _modes(test_engine, user_id)).day_complete is True
    finally:
        await _delete_drill_sessions(test_engine, drill_ids)
        await delete_blunder_check_sessions(test_engine, bc_ids)
