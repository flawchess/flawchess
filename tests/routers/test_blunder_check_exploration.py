"""Phase 261 end to end over HTTP: an exploration window from composition to its solution feedback.

A registered beta user owns one game whose only blunder scores 0.3 (below the 0.70 main cut). The
slot draw is forced to an own exploration slot, so the composer serves that blunder. The tests then
play the window through the real routes and read the solution.

Coverage:
- test_tracer_exploration_window_end_to_end  : compose, start, miss, solution feedback, stored arm
- test_exploration_window_counts_like_any_other : points, session points and the weekly aggregate
- test_no_arm_or_score_before_the_answer    : no arm / score / feedback key in any pre-solution body
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.blunder_check import BlunderCheckWindow, WindowArm
from app.repositories.train_leaderboard_repository import fetch_week_bc_aggregates
from app.services import blunder_check_selection
from app.services.blunder_check_rules import BLUNDER_POINTS, SlotPlan, WindowShape
from tests.blunder_check_seed import (
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)
from tests.facepalm_seed import SEED_FACEPALM_TOLERANCE
from tests.routers.test_blunder_check_drill import (
    _BASE,
    _answer,
    _begin,
    _Clock,
    _start,
    _window_row,
)

_BLUNDER_PLY = 40  # white user; 20 clean user moves precede it
_BLUNDER_DROP_CP = 600
_SEED_ROWS = 61
_EXPLORATION_TARGET = 0.3
_BLUNDER_POSITION = 1
_SHAPE = WindowShape(3, _BLUNDER_POSITION)
_FORBIDDEN_KEYS = {
    "arm",
    "selection_arm",
    "arm_probability",
    "facepalm_score",
    "feedback",
    "type_line",
    "hard_to_catch",
}
_SESSIONS_URL = "/api/blunder-check/sessions"


@pytest.fixture
def clock() -> Iterator[_Clock]:
    c = _Clock()
    app.dependency_overrides[dev_now_utc] = lambda: c.now
    yield c
    app.dependency_overrides.pop(dev_now_utc, None)


def _all_keys(value: object) -> set[str]:
    """Every dict key anywhere in a JSON value."""
    keys: set[str] = set()
    if isinstance(value, dict):
        keys |= set(value)
        for child in value.values():
            keys |= _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            keys |= _all_keys(child)
    return keys


def _force_own_exploration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every slot is an own exploration blunder slot of one fixed shape."""
    monkeypatch.setattr(
        blunder_check_selection,
        "draw_slot_plan",
        lambda rng: SlotPlan("own", _SHAPE, "exploration"),
    )
    monkeypatch.setattr(blunder_check_selection, "draw_blunder_shape", lambda rng: _SHAPE)
    monkeypatch.setattr(blunder_check_selection, "draw_herring_shape", lambda rng: _SHAPE)


async def _seed_low_score_game(test_engine, user_id: int) -> int:
    evals = with_user_blunder(flat_evals(_SEED_ROWS, 0), _BLUNDER_PLY, _BLUNDER_DROP_CP)
    return await seed_judged_game(
        test_engine,
        user_id=user_id,
        evals_cp=evals,
        blunders=[SeedBlunder(ply=_BLUNDER_PLY, facepalm_target=_EXPLORATION_TARGET)],
    )


async def _post_sessions(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(_SESSIONS_URL, headers={"Authorization": f"Bearer {token}"})


async def _get_solution(token: str, session_id: int, position: int) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(
            f"{_BASE}/{session_id}/windows/{position}/solution",
            headers={"Authorization": f"Bearer {token}"},
        )


async def _position_of_game(test_engine, session_id: int, game_id: int) -> int:
    """The position of the window built from the seeded game (other slots may hold other games)."""
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        windows = (
            await session.execute(
                select(BlunderCheckWindow).where(BlunderCheckWindow.session_id == session_id)
            )
        ).scalars()
        for window in windows:
            if window.game_id == game_id:
                return window.position
    raise AssertionError("the seeded game did not fill any window")


async def _compose_and_start(
    test_engine, token: str, game_id: int
) -> tuple[int, int, dict[str, Any], dict[str, Any]]:
    """POST /sessions, find the seeded game's window, start and begin it."""
    created = await _post_sessions(token)
    assert created.status_code == 200, created.text
    session_id = int(created.json()["session_id"])
    position = await _position_of_game(test_engine, session_id, game_id)
    start = await _start(token, session_id, position)
    assert start.status_code == 200, start.text
    begun = await _begin(token, session_id, position)
    assert begun.status_code == 200, begun.text
    return session_id, position, created.json(), start.json()


@pytest.mark.asyncio
async def test_tracer_exploration_window_end_to_end(
    test_engine, monkeypatch, clock: _Clock
) -> None:
    _force_own_exploration(monkeypatch)
    user_id, token = await register_user("bc-explore", beta=True, test_engine=test_engine)
    game_id = await _seed_low_score_game(test_engine, user_id)
    session_id: int | None = None
    try:
        session_id, position, _, _ = await _compose_and_start(test_engine, token, game_id)
        # The blunder is at position 1, so "safe" is a miss.
        answered = await _answer(token, session_id, position, _BLUNDER_POSITION, "safe")
        assert answered.status_code == 200, answered.text
        resp = await _get_solution(token, session_id, position)
        assert resp.status_code == 200, resp.text
        solution = resp.json()
        row = await _window_row(test_engine, session_id, position)
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [game_id])
    assert solution["kind"] == "blunder"
    assert solution["outcome"] == "missed"
    feedback = solution["feedback"]
    assert feedback["score"] == pytest.approx(_EXPLORATION_TARGET, abs=SEED_FACEPALM_TOLERANCE)
    assert feedback["hard_to_catch"] is True
    assert feedback["type_line"] is None  # the seed stores no engine line
    assert row.selection_arm == int(WindowArm.EXPLORATION)


@pytest.mark.asyncio
async def test_exploration_window_counts_like_any_other(
    test_engine, monkeypatch, clock: _Clock
) -> None:
    _force_own_exploration(monkeypatch)
    user_id, token = await register_user("bc-explore-pts", beta=True, test_engine=test_engine)
    game_id = await _seed_low_score_game(test_engine, user_id)
    session_id: int | None = None
    try:
        session_id, position, _, _ = await _compose_and_start(test_engine, token, game_id)
        answered = await _answer(token, session_id, position, _BLUNDER_POSITION, "blunder")
        assert answered.status_code == 200, answered.text
        body = answered.json()
        row = await _window_row(test_engine, session_id, position)
        week_start = clock.now - datetime.timedelta(days=clock.now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as db:
            aggregates = await fetch_week_bc_aggregates(
                db, week_start=week_start, week_end=week_start + datetime.timedelta(days=7)
            )
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [game_id])
    assert body["points_awarded"] == BLUNDER_POINTS
    assert body["session_points"] >= BLUNDER_POINTS
    mine = [a for a in aggregates if a.user_id == user_id]
    assert len(mine) == 1
    assert mine[0].totals.points_scored == row.points_scored
    assert row.points_scored >= BLUNDER_POINTS


@pytest.mark.asyncio
async def test_no_arm_or_score_before_the_answer(test_engine, monkeypatch, clock: _Clock) -> None:
    _force_own_exploration(monkeypatch)
    user_id, token = await register_user("bc-explore-leak", beta=True, test_engine=test_engine)
    game_id = await _seed_low_score_game(test_engine, user_id)
    session_id: int | None = None
    try:
        session_id, position, created, start = await _compose_and_start(test_engine, token, game_id)
        answered = await _answer(token, session_id, position, _BLUNDER_POSITION, "safe")
        assert answered.status_code == 200, answered.text
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [game_id])
    for name, payload in (("sessions", created), ("start", start), ("answer", answered.json())):
        leaked = _all_keys(payload) & _FORBIDDEN_KEYS
        assert not leaked, f"{name} payload leaks {leaked}"
