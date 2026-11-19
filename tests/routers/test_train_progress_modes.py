"""HTTP tests for the per-mode read model on GET /train/progress (Phase 251, D-08, D-09, D-13).

Covers:
  - test_pending_count_sums_both_modes_on_scheduled_day: a scheduled day with no sessions gives
    blunder check pending 6 / remaining 6 and `pending_count` = puzzles.pending + 6.
  - test_pending_count_blunder_check_in_progress: an open session with 2 of 6 windows ended is
    `in_progress` with remaining 4.
  - test_pending_count_unscheduled_day_without_open_session: blunder check contributes 0 to the
    badge on a day outside the weekday mask (D-13).
  - test_pending_count_unscheduled_day_with_open_session: an unfinished open session keeps its
    remaining count in the badge even off-schedule.
  - test_pending_count_off_when_blunder_check_size_zero: size 0 is `off`, contributes nothing.
  - test_notice_*: the D-21 launch notice over HTTP, its dismissal (204, idempotent) and its
    hiding after a blunder-check amount change; a new user or guest never sees it.

Every seeded blunder-check session is deleted in `finally`.
"""

from __future__ import annotations

import datetime

import httpx
import pytest
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.train_settings import TrainSettings
from app.services.train_scheduler import (
    ALL_WEEKDAYS_MASK,
    DEFAULT_BLUNDER_CHECK_PER_SESSION,
    DEFAULT_PUZZLES_PER_SESSION,
)
from tests.blunder_check_seed import (
    delete_blunder_check_sessions,
    register_user,
)

_PROGRESS = "/api/train/progress"
_SETTINGS = "/api/train/settings"
_DISMISS = "/api/train/blunder-check-notice/dismiss"
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_WINDOW_COUNT = 6
_ENDED_WINDOWS = 2
_WINDOW_LENGTH = 3
_POINTS_PER_WINDOW = 4
_SESSION_HOUR_UTC = 12


def _maker(test_engine) -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


def _today() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


async def _seed_settings(
    test_engine,
    user_id: int,
    *,
    weekday_mask: int = ALL_WEEKDAYS_MASK,
    bc_size: int = DEFAULT_BLUNDER_CHECK_PER_SESSION,
    puzzles_size: int = DEFAULT_PUZZLES_PER_SESSION,
    notice_from: datetime.datetime | None = None,
) -> None:
    """A settings row in UTC with the given schedule and sizes (progress reads it as-is)."""
    values = {
        "timezone": "UTC",
        "weekday_mask": weekday_mask,
        "puzzles_per_session": puzzles_size,
        "blunder_check_per_session": bc_size,
        "blunder_check_notice_from": notice_from,
    }
    async with _maker(test_engine)() as session, session.begin():
        await session.execute(
            pg_insert(TrainSettings)
            .values(user_id=user_id, **values)
            .on_conflict_do_update(index_elements=["user_id"], set_=values)
        )


async def _seed_open_bc_session(test_engine, user_id: int, *, ended: int, started: int) -> int:
    """An open session dated today with `_WINDOW_COUNT` windows: the first `ended` are ended
    (CLEARED, started and ended), the next ones up to `started` have only started."""
    today = _today()
    instant = datetime.datetime(
        today.year, today.month, today.day, _SESSION_HOUR_UTC, tzinfo=datetime.timezone.utc
    )
    async with _maker(test_engine)() as session, session.begin():
        header = BlunderCheckSession(
            user_id=user_id,
            status="open",
            window_count=_WINDOW_COUNT,
            started_at=instant,
            session_date=today,
            expires_on=today + datetime.timedelta(days=1),
        )
        session.add(header)
        await session.flush()
        for position in range(_WINDOW_COUNT):
            is_ended = position < ended
            is_started = position < started
            session.add(
                BlunderCheckWindow(
                    session_id=header.id,
                    position=position,
                    user_id=user_id,
                    game_id=None,
                    is_own=True,
                    window_length=_WINDOW_LENGTH,
                    blunder_position=None,
                    first_ply=10,
                    blunder_ply=None,
                    window_case=int(WindowCase.HERRING),
                    start_fen=_START_FEN,
                    move_ucis="e2e4 e7e5 g1f3",
                    lead_in_plies=0,
                    points_possible=_POINTS_PER_WINDOW,
                    points_scored=_POINTS_PER_WINDOW if is_ended else 0,
                    outcome=int(WindowOutcome.CLEARED) if is_ended else None,
                    started_at=instant if is_started else None,
                    ended_at=instant if is_ended else None,
                )
            )
        return header.id


async def _progress(token: str) -> dict[str, object]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(_PROGRESS, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def _modes(body: dict[str, object]) -> dict[str, dict[str, object]]:
    modes = body["modes"]
    assert isinstance(modes, dict)
    return modes


@pytest.mark.asyncio
async def test_pending_count_sums_both_modes_on_scheduled_day(test_engine) -> None:
    """Tracer: a scheduled day with no sessions, blunder check owes its whole size."""
    user_id, token = await register_user("modes-sum", beta=False, test_engine=test_engine)
    await _seed_settings(test_engine, user_id)
    body = await _progress(token)
    modes = _modes(body)
    bc = modes["blunder_check"]
    assert bc["state"] == "pending"
    assert bc["remaining"] == DEFAULT_BLUNDER_CHECK_PER_SESSION
    assert bc["pending"] == DEFAULT_BLUNDER_CHECK_PER_SESSION
    puzzles = modes["puzzles"]
    assert body["pending_count"] == puzzles["pending"] + DEFAULT_BLUNDER_CHECK_PER_SESSION  # ty: ignore[unsupported-operator]
    assert body["day_complete"] is False
    assert body["blunder_check_notice"] is False


@pytest.mark.asyncio
async def test_pending_count_blunder_check_in_progress(test_engine) -> None:
    """Two of six windows ended: in_progress, remaining 4, and the badge follows it."""
    user_id, token = await register_user("modes-prog", beta=False, test_engine=test_engine)
    await _seed_settings(test_engine, user_id)
    session_id = await _seed_open_bc_session(
        test_engine, user_id, ended=_ENDED_WINDOWS, started=_ENDED_WINDOWS
    )
    try:
        body = await _progress(token)
        bc = _modes(body)["blunder_check"]
        assert bc["state"] == "in_progress"
        assert bc["remaining"] == _WINDOW_COUNT - _ENDED_WINDOWS
        assert bc["pending"] == _WINDOW_COUNT - _ENDED_WINDOWS
        puzzles = _modes(body)["puzzles"]
        assert body["pending_count"] == puzzles["pending"] + _WINDOW_COUNT - _ENDED_WINDOWS  # ty: ignore[unsupported-operator]
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_pending_count_unscheduled_day_without_open_session(test_engine) -> None:
    """D-13: off the weekday mask with nothing open, blunder check adds nothing to the badge."""
    user_id, token = await register_user("modes-off-day", beta=False, test_engine=test_engine)
    off_mask = ALL_WEEKDAYS_MASK & ~(1 << _today().weekday())
    await _seed_settings(test_engine, user_id, weekday_mask=off_mask)
    body = await _progress(token)
    bc = _modes(body)["blunder_check"]
    assert bc["state"] == "pending"
    assert bc["pending"] == 0
    assert body["pending_count"] == _modes(body)["puzzles"]["pending"]


@pytest.mark.asyncio
async def test_pending_count_unscheduled_day_with_open_session(test_engine) -> None:
    """An unfinished open session off-schedule keeps counting (it can still be rescued)."""
    user_id, token = await register_user("modes-off-open", beta=False, test_engine=test_engine)
    off_mask = ALL_WEEKDAYS_MASK & ~(1 << _today().weekday())
    await _seed_settings(test_engine, user_id, weekday_mask=off_mask)
    session_id = await _seed_open_bc_session(
        test_engine, user_id, ended=_ENDED_WINDOWS, started=_ENDED_WINDOWS
    )
    try:
        bc = _modes(await _progress(token))["blunder_check"]
        assert bc["state"] == "in_progress"
        assert bc["pending"] == _WINDOW_COUNT - _ENDED_WINDOWS
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


@pytest.mark.asyncio
async def test_pending_count_off_when_blunder_check_size_zero(test_engine) -> None:
    """Size 0 is `off`: no remaining, no badge contribution, even with a leftover open session."""
    user_id, token = await register_user("modes-bc-off", beta=False, test_engine=test_engine)
    await _seed_settings(test_engine, user_id, bc_size=0)
    session_id = await _seed_open_bc_session(test_engine, user_id, ended=0, started=0)
    try:
        body = await _progress(token)
        bc = _modes(body)["blunder_check"]
        assert bc["state"] == "off"
        assert bc["size"] == 0
        assert bc["remaining"] == 0
        assert bc["pending"] == 0
        assert body["pending_count"] == _modes(body)["puzzles"]["pending"]
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id])


async def _post_dismiss(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(_DISMISS, headers={"Authorization": f"Bearer {token}"})


@pytest.mark.asyncio
async def test_notice_visible_then_dismissed(test_engine) -> None:
    """A row stamped at launch shows the notice; the dismiss POST (204) clears it."""
    user_id, token = await register_user("notice-dismiss", beta=False, test_engine=test_engine)
    await _seed_settings(
        test_engine, user_id, notice_from=datetime.datetime.now(datetime.timezone.utc)
    )
    assert (await _progress(token))["blunder_check_notice"] is True
    resp = await _post_dismiss(token)
    assert resp.status_code == 204
    assert (await _progress(token))["blunder_check_notice"] is False
    # Idempotent: a second dismissal is still 204.
    assert (await _post_dismiss(token)).status_code == 204


@pytest.mark.asyncio
async def test_notice_dismiss_is_scoped_to_caller(test_engine) -> None:
    """T-251-18: dismissing as one user leaves another user's notice alone."""
    stamp = datetime.datetime.now(datetime.timezone.utc)
    user_a, token_a = await register_user("notice-scope-a", beta=False, test_engine=test_engine)
    user_b, token_b = await register_user("notice-scope-b", beta=False, test_engine=test_engine)
    await _seed_settings(test_engine, user_a, notice_from=stamp)
    await _seed_settings(test_engine, user_b, notice_from=stamp)
    assert (await _post_dismiss(token_a)).status_code == 204
    assert (await _progress(token_a))["blunder_check_notice"] is False
    assert (await _progress(token_b))["blunder_check_notice"] is True


@pytest.mark.asyncio
async def test_notice_hidden_after_blunder_check_amount_change(test_engine) -> None:
    """PUT /train/settings with a different blunder-check amount clears the notice (D-21)."""
    user_id, token = await register_user("notice-resize", beta=False, test_engine=test_engine)
    await _seed_settings(
        test_engine, user_id, notice_from=datetime.datetime.now(datetime.timezone.utc)
    )
    assert (await _progress(token))["blunder_check_notice"] is True
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            _SETTINGS,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "timezone": "UTC",
                "weekday_mask": ALL_WEEKDAYS_MASK,
                "puzzles_per_session": DEFAULT_PUZZLES_PER_SESSION,
                "blunder_check_per_session": DEFAULT_BLUNDER_CHECK_PER_SESSION - 1,
                "reminder_enabled": False,
                "reminder_hour": 18,
                "reminder_intent_at": None,
            },
        )
    assert resp.status_code == 200, resp.text
    assert (await _progress(token))["blunder_check_notice"] is False


@pytest.mark.asyncio
async def test_notice_never_for_new_user_or_guest(test_engine) -> None:
    """A NULL stamp (new users, guests) never shows the notice."""
    _user_id, token = await register_user("notice-new", beta=False, test_engine=test_engine)
    assert (await _progress(token))["blunder_check_notice"] is False
    _guest_id, guest_token = await register_user(
        "notice-guest", beta=False, test_engine=test_engine, guest=True
    )
    assert (await _progress(guest_token))["blunder_check_notice"] is False
