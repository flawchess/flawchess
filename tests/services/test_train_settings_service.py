"""Service tests for `apply_settings_update` (Phase 251, D-04, D-06).

These drive the service with an explicit `now_utc` (the dev-clock pattern) so day boundaries are
deterministic. Rows are committed through `test_engine` because the service and the repository
helpers run in their own transactions.

Coverage, the D-06 resize of an open blunder-check session (`-k resize`):
- test_resize_to_zero_expires_open_session         : n = 0 expires the session, keeps ended windows
- test_resize_at_or_below_done_completes           : n <= windows ended completes it now
- test_resize_keeps_started_unended_window         : a shown-but-unended window survives completion
- test_resize_shorten_keeps_open                   : ended < n < window_count shortens it
- test_resize_extend_composes_more                 : n > window_count appends freshly composed windows
- test_resize_after_completion_applies_next_session: a completed session is never reopened
- test_resize_extend_never_reserves_shown_blunder  : no extension window repeats a served blunder

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
from app.services import blunder_check_selection, blunder_check_service
from app.services.train_scheduler import ALL_WEEKDAYS_MASK
from app.services.train_settings_service import apply_settings_update
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
_NEXT_DAY_NOW = datetime.datetime(2026, 11, 11, 12, 0, tzinfo=datetime.timezone.utc)
_DAY = datetime.date(2026, 11, 10)
_YESTERDAY = datetime.date(2026, 11, 9)
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_STARTING_STREAK = 3
_STARTING_SHIELD = 2
_BC_SIZE = 6
_PUZZLES_SIZE = 6
_WINDOW_POINTS = 3
_SEED_ROWS = 61
_SEED_BLUNDER_PLY = 20
_SEED_BLUNDER_DROP_CP = 500
_SUPPLY_GAMES = 24
_FOREIGN_SUPPLY_GAMES = 16


@pytest.fixture(autouse=True)
def _full_foreign_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sample every page: a 2% TABLESAMPLE of a tiny test table would return almost nothing."""
    monkeypatch.setattr(blunder_check_selection, "FOREIGN_SAMPLE_PERCENT", 100.0)


def _maker(test_engine) -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed_holder(test_engine, user_id: int, *, bc_size: int = _BC_SIZE) -> None:
    """A streak holder settled through yesterday, eligible since yesterday, UTC, every day scheduled."""
    async with _maker(test_engine)() as session, session.begin():
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
                puzzles_per_session=_PUZZLES_SIZE,
                weekday_mask=ALL_WEEKDAYS_MASK,
            )
        )


async def _seed_completed_puzzle_session(test_engine, user_id: int, day: datetime.date) -> int:
    async with _maker(test_engine)() as session, session.begin():
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


async def _delete_drill_sessions(test_engine, ids: list[int]) -> None:
    if not ids:
        return
    async with _maker(test_engine)() as session, session.begin():
        await session.execute(delete(DrillSession).where(DrillSession.id.in_(ids)))


async def _seed_open_bc_session(
    test_engine,
    user_id: int,
    *,
    total: int,
    ended: int,
    game_ids: list[int] | None = None,
    started_unended: int = 0,
) -> int:
    """An open blunder-check session dated `_DAY` with `total` windows.

    The first `ended` windows are ended (CLEARED, 3 points), the next `started_unended` were
    shown but not ended, the rest were never started. With `game_ids`, window i is an own
    blunder window on `game_ids[i]` at the seed blunder ply (so the served-set lookup sees it).
    """
    instant = datetime.datetime.combine(_DAY, datetime.time(12), datetime.timezone.utc)
    async with _maker(test_engine)() as session, session.begin():
        header = BlunderCheckSession(
            user_id=user_id,
            status="open",
            window_count=total,
            started_at=instant,
            session_date=_DAY,
            expires_on=_DAY + datetime.timedelta(days=1),
        )
        session.add(header)
        await session.flush()
        for position in range(total):
            is_ended = position < ended
            is_shown = position < ended + started_unended
            with_game = game_ids is not None
            session.add(
                BlunderCheckWindow(
                    session_id=header.id,
                    position=position,
                    user_id=user_id,
                    game_id=game_ids[position] if game_ids is not None else None,
                    is_own=True,
                    window_length=3,
                    blunder_position=2 if with_game else None,
                    first_ply=_SEED_BLUNDER_PLY - 4 if with_game else 10,
                    blunder_ply=_SEED_BLUNDER_PLY if with_game else None,
                    window_case=int(WindowCase.ALLOWED if with_game else WindowCase.HERRING),
                    start_fen=_START_FEN,
                    move_ucis="e2e4 e7e5 g1f3",
                    lead_in_plies=0,
                    points_possible=_WINDOW_POINTS,
                    points_scored=_WINDOW_POINTS if is_ended else 0,
                    outcome=int(WindowOutcome.CLEARED) if is_ended else None,
                    started_at=instant if is_shown else None,
                    ended_at=instant if is_ended else None,
                )
            )
        return header.id


async def _seed_supply(test_engine, user_id: int, count: int) -> list[int]:
    """`count` own fully evaluated games, each holding one qualifying blunder at the seed ply."""
    evals = with_user_blunder(flat_evals(_SEED_ROWS, 0), _SEED_BLUNDER_PLY, _SEED_BLUNDER_DROP_CP)
    return [
        await seed_judged_game(
            test_engine,
            user_id=user_id,
            evals_cp=evals,
            blunders=[SeedBlunder(ply=_SEED_BLUNDER_PLY)],
        )
        for _ in range(count)
    ]


async def _seed_full_supply(test_engine, user_id: int) -> list[int]:
    """Own games plus another user's games, so every slot origin of a composition can fill.

    Without the foreign half, slots drawn as foreign stay empty and an extension composes a
    random number of windows.
    """
    foreign_id, _ = await register_user("resize-foreign", beta=False, test_engine=test_engine)
    own = await _seed_supply(test_engine, user_id, _SUPPLY_GAMES)
    foreign = await _seed_supply(test_engine, foreign_id, _FOREIGN_SUPPLY_GAMES)
    return own + foreign


async def _apply(
    test_engine,
    user_id: int,
    *,
    bc_size: int | None,
    puzzles: int = _PUZZLES_SIZE,
    now: datetime.datetime = _NOW,
) -> None:
    async with _maker(test_engine)() as session, session.begin():
        await apply_settings_update(
            session,
            user_id=user_id,
            timezone="UTC",
            weekday_mask=ALL_WEEKDAYS_MASK,
            puzzles_per_session=puzzles,
            blunder_check_per_session=bc_size,
            blunder_check_level=None,
            reminder_enabled=False,
            reminder_hour=18,
            reminder_intent_at=None,
            now_utc=now,
        )


async def _header(test_engine, session_id: int) -> BlunderCheckSession:
    async with _maker(test_engine)() as session:
        return (
            await session.execute(
                select(BlunderCheckSession).where(BlunderCheckSession.id == session_id)
            )
        ).scalar_one()


async def _windows(test_engine, session_id: int) -> list[BlunderCheckWindow]:
    async with _maker(test_engine)() as session:
        return list(
            (
                await session.execute(
                    select(BlunderCheckWindow)
                    .where(BlunderCheckWindow.session_id == session_id)
                    .order_by(BlunderCheckWindow.position)
                )
            )
            .scalars()
            .all()
        )


async def _settings(test_engine, user_id: int) -> TrainSettings:
    async with _maker(test_engine)() as session:
        return (
            await session.execute(select(TrainSettings).where(TrainSettings.user_id == user_id))
        ).scalar_one()


@pytest.mark.asyncio
async def test_resize_to_zero_expires_open_session(test_engine) -> None:
    """n = 0 expires the open session, drops never-started windows, keeps ended ones and ticks."""
    user_id, _ = await register_user("resize-zero", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    drill_ids = [await _seed_completed_puzzle_session(test_engine, user_id, _DAY)]
    session_id = await _seed_open_bc_session(test_engine, user_id, total=6, ended=2)
    try:
        await _apply(test_engine, user_id, bc_size=0)

        assert (await _header(test_engine, session_id)).status == "expired"
        windows = await _windows(test_engine, session_id)
        assert [w.position for w in windows] == [0, 1]
        assert sum(w.points_scored for w in windows) == 2 * _WINDOW_POINTS
        row = await _settings(test_engine, user_id)
        assert row.streak_count == _STARTING_STREAK + 1
        assert row.streak_credited_on == _DAY
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await _delete_drill_sessions(test_engine, drill_ids)


@pytest.mark.asyncio
async def test_resize_at_or_below_done_completes(test_engine) -> None:
    """2 of 6 windows ended and n = 2: the session completes now and the day credits once."""
    user_id, _ = await register_user("resize-done", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    drill_ids = [await _seed_completed_puzzle_session(test_engine, user_id, _DAY)]
    session_id = await _seed_open_bc_session(test_engine, user_id, total=6, ended=2)
    try:
        await _apply(test_engine, user_id, bc_size=2)

        header = await _header(test_engine, session_id)
        assert header.status == "completed"
        assert header.completed_at is not None
        windows = await _windows(test_engine, session_id)
        assert [w.position for w in windows] == [0, 1]
        assert header.window_count == len(windows)
        row = await _settings(test_engine, user_id)
        assert row.streak_count == _STARTING_STREAK + 1
        assert row.streak_credited_on == _DAY

        # The same PUT again changes nothing and never credits a second time.
        await _apply(test_engine, user_id, bc_size=2)
        again = await _settings(test_engine, user_id)
        assert again.streak_count == _STARTING_STREAK + 1
        assert again.shield_level == row.shield_level
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await _delete_drill_sessions(test_engine, drill_ids)


@pytest.mark.asyncio
async def test_resize_keeps_started_unended_window(test_engine) -> None:
    """A window that was shown but not ended stays stored (D-01) when the session completes."""
    user_id, _ = await register_user("resize-shown", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    session_id = await _seed_open_bc_session(
        test_engine, user_id, total=6, ended=2, started_unended=1
    )
    try:
        await _apply(test_engine, user_id, bc_size=2)

        header = await _header(test_engine, session_id)
        assert header.status == "completed"
        windows = await _windows(test_engine, session_id)
        assert [w.position for w in windows] == [0, 1, 2]
        assert header.window_count == 3
        # The abandoned window never got an outcome or points.
        assert windows[2].outcome is None
        assert windows[2].points_scored == 0
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_resize_shorten_keeps_open(test_engine) -> None:
    """2 ended of 6 and n = 4: still open, windows at position >= 4 deleted, window_count 4."""
    user_id, _ = await register_user("resize-short", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    session_id = await _seed_open_bc_session(test_engine, user_id, total=6, ended=2)
    try:
        await _apply(test_engine, user_id, bc_size=4)

        header = await _header(test_engine, session_id)
        assert header.status == "open"
        assert header.window_count == 4
        assert [w.position for w in await _windows(test_engine, session_id)] == [0, 1, 2, 3]
        assert (await _settings(test_engine, user_id)).streak_count == _STARTING_STREAK
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_resize_extend_composes_more(test_engine) -> None:
    """2 ended of 6 and n = 9: three new windows at positions 6, 7, 8; window_count 9."""
    user_id, _ = await register_user("resize-extend", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    all_game_ids = await _seed_full_supply(test_engine, user_id)
    game_ids = all_game_ids[:_SUPPLY_GAMES]
    session_id = await _seed_open_bc_session(
        test_engine, user_id, total=6, ended=2, game_ids=game_ids[:6]
    )
    try:
        await _apply(test_engine, user_id, bc_size=9)

        header = await _header(test_engine, session_id)
        assert header.status == "open"
        windows = await _windows(test_engine, session_id)
        assert [w.position for w in windows] == list(range(9))
        assert header.window_count == 9
        # The three appended windows are never-started and carry real game ids.
        for window in windows[6:]:
            assert window.started_at is None
            assert window.outcome is None
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, all_game_ids)


@pytest.mark.asyncio
async def test_resize_extend_never_reserves_shown_blunder(test_engine) -> None:
    """D-01: no extension window repeats a (game_id, blunder_ply) already in a window of the user."""
    user_id, _ = await register_user("resize-serve", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    all_game_ids = await _seed_full_supply(test_engine, user_id)
    game_ids = all_game_ids[:_SUPPLY_GAMES]
    session_id = await _seed_open_bc_session(
        test_engine, user_id, total=6, ended=4, game_ids=game_ids[:6]
    )
    try:
        await _apply(test_engine, user_id, bc_size=12)

        windows = await _windows(test_engine, session_id)
        original = {(w.game_id, w.blunder_ply) for w in windows[:6]}
        appended = [(w.game_id, w.blunder_ply) for w in windows[6:]]
        assert appended, "the extension composed nothing, so the check below proves nothing"
        assert not original & set(appended)
        # Within the extension itself no blunder repeats either.
        blunders = [pair for pair in appended if pair[1] is not None]
        assert len(blunders) == len(set(blunders))
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])
        await delete_games(test_engine, all_game_ids)


@pytest.mark.asyncio
async def test_resize_after_completion_applies_next_session(
    test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed session is never reopened; the next session composes with the new size."""
    user_id, _ = await register_user("resize-after", beta=False, test_engine=test_engine)
    await _seed_holder(test_engine, user_id)
    all_game_ids = await _seed_full_supply(test_engine, user_id)
    session_id = await seed_completed_blunder_check_session(
        test_engine, user_id=user_id, session_date=_DAY, points=_WINDOW_POINTS
    )
    new_session_ids: list[int] = []
    try:
        await _apply(test_engine, user_id, bc_size=9)

        header = await _header(test_engine, session_id)
        assert header.status == "completed"
        assert header.window_count == 1
        assert [w.position for w in await _windows(test_engine, session_id)] == [0]

        seen_counts: list[int] = []
        original = blunder_check_selection.compose_windows

        async def spy(*args: object, **kwargs: object):  # noqa: ANN202 - passthrough wrapper
            count = kwargs.get("count")
            assert isinstance(count, int)
            seen_counts.append(count)
            return await original(*args, **kwargs)  # ty: ignore[invalid-argument-type]

        monkeypatch.setattr(blunder_check_selection, "compose_windows", spy)
        async with _maker(test_engine)() as session, session.begin():
            composed = await blunder_check_service.compose_or_resume(
                session, user_id=user_id, now_utc=_NEXT_DAY_NOW
            )
        assert composed is not None
        new_session_ids.append(composed.session_id)
        assert composed.session_id != session_id
        assert seen_counts == [9]
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id, *new_session_ids])
        await delete_games(test_engine, all_game_ids)
