"""Integration tests for the better move and the solution endpoints (Phase 249-05).

Sessions are built with the drill test helpers (`_setup`, `_Spec`, `clock`), so every window
shape and every instant is deterministic.

Coverage (this module grows task by task):
- test_tracer_*  : catch a blunder, submit its key as the better move (+2), read the solution
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

import chess
import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.blunder_check import (
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckWindow,
    WindowArm,
    WindowOutcome,
)
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.blunder_check_repository import WindowSelectionRecord, insert_session
from app.services.blunder_check_rules import BETTER_MOVE_POINTS, BLUNDER_POINTS, SAFE_POINTS
from tests.blunder_check_seed import delete_blunder_check_sessions, delete_games, register_user
from tests.routers.test_blunder_check_drill import (
    _BASE,
    _BLUNDER_AT_ONE,
    _BLUNDER_PLY,
    _T0,
    _all_keys,
    _call,
    _Clock,
    _mainline_ucis,
    _new_window,
    _ok,
    _setup,
    _Setup,
    _Spec,
    _started,
    _window_row,
)


@pytest.fixture
def clock() -> Iterator[_Clock]:
    c = _Clock()
    app.dependency_overrides[dev_now_utc] = lambda: c.now
    yield c
    app.dependency_overrides.pop(dev_now_utc, None)


_BETTER_KEYS = {"tier", "points_awarded", "window_points", "session_points"}


async def _better_move(
    s: _Setup, position: int, played_uci: str, client_tier: str = "wrong"
) -> httpx.Response:
    return await _call(
        s.token,
        f"{_BASE}/{s.session_id}/windows/{position}/better-move",
        {"played_uci": played_uci, "client_tier": client_tier},
    )


async def _solution(token: str, session_id: int, position: int) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(
            f"{_BASE}/{session_id}/windows/{position}/solution",
            headers={"Authorization": f"Bearer {token}"},
        )


async def _caught_at_one(s: _Setup) -> dict[str, Any]:
    """Start the window and catch the position-1 blunder; return the answer body."""
    await _started(s)
    return await _ok(s, 1, "blunder")


# ---------------------------------------------------------------------------
# Reload during the better-move step
# ---------------------------------------------------------------------------


async def _open_session(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(f"{_BASE}/open", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_reload_before_the_better_move_hands_the_task_out_again(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_BLUNDER_AT_ONE, _BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)

        # The caught window stays the current one, and starting it again resumes the task.
        assert (await _open_session(s.token))["current_position"] == 0
        resumed = await _started(s)
        assert resumed["better_move"] == caught["better_move"]
        assert resumed["prompt"] == {"move_index": 1, "move_uci": mainline[_BLUNDER_PLY]}
        assert [(m["move_index"], m["result"]) for m in resumed["answered"]] == [(1, "caught")]
        assert resumed["window_points"] == BLUNDER_POINTS

        # Once the better move is played the window is done: the session moves on.
        played = await _better_move(s, 0, caught["better_move"]["key_uci"])
        assert played.status_code == 200, played.text
        assert (await _open_session(s.token))["current_position"] == 1
        restart = await _call(s.token, f"{_BASE}/{s.session_id}/windows/0/start")
    assert restart.status_code == 409 and restart.json()["detail"] == "window_ended"


@pytest.mark.asyncio
@pytest.mark.parametrize("miss", ["safe", "timeout"])
async def test_reload_after_a_miss_hands_the_task_out_again(test_engine, clock, miss: str) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE, _BLUNDER_AT_ONE]) as s:
        await _started(s)
        missed = await _ok(s, 1, miss)

        # The missed window stays the current one, and starting it again resumes the task.
        assert (await _open_session(s.token))["current_position"] == 0
        resumed = await _started(s)
        assert resumed["better_move"] == missed["better_move"]
        assert resumed["outcome"] == "missed" and resumed["awaiting_ready"] is False
        assert [(m["move_index"], m["result"]) for m in resumed["answered"]] == [
            (1, "missed" if miss == "safe" else "timeout_blunder")
        ]

        # Once the better move is played the window is done: the session moves on.
        played = await _better_move(s, 0, missed["better_move"]["key_uci"])
        assert played.status_code == 200, played.text
        assert (await _open_session(s.token))["current_position"] == 1
        restart = await _call(s.token, f"{_BASE}/{s.session_id}/windows/0/start")
    assert restart.status_code == 409 and restart.json()["detail"] == "window_ended"


# ---------------------------------------------------------------------------
# Tracer: a caught blunder's better move earns +2 and the solution comes back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tracer_better_move_earns_two_and_the_solution_is_served(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        window = await _window_row(test_engine, s.session_id, 0)
        key = caught["better_move"]["key_uci"]

        resp = await _better_move(s, 0, key, client_tier="wrong")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body) == _BETTER_KEYS
        # The key is good whatever the client asserts (server override).
        assert body["tier"] == "good"
        assert body["points_awarded"] == BETTER_MOVE_POINTS
        assert body["window_points"] == BLUNDER_POINTS + BETTER_MOVE_POINTS
        assert body["session_points"] == BLUNDER_POINTS + BETTER_MOVE_POINTS

        solution = await _solution(s.token, s.session_id, 0)
        assert solution.status_code == 200, solution.text
        data = solution.json()
        assert data["kind"] == "blunder" and data["outcome"] == "caught"
        assert data["game_id"] == window.game_id
        assert data["analysis_ply"] == _BLUNDER_PLY
        assert data["key_uci"] == key == window.key_uci
        assert data["blunder_uci"] == mainline[_BLUNDER_PLY]
        assert data["better_move_tier"] == "good" and data["better_move_uci"] == key
        assert data["window_points"] == BLUNDER_POINTS + BETTER_MOVE_POINTS
        # The breakdown behind the verdict's point badges adds up to the window's points.
        assert (data["safe_points"], data["blunder_points"], data["better_move_points"]) == (
            0,
            BLUNDER_POINTS,
            BETTER_MOVE_POINTS,
        )


# ---------------------------------------------------------------------------
# Better move: tier precedence and claim guards
# ---------------------------------------------------------------------------

_BLUNDER_KEYS = {
    "kind",
    "outcome",
    "is_own",
    "window_case",
    "game_id",
    "analysis_ply",
    "fen",
    "blunder_uci",
    "key_uci",
    "better_move_uci",
    "better_move_tier",
    "server_graded_moves",
    "game_info",
    "window_points",
    "safe_points",
    "blunder_points",
    "better_move_points",
    "feedback",
}
_HERRING_KEYS = {
    "kind",
    "outcome",
    "is_own",
    "game_id",
    "analysis_ply",
    "fen",
    "sequence_ucis",
    "game_info",
    "window_points",
}
_FALSE_ALARM_KEYS = {
    "kind",
    "outcome",
    "is_own",
    "game_id",
    "analysis_ply",
    "flagged_uci",
    "fen",
    "key_uci",
    "game_info",
    "window_points",
}
# What a false alarm still withholds: the window's case and its unreached blunder (D-10).
_FALSE_ALARM_WITHHELD_KEYS = {"window_case", "blunder_uci", "refutation_uci"}
_GAME_INFO_KEYS = {"time_control_str", "time_control_bucket", "played_at", "mover_rating"}
_WITHHELD_KEYS = {"game_id", "is_own", "window_case", "blunder_uci", "key_uci", "analysis_ply"}
_IDENTITY_KEY_PARTS = ("username", "email", "user_id")
_HERRING_3 = _Spec(first_ply=30, length=3, blunder_position=None)
_BLUNDER_AT_THREE = _Spec(first_ply=36, length=4, blunder_position=3)  # blunder ply 40
_BLUNDER_AT_THREE_PLY = 40
_FALSE_ALARM_PLY = 38  # the second judged move of _BLUNDER_AT_THREE
_HERRING_ALARM_PLY = 32  # the second judged move of _HERRING_3
_RATING = 1500
_ILLEGAL_UCI = "e1e5"


def _board_before(ply: int) -> chess.Board:
    board = chess.Board()
    for uci in _mainline_ucis()[:ply]:
        board.push_uci(uci)
    return board


def _off_key_legal_move(key: str) -> str:
    """A legal move at the blunder ply that is neither the key nor the user's own blunder."""
    banned = {key, _mainline_ucis()[_BLUNDER_PLY]}
    return next(m.uci() for m in _board_before(_BLUNDER_PLY).legal_moves if m.uci() not in banned)


async def _set_blob(test_engine, game_id: int, ply: int, blob: list[dict[str, Any]]) -> None:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            await session.execute(
                update(GameFlaw)
                .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
                .values(missed_pv_lines=blob)
            )


@pytest.mark.asyncio
async def test_precedence_the_users_own_blunder_is_wrong_whatever_the_client_says(
    test_engine, clock
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        resp = await _better_move(s, 0, _mainline_ucis()[_BLUNDER_PLY], client_tier="good")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tier"] == "wrong" and body["points_awarded"] == 0
    assert body["window_points"] == BLUNDER_POINTS


@pytest.mark.asyncio
async def test_precedence_a_server_graded_move_overrides_the_client_tier(
    test_engine, clock
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        key = caught["better_move"]["key_uci"]
        runner_up = _off_key_legal_move(key)
        window = await _window_row(test_engine, s.session_id, 0)
        assert window.game_id is not None
        await _set_blob(
            test_engine,
            window.game_id,
            _BLUNDER_PLY,
            [{"b": 50, "bm": None, "s": 40, "sm": None, "su": runner_up}],
        )
        resp = await _better_move(s, 0, runner_up, client_tier="wrong")
    assert resp.status_code == 200, resp.text
    assert resp.json()["tier"] == "good" and resp.json()["points_awarded"] == BETTER_MOVE_POINTS


@pytest.mark.asyncio
@pytest.mark.parametrize(("client_tier", "points"), [("good", 1), ("inaccuracy", 1), ("wrong", 0)])
async def test_precedence_an_ungraded_off_key_move_takes_the_client_tier(
    test_engine, clock, client_tier: str, points: int
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        off_key = _off_key_legal_move(caught["better_move"]["key_uci"])
        resp = await _better_move(s, 0, off_key, client_tier=client_tier)
        window = await _window_row(test_engine, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    assert resp.json()["tier"] == client_tier and resp.json()["points_awarded"] == points
    assert window.points_scored == BLUNDER_POINTS + points
    assert window.better_move_uci == off_key


@pytest.mark.asyncio
async def test_better_move_twice_is_rejected_and_awards_nothing_more(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        key = caught["better_move"]["key_uci"]
        first = await _better_move(s, 0, key)
        second = await _better_move(s, 0, key)
        window = await _window_row(test_engine, s.session_id, 0)
    assert first.status_code == 200
    assert second.status_code == 409 and second.json()["detail"] == "better_move_done"
    assert window.points_scored == BLUNDER_POINTS + BETTER_MOVE_POINTS


@pytest.mark.asyncio
async def test_better_move_concurrent_submits_award_once(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        key = caught["better_move"]["key_uci"]
        first, second = await asyncio.gather(_better_move(s, 0, key), _better_move(s, 0, key))
        window = await _window_row(test_engine, s.session_id, 0)
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert window.points_scored == BLUNDER_POINTS + BETTER_MOVE_POINTS


@pytest.mark.asyncio
async def test_better_move_refused_on_cleared_and_false_alarm(test_engine, clock) -> None:
    # Any legal-looking move: the window-state guard fires before the legality check.
    key = _mainline_ucis()[_BLUNDER_PLY]
    specs = [_HERRING_3, _BLUNDER_AT_THREE]
    async with _setup(test_engine, specs) as s:
        await _started(s, 0)
        for index in (1, 2, 3):
            await _ok(s, index, "safe", position=0)  # cleared
        await _started(s, 1)
        await _ok(s, 1, "safe", position=1)
        await _ok(s, 2, "blunder", position=1)  # false alarm
        results = [await _better_move(s, position, key) for position in range(2)]
        rows = [await _window_row(test_engine, s.session_id, position) for position in range(2)]
    assert [r.status_code for r in results] == [409, 409]
    assert {r.json()["detail"] for r in results} == {"no_better_move"}
    assert all(row.better_move_tier is None for row in rows)


@pytest.mark.asyncio
@pytest.mark.parametrize("miss", ["safe", "timeout"])
async def test_better_move_after_a_miss_is_graded_and_scored_like_after_a_catch(
    test_engine, clock, miss: str
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "safe")
        missed = await _ok(s, 3, miss)
        key = missed["better_move"]["key_uci"]
        # A timeout on the blunder forfeits the pot, a "safe" call keeps it.
        kept = 2 * SAFE_POINTS if miss == "safe" else 0
        resp = await _better_move(s, 0, key, client_tier="wrong")
        again = await _better_move(s, 0, key)
        window = await _window_row(test_engine, s.session_id, 0)
    assert missed["outcome"] == "missed" and missed["window_points"] == kept
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tier"] == "good" and body["points_awarded"] == BETTER_MOVE_POINTS
    assert body["window_points"] == kept + BETTER_MOVE_POINTS
    assert again.status_code == 409 and again.json()["detail"] == "better_move_done"
    assert window.outcome == int(WindowOutcome.MISSED)
    assert window.points_scored == kept + BETTER_MOVE_POINTS


@pytest.mark.asyncio
async def test_better_move_on_a_window_that_has_not_ended_is_refused(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _started(s)
        resp = await _better_move(s, 0, _mainline_ucis()[_BLUNDER_PLY])
    assert resp.status_code == 409 and resp.json()["detail"] == "no_better_move"


@pytest.mark.asyncio
async def test_better_move_on_a_finished_session_is_session_closed(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        finished = await _call(s.token, f"{_BASE}/{s.session_id}/finish")
        resp = await _better_move(s, 0, caught["better_move"]["key_uci"])
        window = await _window_row(test_engine, s.session_id, 0)
    assert finished.status_code == 200, finished.text
    assert resp.status_code == 409 and resp.json()["detail"] == "session_closed"
    assert window.better_move_tier is None and window.points_scored == BLUNDER_POINTS


@pytest.mark.asyncio
@pytest.mark.parametrize("played", [_ILLEGAL_UCI, "a1a1", "e2e5"])
async def test_better_move_illegal_uci_is_422_and_awards_nothing(
    test_engine, clock, played: str
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        resp = await _better_move(s, 0, played)
        malformed = await _better_move(s, 0, "zzzz")
        window = await _window_row(test_engine, s.session_id, 0)
    assert resp.status_code == 422 and resp.json()["detail"] == "Illegal move"
    assert malformed.status_code == 422
    assert window.better_move_tier is None and window.points_scored == BLUNDER_POINTS


@pytest.mark.asyncio
async def test_better_move_and_solution_of_another_users_window_are_404(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        caught = await _caught_at_one(s)
        _, other_token = await register_user(
            "bc-solution-other", beta=True, test_engine=test_engine
        )
        other = _Setup(0, other_token, s.session_id, [])
        better = await _better_move(other, 0, caught["better_move"]["key_uci"])
        solution = await _solution(other_token, s.session_id, 0)
        window = await _window_row(test_engine, s.session_id, 0)
    assert better.status_code == 404 and solution.status_code == 404
    assert window.better_move_tier is None


@pytest.mark.asyncio
async def test_better_move_non_beta_user_and_guest_reach_the_routes(test_engine, clock) -> None:
    """D-18: no beta gate; a non-beta user and a guest get the scoped 404 for a foreign session."""
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        statuses: list[int] = []
        for guest in (False, True):
            _, token = await register_user(
                "bc-solution-nonbeta", beta=False, test_engine=test_engine, guest=guest
            )
            other = _Setup(0, token, s.session_id, [])
            statuses.append((await _better_move(other, 0, "e2e4")).status_code)
            statuses.append((await _solution(token, s.session_id, 0)).status_code)
    assert statuses == [404, 404, 404, 404]


# ---------------------------------------------------------------------------
# Solution: window must have ended, then each kind reveals what D-10/D-14/D-16 allow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_solution_window_open_is_409_before_and_during_the_window(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        before = await _solution(s.token, s.session_id, 0)
        await _started(s)
        during = await _solution(s.token, s.session_id, 0)
    for resp in (before, during):
        assert resp.status_code == 409 and resp.json()["detail"] == "window_open"
        assert not _all_keys(resp.json()) & _WITHHELD_KEYS


@pytest.mark.asyncio
async def test_solution_missed_window_before_and_after_the_better_move(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "safe")
        missed = await _ok(s, 3, "safe")
        before = await _solution(s.token, s.session_id, 0)
        played = await _better_move(s, 0, missed["better_move"]["key_uci"])
        after = await _solution(s.token, s.session_id, 0)
        window = await _window_row(test_engine, s.session_id, 0)
    assert before.status_code == 200, before.text
    data = before.json()
    assert set(data) == _BLUNDER_KEYS
    assert data["kind"] == "blunder" and data["outcome"] == "missed"
    assert data["better_move_uci"] is None and data["better_move_tier"] is None
    assert data["game_id"] == window.game_id and data["is_own"] is True
    # A "safe" call kept the pot, so it is all safe points; the miss itself earned nothing.
    assert (data["safe_points"], data["blunder_points"], data["better_move_points"]) == (
        2 * SAFE_POINTS,
        0,
        None,
    )
    # No blob on the flaw row: no graded alternative beyond the key.
    assert [m["uci"] for m in data["server_graded_moves"] if m["uci"] != window.key_uci] == []
    assert data["window_case"] == "allowed"
    assert data["blunder_uci"] == mainline[_BLUNDER_AT_THREE_PLY]
    assert data["key_uci"] == window.key_uci
    assert data["fen"] == _board_before(_BLUNDER_AT_THREE_PLY).fen()
    assert data["game_info"] is None
    assert played.status_code == 200, played.text
    done = after.json()
    assert done["better_move_tier"] == "good" and done["better_move_uci"] == window.key_uci
    assert (done["safe_points"], done["blunder_points"], done["better_move_points"]) == (
        2 * SAFE_POINTS,
        0,
        BETTER_MOVE_POINTS,
    )
    assert done["window_points"] == 2 * SAFE_POINTS + BETTER_MOVE_POINTS


@pytest.mark.asyncio
async def test_solution_missed_after_a_timeout_has_no_safe_points(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "safe")
        missed = await _ok(s, 3, "timeout")
        await _better_move(s, 0, missed["better_move"]["key_uci"])
        resp = await _solution(s.token, s.session_id, 0)
    data = resp.json()
    assert (data["safe_points"], data["blunder_points"], data["better_move_points"]) == (
        0,
        0,
        BETTER_MOVE_POINTS,
    )
    assert data["window_points"] == BETTER_MOVE_POINTS


@pytest.mark.asyncio
async def test_solution_of_a_window_caught_before_the_rebalance_keeps_its_old_points(
    test_engine, clock
) -> None:
    """A catch that earned 3 (pre quick 261123-lb8) reports 3, not the constant 2."""
    old_catch_points = 3
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        window = await _window_row(test_engine, s.session_id, 0)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            async with session.begin():
                await session.execute(
                    update(BlunderCheckAnswer)
                    .where(
                        BlunderCheckAnswer.window_id == window.id,
                        BlunderCheckAnswer.result == int(AnswerResult.CAUGHT),
                    )
                    .values(points_awarded=old_catch_points)
                )
                await session.execute(
                    update(BlunderCheckWindow)
                    .where(BlunderCheckWindow.id == window.id)
                    .values(points_scored=old_catch_points)
                )
        resp = await _solution(s.token, s.session_id, 0)
    data = resp.json()
    assert data["blunder_points"] == old_catch_points
    assert data["safe_points"] == 0 and data["window_points"] == old_catch_points


@pytest.mark.asyncio
async def test_solution_caught_window_before_the_better_move_has_null_better_fields(
    test_engine, clock
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["outcome"] == "caught" and data["better_move_tier"] is None
    assert data["window_points"] == BLUNDER_POINTS
    assert data["blunder_points"] == BLUNDER_POINTS and data["better_move_points"] is None


@pytest.mark.asyncio
async def test_solution_herring_cleared_has_exactly_the_herring_keys(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        for index in (1, 2, 3):
            await _ok(s, index, "safe")
        resp = await _solution(s.token, s.session_id, 0)
        window = await _window_row(test_engine, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data) == _HERRING_KEYS
    assert data["kind"] == "herring" and data["outcome"] == "cleared"
    # The whole window with the replies, through the reply after the last judged move.
    assert data["sequence_ucis"] == mainline[30:36]
    assert data["analysis_ply"] == _HERRING_3.first_ply
    assert data["fen"] == _board_before(_HERRING_3.first_ply).fen()
    assert data["game_id"] == window.game_id and data["is_own"] is True
    assert data["game_info"] is None and data["window_points"] == 3 * SAFE_POINTS


async def _false_alarm_solution(
    test_engine, spec: _Spec, alarm_index: int, safe_before: int
) -> dict[str, Any]:
    """Play `safe_before` safe moves, then flag the next one; return the solution JSON."""
    async with _setup(test_engine, [spec]) as s:
        await _started(s)
        for index in range(1, safe_before + 1):
            await _ok(s, index, "safe")
        alarm = await _ok(s, alarm_index, "blunder")
        assert alarm["outcome"] == "false_alarm"
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_solution_false_alarm_in_a_blunder_window_withholds_the_blunder(
    test_engine, clock
) -> None:
    data = await _false_alarm_solution(test_engine, _BLUNDER_AT_THREE, 2, 1)
    assert set(data) == _FALSE_ALARM_KEYS
    assert data["kind"] == "false_alarm" and data["outcome"] == "false_alarm"
    assert data["flagged_uci"] == _mainline_ucis()[_FALSE_ALARM_PLY]
    assert data["fen"] == _board_before(_FALSE_ALARM_PLY).fen()
    assert data["window_points"] == SAFE_POINTS
    # Phase 249 UAT: the flagged move's game and ply are served for the lines and Analyze,
    # the ply being the flagged move's, never the unreached blunder's.
    assert data["is_own"] is True and data["game_id"] is not None
    assert data["analysis_ply"] == _FALSE_ALARM_PLY
    assert data["game_info"] is None
    assert not _all_keys(data) & _FALSE_ALARM_WITHHELD_KEYS


@pytest.mark.asyncio
async def test_solution_false_alarm_in_a_herring_window_withholds_the_window(
    test_engine, clock
) -> None:
    data = await _false_alarm_solution(test_engine, _HERRING_3, 2, 1)
    assert set(data) == _FALSE_ALARM_KEYS
    assert data["flagged_uci"] == _mainline_ucis()[_HERRING_ALARM_PLY]
    assert data["fen"] == _board_before(_HERRING_ALARM_PLY).fen()
    assert not _all_keys(data) & _FALSE_ALARM_WITHHELD_KEYS


@pytest.mark.asyncio
@pytest.mark.parametrize("stored_is_legal", [True, False])
async def test_solution_false_alarm_serves_the_stored_best_move_only_when_legal(
    test_engine, clock, stored_is_legal: bool
) -> None:
    board = _board_before(_FALSE_ALARM_PLY)
    legal = next(
        m.uci() for m in board.legal_moves if m.uci() != _mainline_ucis()[_FALSE_ALARM_PLY]
    )
    stored = legal if stored_is_legal else _ILLEGAL_UCI
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        window = await _window_row(test_engine, s.session_id, 0)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            await session.execute(
                update(GamePosition)
                .where(GamePosition.game_id == window.game_id, GamePosition.ply == _FALSE_ALARM_PLY)
                .values(best_move=stored)
            )
            await session.commit()
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "blunder")
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    assert resp.json()["key_uci"] == (legal if stored_is_legal else None)


@pytest.mark.asyncio
async def test_solution_false_alarm_on_the_first_move_has_zero_points(test_engine, clock) -> None:
    data = await _false_alarm_solution(test_engine, _BLUNDER_AT_THREE, 1, 0)
    assert set(data) == _FALSE_ALARM_KEYS and data["window_points"] == 0
    assert data["flagged_uci"] == _mainline_ucis()[_BLUNDER_AT_THREE.first_ply]


@asynccontextmanager
async def _foreign_setup(test_engine, spec: _Spec):
    """A beta solver with a window whose game belongs to ANOTHER user (is_own false)."""
    solver_id, token = await register_user("bc-solver", beta=True, test_engine=test_engine)
    owner_id, _ = await register_user("bc-owner", beta=False, test_engine=test_engine)
    window = replace(await _new_window(test_engine, owner_id, 0, spec), is_own=False)
    session_id: int | None = None
    try:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            async with session.begin():
                session_id = await insert_session(
                    session,
                    user_id=solver_id,
                    windows=[window],
                    now_utc=_T0,
                    session_date=_T0.date(),
                    expires_on=_T0.date() + datetime.timedelta(days=1),
                )
        assert session_id is not None
        yield _Setup(solver_id, token, session_id, [window.game_id])
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [window.game_id])


def _assert_neutral(value: object) -> None:
    for key in _all_keys(value):
        assert not any(part in key for part in _IDENTITY_KEY_PARTS), key


@pytest.mark.asyncio
async def test_solution_foreign_blunder_window_carries_neutral_game_info(
    test_engine, clock
) -> None:
    async with _foreign_setup(test_engine, _BLUNDER_AT_ONE) as s:
        await _started(s)
        await _ok(s, 1, "blunder")
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_own"] is False and data["game_id"] is not None
    info = data["game_info"]
    assert set(info) == _GAME_INFO_KEYS
    assert info["time_control_str"] == "300+0" and info["time_control_bucket"] == "blitz"
    assert info["played_at"] is not None and info["mover_rating"] == _RATING
    _assert_neutral(data)


@pytest.mark.asyncio
async def test_solution_foreign_herring_window_carries_neutral_game_info(
    test_engine, clock
) -> None:
    async with _foreign_setup(test_engine, _HERRING_3) as s:
        await _started(s)
        for index in (1, 2, 3):
            await _ok(s, index, "safe")
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "herring" and data["is_own"] is False
    assert set(data["game_info"]) == _GAME_INFO_KEYS
    _assert_neutral(data)


@pytest.mark.asyncio
async def test_solution_foreign_false_alarm_carries_neutral_game_info(test_engine, clock) -> None:
    async with _foreign_setup(test_engine, _BLUNDER_AT_THREE) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "blunder")
        resp = await _solution(s.token, s.session_id, 0)
    data = resp.json()
    assert set(data) == _FALSE_ALARM_KEYS
    assert data["is_own"] is False and set(data["game_info"]) == _GAME_INFO_KEYS
    assert not _all_keys(data) & _FALSE_ALARM_WITHHELD_KEYS
    _assert_neutral(data)


@pytest.mark.asyncio
async def test_better_move_works_on_a_foreign_window_too(test_engine, clock) -> None:
    async with _foreign_setup(test_engine, _BLUNDER_AT_ONE) as s:
        await _started(s)
        caught = await _ok(s, 1, "blunder")
        resp = await _better_move(s, 0, caught["better_move"]["key_uci"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["tier"] == "good"


@pytest.mark.asyncio
async def test_solution_own_window_has_null_game_info(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        data = (await _solution(s.token, s.session_id, 0)).json()
    assert data["is_own"] is True and data["game_info"] is None


@pytest.mark.asyncio
async def test_solution_still_serves_after_the_source_game_is_deleted(test_engine, clock) -> None:
    async with _foreign_setup(test_engine, _BLUNDER_AT_ONE) as s:
        await _started(s)
        caught = await _ok(s, 1, "blunder")
        await delete_games(test_engine, s.game_ids)
        solution = await _solution(s.token, s.session_id, 0)
        # The snapshot keeps the window servable: the better move still grades (empty graded set).
        better = await _better_move(s, 0, caught["better_move"]["key_uci"])
    assert solution.status_code == 200, solution.text
    data = solution.json()
    assert data["game_id"] is None and data["game_info"] is None
    assert data["key_uci"] == caught["better_move"]["key_uci"]
    assert better.status_code == 200 and better.json()["tier"] == "good"


@pytest.mark.asyncio
async def test_solution_missed_window_carries_the_graded_alternatives(test_engine, clock) -> None:
    """A missed blunder never got a better-move task, yet its solution names the good moves."""
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
        assert window.game_id is not None and window.key_uci is not None
        runner_up = _off_key_legal_move(window.key_uci)
        await _set_blob(
            test_engine,
            window.game_id,
            _BLUNDER_PLY,
            [{"b": 50, "bm": None, "s": 40, "sm": None, "su": runner_up}],
        )
        resp = await _solution(s.token, s.session_id, 0)
    assert resp.status_code == 200, resp.text
    # The graded set lists the key too; the runner-up is the alternative the solution badges.
    assert {"uci": runner_up, "tier": "good"} in resp.json()["server_graded_moves"]


# ---------------------------------------------------------------------------
# Phase 261 feedback: the serve-time snapshot on the solution (D-04, D-05, D-06)
# ---------------------------------------------------------------------------

_SNAPSHOT_PLAYED_PROB = 0.05
_FEEDBACK_KEYS = {"score", "type_line", "hard_to_catch"}


def _record(
    *, score: float, loss: float, missed: float, type_swing: int | None, type_mate: bool
) -> WindowSelectionRecord:
    return WindowSelectionRecord(
        arm=WindowArm.MAIN,
        arm_probability=0.8,
        facepalm_score=score,
        played_prob=_SNAPSHOT_PLAYED_PROB,
        loss=loss,
        missed=missed,
        best_prob=None,
        reply_prob=None,
        type_swing=type_swing,
        type_mate=type_mate,
    )


@asynccontextmanager
async def _snapshot_setup(test_engine, specs: list[_Spec], record: WindowSelectionRecord | None):
    """Own windows like `_setup`, each carrying `record` as its serve-time snapshot."""
    user_id, token = await register_user("bc-feedback", beta=True, test_engine=test_engine)
    windows = [
        replace(await _new_window(test_engine, user_id, position, spec), selection=record)
        for position, spec in enumerate(specs)
    ]
    session_id: int | None = None
    try:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            async with session.begin():
                session_id = await insert_session(
                    session,
                    user_id=user_id,
                    windows=windows,
                    now_utc=_T0,
                    session_date=_T0.date(),
                    expires_on=_T0.date() + datetime.timedelta(days=1),
                )
        assert session_id is not None
        yield _Setup(user_id, token, session_id, [w.game_id for w in windows])
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, [w.game_id for w in windows])


@pytest.mark.asyncio
async def test_solution_legacy_window_has_null_feedback(test_engine, clock) -> None:
    """A window served before the phase has no snapshot: the feedback is null, never absent."""
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _caught_at_one(s)
        data = (await _solution(s.token, s.session_id, 0)).json()
    assert "feedback" in data and data["feedback"] is None


@pytest.mark.asyncio
async def test_solution_missed_and_caught_carry_the_snapshot_feedback(test_engine, clock) -> None:
    record = _record(score=0.95, loss=3.0, missed=0.0, type_swing=3, type_mate=False)
    async with _snapshot_setup(test_engine, [_BLUNDER_AT_ONE, _BLUNDER_AT_ONE], record) as s:
        await _started(s, 0)
        await _ok(s, 1, "blunder", position=0)  # caught
        await _started(s, 1)
        await _ok(s, 1, "safe", position=1)  # missed
        caught = (await _solution(s.token, s.session_id, 0)).json()
        missed = (await _solution(s.token, s.session_id, 1)).json()
    assert (caught["outcome"], missed["outcome"]) == ("caught", "missed")
    for data in (caught, missed):
        feedback = data["feedback"]
        assert set(feedback) == _FEEDBACK_KEYS
        assert feedback["score"] == pytest.approx(0.95, abs=1e-6)
        assert feedback["type_line"] == "allowed_material"
        assert feedback["hard_to_catch"] is False


@pytest.mark.asyncio
async def test_solution_feedback_mate_and_hard_to_catch(test_engine, clock) -> None:
    record = _record(score=0.42, loss=0.0, missed=5.0, type_swing=None, type_mate=True)
    async with _snapshot_setup(test_engine, [_BLUNDER_AT_ONE], record) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        data = (await _solution(s.token, s.session_id, 0)).json()
    assert data["feedback"]["type_line"] == "missed_mate"
    assert data["feedback"]["hard_to_catch"] is True
    assert data["feedback"]["score"] == pytest.approx(0.42, abs=1e-6)


@pytest.mark.asyncio
async def test_solution_false_alarm_of_a_low_score_window_has_no_feedback(
    test_engine, clock
) -> None:
    """D-05: the unreached low-score blunder stays withheld, no feedback key at all."""
    record = _record(score=0.3, loss=0.0, missed=5.0, type_swing=None, type_mate=True)
    async with _snapshot_setup(test_engine, [_BLUNDER_AT_THREE], record) as s:
        await _started(s)
        alarm = await _ok(s, 1, "blunder")  # the first judged move is fine: a false alarm
        assert alarm["outcome"] == "false_alarm"
        data = (await _solution(s.token, s.session_id, 0)).json()
    assert set(data) == _FALSE_ALARM_KEYS
    assert not _all_keys(data) & {"feedback", "type_line", "hard_to_catch", "facepalm_score"}


@pytest.mark.asyncio
async def test_solution_feedback_survives_the_game_delete(test_engine, clock) -> None:
    record = _record(score=0.42, loss=3.0, missed=0.0, type_swing=3, type_mate=False)
    async with _snapshot_setup(test_engine, [_BLUNDER_AT_ONE], record) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        before = (await _solution(s.token, s.session_id, 0)).json()
        await delete_games(test_engine, s.game_ids)
        after = (await _solution(s.token, s.session_id, 0)).json()
    assert before["game_id"] is not None and after["game_id"] is None
    assert after["feedback"] == before["feedback"]
    assert after["feedback"]["type_line"] == "allowed_material"
    assert after["feedback"]["hard_to_catch"] is True
