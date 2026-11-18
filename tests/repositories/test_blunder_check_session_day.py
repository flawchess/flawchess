"""Repository tests for the blunder-check session day (Phase 251, D-01 / D-02).

Coverage:
- test_bc_session_dated_local_today       : insert_session writes the day and expiry it is given
- test_bc_expire_deletes_only_unstarted_windows : expiry keeps shown windows (D-01, A9)
- test_bc_open_session_ignores_expired    : the read path skips an expired row and writes nothing
- test_bc_completed_in_window_returns_done_session : done session visible only inside its window
- test_bc_complete_session_true_once      : complete_session reports whether it moved the row
- test_bc_get_session_date_scoped_to_user : a foreign session id resolves to nothing (T-251-02)

Every seeded game and session is deleted in `finally` (eval lottery isolation).
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.blunder_check import BlunderCheckSession, BlunderCheckWindow, WindowCase
from app.repositories import blunder_check_repository as repo
from app.repositories.blunder_check_repository import NewWindow
from tests.blunder_check_seed import (
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_completed_blunder_check_session,
    seed_judged_game,
    with_user_blunder,
)

_NOW = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_DAY = datetime.date(2026, 11, 10)
_NEXT_DAY = datetime.date(2026, 11, 11)
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_ROWS = 60
_BLUNDER_PLY = 20
_BLUNDER_DROP_CP = 500
_SEEDED_POINTS = 5
_WINDOW_COUNT = 3


def _maker(test_engine) -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


def _new_window(game_id: int, position: int) -> NewWindow:
    return NewWindow(
        position=position,
        game_id=game_id,
        is_own=True,
        window_length=3,
        blunder_position=2,
        first_ply=_BLUNDER_PLY - 2,
        blunder_ply=_BLUNDER_PLY,
        window_case=WindowCase.ALLOWED,
        mover_elo=1500,
        start_fen=_START_FEN,
        move_ucis="e2e4 e7e5 g1f3",
        lead_in_plies=0,
        key_uci="d2d4",
        refutation_uci="e7e5",
        points_possible=3,
    )


async def _open_session_with_windows(
    test_engine, user_id: int, *, expires_on: datetime.date, started: list[bool]
) -> int:
    """An open session dated _DAY whose windows are shown (True) or never started (False)."""
    maker = _maker(test_engine)
    async with maker() as session:
        async with session.begin():
            header = BlunderCheckSession(
                user_id=user_id,
                status="open",
                window_count=len(started),
                started_at=_NOW,
                session_date=_DAY,
                expires_on=expires_on,
            )
            session.add(header)
            await session.flush()
            for position, was_shown in enumerate(started):
                session.add(
                    BlunderCheckWindow(
                        session_id=header.id,
                        position=position,
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
                        points_possible=3,
                        started_at=_NOW if was_shown else None,
                    )
                )
            return header.id


async def _status_of(test_engine, session_id: int) -> str:
    async with _maker(test_engine)() as session:
        return (
            await session.execute(
                select(BlunderCheckSession.status).where(BlunderCheckSession.id == session_id)
            )
        ).scalar_one()


async def _window_positions(test_engine, session_id: int) -> list[int]:
    async with _maker(test_engine)() as session:
        rows = await session.execute(
            select(BlunderCheckWindow.position)
            .where(BlunderCheckWindow.session_id == session_id)
            .order_by(BlunderCheckWindow.position)
        )
        return list(rows.scalars())


@pytest.mark.asyncio
async def test_bc_session_dated_local_today(test_engine) -> None:
    user_id, _ = await register_user("bc-day-insert", beta=True, test_engine=test_engine)
    game_id = await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=with_user_blunder(flat_evals(_ROWS, 0), _BLUNDER_PLY, _BLUNDER_DROP_CP),
        blunders=[SeedBlunder(ply=_BLUNDER_PLY)],
    )
    session_id: int | None = None
    try:
        async with _maker(test_engine)() as session:
            async with session.begin():
                session_id = await repo.insert_session(
                    session,
                    user_id=user_id,
                    windows=[_new_window(game_id, 0)],
                    now_utc=_NOW,
                    session_date=_DAY,
                    expires_on=_NEXT_DAY,
                )
        assert session_id is not None
        async with _maker(test_engine)() as session:
            header = (
                await session.execute(
                    select(BlunderCheckSession).where(BlunderCheckSession.id == session_id)
                )
            ).scalar_one()
        assert header.session_date == _DAY
        assert header.expires_on == _NEXT_DAY
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [game_id])


@pytest.mark.asyncio
async def test_bc_expire_deletes_only_unstarted_windows(test_engine) -> None:
    user_id, _ = await register_user("bc-day-expire", beta=True, test_engine=test_engine)
    session_id = await _open_session_with_windows(
        test_engine, user_id, expires_on=_NEXT_DAY, started=[True, False, False]
    )
    try:
        async with _maker(test_engine)() as session:
            async with session.begin():
                await repo.expire_stale_sessions(session, user_id=user_id, today=_NEXT_DAY)
        assert await _status_of(test_engine, session_id) == "expired"
        # Only the shown window stays stored (D-01); never-shown ones return to the pool (A9).
        assert await _window_positions(test_engine, session_id) == [0]
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_bc_open_session_ignores_expired(test_engine) -> None:
    user_id, _ = await register_user("bc-day-open", beta=True, test_engine=test_engine)
    session_id = await _open_session_with_windows(
        test_engine, user_id, expires_on=_NEXT_DAY, started=[False, False]
    )
    try:
        async with _maker(test_engine)() as session:
            expired = await repo.open_session_progress(session, user_id=user_id, today=_NEXT_DAY)
            current = await repo.open_session_progress(session, user_id=user_id, today=_DAY)
        assert expired is None
        assert current is not None and current.session_id == session_id
        # The read path never writes: the row is still open with all its windows.
        assert await _status_of(test_engine, session_id) == "open"
        assert await _window_positions(test_engine, session_id) == [0, 1]
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_bc_completed_in_window_returns_done_session(test_engine) -> None:
    user_id, _ = await register_user("bc-day-done", beta=True, test_engine=test_engine)
    session_id = await seed_completed_blunder_check_session(
        test_engine, user_id=user_id, session_date=_DAY, points=_SEEDED_POINTS
    )
    try:
        async with _maker(test_engine)() as session:
            inside = await repo.completed_session_in_window(session, user_id=user_id, today=_DAY)
            after = await repo.completed_session_in_window(
                session, user_id=user_id, today=_NEXT_DAY
            )
        assert inside is not None
        assert inside.session_id == session_id
        assert [row.points_scored for row in inside.windows] == [_SEEDED_POINTS]
        assert after is None
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_bc_complete_session_true_once(test_engine) -> None:
    user_id, _ = await register_user("bc-day-complete", beta=True, test_engine=test_engine)
    session_id = await _open_session_with_windows(
        test_engine, user_id, expires_on=_NEXT_DAY, started=[True] * _WINDOW_COUNT
    )
    try:
        async with _maker(test_engine)() as session:
            async with session.begin():
                first = await repo.complete_session(session, session_id=session_id, now_utc=_NOW)
        async with _maker(test_engine)() as session:
            async with session.begin():
                second = await repo.complete_session(session, session_id=session_id, now_utc=_NOW)
        assert first is True
        assert second is False
        assert await _status_of(test_engine, session_id) == "completed"
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_bc_get_session_date_scoped_to_user(test_engine) -> None:
    owner_id, _ = await register_user("bc-day-owner", beta=True, test_engine=test_engine)
    other_id, _ = await register_user("bc-day-other", beta=True, test_engine=test_engine)
    session_id = await seed_completed_blunder_check_session(
        test_engine, user_id=owner_id, session_date=_DAY, points=_SEEDED_POINTS
    )
    try:
        async with _maker(test_engine)() as session:
            mine = await repo.get_session_date(session, user_id=owner_id, session_id=session_id)
            theirs = await repo.get_session_date(session, user_id=other_id, session_id=session_id)
        assert mine == _DAY
        assert theirs is None
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
