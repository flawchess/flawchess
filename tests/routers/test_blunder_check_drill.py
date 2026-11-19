"""Integration tests for the blunder-check drill: window start, answers and finish (Phase 249-04).

Sessions are built directly with `insert_session` from seeded games, so every window shape is
deterministic (no composer randomness). The dev clock is driven through
`app.dependency_overrides[dev_now_utc]` with a mutable clock.

Coverage (this module grows task by task):
- test_tracer_*  : start a window and catch a position-1 blunder (+3 and the better-move task)
"""

from __future__ import annotations

import asyncio
import datetime
import io
import random
from collections.abc import Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import chess.pgn
import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.models.blunder_check import (
    AnswerResult,
    BlunderCheckAnswer,
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.game_position import GamePosition
from app.repositories.blunder_check_repository import NewWindow, insert_session
from app.services import blunder_check_selection
from app.services.blunder_check_candidates import points_possible
from app.services.blunder_check_grading import (
    ANSWER_CEILING_S,
    MOVE_TIMER_SECONDS,
    MS_PER_SECOND,
    judged_ply,
)
from app.services.blunder_check_rules import LEAD_IN_PLIES, SlotPlan, WindowShape
from app.services.blunder_check_selection import build_snapshot
from tests.blunder_check_seed import (
    SEED_PGN,
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    register_user,
    seed_judged_game,
    with_user_blunder,
)

_T0 = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)
_SEED_ROWS = 61
_BLUNDER_DROP_CP = 600
_START_KEYS = {
    "position",
    "start_fen",
    "orientation",
    "lead_in_ucis",
    "answered",
    "prompt",
    "timer_remaining_ms",
    "move_timer_seconds",
    "window_points",
    "session_points",
    "better_move",
    "awaiting_ready",
    "prior_uci",
}
_ANSWER_KEYS = {
    "move_index",
    "result",
    "points_awarded",
    "points_forfeited",
    "window_points",
    "session_points",
    "window_ended",
    "outcome",
    "reply_uci",
    "next_prompt",
    "timer_remaining_ms",
    "better_move",
}
_BASE = "/api/blunder-check/sessions"
_SECONDS_PER_DAY = 24 * 60 * 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Clock:
    """A mutable dev clock: every request sees `now`."""

    def __init__(self) -> None:
        self.now = _T0

    def advance(self, seconds: float) -> None:
        self.now += datetime.timedelta(seconds=seconds)


@pytest.fixture
def clock() -> Iterator[_Clock]:
    c = _Clock()
    app.dependency_overrides[dev_now_utc] = lambda: c.now
    yield c
    app.dependency_overrides.pop(dev_now_utc, None)


@dataclass(frozen=True)
class _Spec:
    """One window: first judged ply (even: the user is white), length and blunder position."""

    first_ply: int
    length: int
    blunder_position: int | None


@dataclass(frozen=True)
class _Setup:
    user_id: int
    token: str
    session_id: int
    game_ids: list[int]


def _mainline_ucis() -> list[str]:
    game = chess.pgn.read_game(io.StringIO(SEED_PGN))
    assert game is not None
    return [move.uci() for move in game.mainline_moves()]


async def _best_move_at(test_engine, game_id: int, ply: int) -> str:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        row = (
            await session.execute(
                select(GamePosition.best_move).where(
                    GamePosition.game_id == game_id, GamePosition.ply == ply
                )
            )
        ).scalar_one()
    assert row is not None
    return row


async def _seed_window_game(test_engine, user_id: int, blunder_ply: int | None) -> int:
    evals = flat_evals(_SEED_ROWS, 0)
    blunders: list[SeedBlunder] = []
    if blunder_ply is not None:
        evals = with_user_blunder(evals, blunder_ply, _BLUNDER_DROP_CP)
        blunders = [SeedBlunder(ply=blunder_ply)]
    return await seed_judged_game(test_engine, user_id=user_id, evals_cp=evals, blunders=blunders)


async def _new_window(test_engine, user_id: int, position: int, spec: _Spec) -> NewWindow:
    blunder_ply = (
        None if spec.blunder_position is None else judged_ply(spec.first_ply, spec.blunder_position)
    )
    last_ply = blunder_ply if blunder_ply is not None else judged_ply(spec.first_ply, spec.length)
    snapshot = build_snapshot(SEED_PGN, spec.first_ply, last_ply)
    assert snapshot is not None
    game_id = await _seed_window_game(test_engine, user_id, blunder_ply)
    shape = WindowShape(spec.length, spec.blunder_position)
    return NewWindow(
        position=position,
        game_id=game_id,
        is_own=True,
        window_length=spec.length,
        blunder_position=spec.blunder_position,
        first_ply=spec.first_ply,
        blunder_ply=blunder_ply,
        window_case=WindowCase.HERRING if blunder_ply is None else WindowCase.ALLOWED,
        mover_elo=1500,
        start_fen=snapshot.start_fen,
        move_ucis=snapshot.move_ucis,
        lead_in_plies=snapshot.lead_in_plies,
        prior_uci=snapshot.prior_uci,
        key_uci=None
        if blunder_ply is None
        else await _best_move_at(test_engine, game_id, blunder_ply),
        refutation_uci=None,
        points_possible=points_possible(shape),
    )


@asynccontextmanager
async def _setup(test_engine, specs: list[_Spec], *, user_id_token: tuple[int, str] | None = None):
    """A beta user with an open session of one window per spec; cleans up in `finally`."""
    user_id, token = user_id_token or await register_user(
        "bc-drill", beta=True, test_engine=test_engine
    )
    windows: list[NewWindow] = []
    session_id: int | None = None
    try:
        for position, spec in enumerate(specs):
            windows.append(await _new_window(test_engine, user_id, position, spec))
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


def _force_own_shape(monkeypatch, shape: WindowShape) -> None:
    """Every composed slot is an own slot of `shape` (the mix is the composer tests' concern)."""
    monkeypatch.setattr(
        blunder_check_selection, "draw_slot_plan", lambda rng: SlotPlan("own", shape)
    )
    monkeypatch.setattr(blunder_check_selection, "draw_blunder_shape", lambda rng: shape)
    monkeypatch.setattr(blunder_check_selection, "draw_herring_shape", lambda rng: shape)


async def _call(token: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(path, headers={"Authorization": f"Bearer {token}"}, json=body)


async def _start(token: str, session_id: int, position: int) -> httpx.Response:
    return await _call(token, f"{_BASE}/{session_id}/windows/{position}/start")


async def _begin(token: str, session_id: int, position: int) -> httpx.Response:
    return await _call(token, f"{_BASE}/{session_id}/windows/{position}/begin")


async def _answer(
    token: str,
    session_id: int,
    position: int,
    move_index: int,
    answer: str,
    *,
    client_elapsed_ms: int = 1500,
) -> httpx.Response:
    return await _call(
        token,
        f"{_BASE}/{session_id}/windows/{position}/answers",
        {"move_index": move_index, "answer": answer, "client_elapsed_ms": client_elapsed_ms},
    )


async def _window_row(test_engine, session_id: int, position: int) -> BlunderCheckWindow:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        return (
            await session.execute(
                select(BlunderCheckWindow).where(
                    BlunderCheckWindow.session_id == session_id,
                    BlunderCheckWindow.position == position,
                )
            )
        ).scalar_one()


async def _session_count(test_engine, user_id: int) -> int:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(BlunderCheckSession)
                .where(BlunderCheckSession.user_id == user_id)
            )
        ).scalar_one()


async def _answer_rows(test_engine, window_id: int) -> list[BlunderCheckAnswer]:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        rows = (
            await session.execute(
                select(BlunderCheckAnswer)
                .where(BlunderCheckAnswer.window_id == window_id)
                .order_by(BlunderCheckAnswer.move_index)
            )
        ).scalars()
        return list(rows)


# ---------------------------------------------------------------------------
# Tracer: start a window and catch a position-1 blunder
# ---------------------------------------------------------------------------

_BLUNDER_AT_ONE = _Spec(first_ply=40, length=3, blunder_position=1)
_BLUNDER_PLY = 40


@pytest.mark.asyncio
async def test_tracer_start_and_catch_position_one_blunder(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        start = await _start(s.token, s.session_id, 0)
        assert start.status_code == 200, start.text
        body = start.json()
        assert set(body) == _START_KEYS
        assert body["awaiting_ready"] is True
        assert body["timer_remaining_ms"] == _FULL_TIMER_MS
        assert len(body["lead_in_ucis"]) == LEAD_IN_PLIES
        assert body["lead_in_ucis"] == mainline[_BLUNDER_PLY - LEAD_IN_PLIES : _BLUNDER_PLY]
        assert body["prompt"] == {"move_index": 1, "move_uci": mainline[_BLUNDER_PLY]}
        assert body["orientation"] == "white"
        # The move before the start position, for the Ready gate's last-move highlight.
        assert body["prior_uci"] == mainline[_BLUNDER_PLY - LEAD_IN_PLIES - 1]
        assert body["answered"] == []
        assert body["window_points"] == 0

        begun = await _begin(s.token, s.session_id, 0)
        assert begun.status_code == 200, begun.text
        assert begun.json()["awaiting_ready"] is False

        resp = await _answer(s.token, s.session_id, 0, 1, "blunder")
        assert resp.status_code == 200, resp.text
        answer = resp.json()
        assert set(answer) == _ANSWER_KEYS
        assert answer["result"] == "caught"
        assert answer["points_awarded"] == 3
        assert answer["window_ended"] is True
        assert answer["outcome"] == "caught"
        assert answer["reply_uci"] is None
        assert answer["next_prompt"] is None
        window = await _window_row(test_engine, s.session_id, 0)
        task = answer["better_move"]
        assert task["key_uci"] == window.key_uci
        board = chess.Board(start.json()["start_fen"])
        for uci in mainline[_BLUNDER_PLY - LEAD_IN_PLIES : _BLUNDER_PLY]:
            board.push_uci(uci)
        assert task["fen"] == board.fen()
        assert task["server_graded_moves"] == []

        rows = await _answer_rows(test_engine, window.id)
        assert [(r.move_index, r.result) for r in rows] == [(1, int(AnswerResult.CAUGHT))]
        assert rows[0].answered_at is not None
        assert window.outcome == int(WindowOutcome.CAUGHT)
        assert window.points_scored == 3


# ---------------------------------------------------------------------------
# Every answer path
# ---------------------------------------------------------------------------

_HERRING_3 = _Spec(first_ply=30, length=3, blunder_position=None)
_BLUNDER_AT_THREE = _Spec(first_ply=36, length=4, blunder_position=3)  # blunder ply 40
_BLUNDER_AT_THREE_PLY = 40
_FORBIDDEN_KEYS = {
    "game_id",
    "ply",
    "blunder_ply",
    "case",
    "window_case",
    "is_own",
    "window_length",
}
# Derived from the grading constants so a timer change cannot leave these inside or past the
# ceiling by accident (Phase 251 UAT moved the timer from 10 s to 12 s).
_BEFORE_CEILING_S = ANSWER_CEILING_S - 2
_PAST_CEILING_S = ANSWER_CEILING_S + 1
_RELOAD_DELAY_S = 6
_FULL_TIMER_MS = MOVE_TIMER_SECONDS * MS_PER_SECOND
_RELOAD_REMAINING_MS = _FULL_TIMER_MS - _RELOAD_DELAY_S * MS_PER_SECOND


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


async def _started(s: _Setup, position: int = 0) -> dict[str, Any]:
    """Start a window the way the client does: press Ready when the start lands on the gate.

    A reload after Ready (or a caught window waiting for its better move) is not on the gate,
    so its start body is returned as is and begin is not called.
    """
    resp = await _start(s.token, s.session_id, position)
    assert resp.status_code == 200, resp.text
    if not resp.json()["awaiting_ready"]:
        return resp.json()
    begun = await _begin(s.token, s.session_id, position)
    assert begun.status_code == 200, begun.text
    return begun.json()


async def _ok(s: _Setup, move_index: int, answer: str, position: int = 0) -> dict[str, Any]:
    resp = await _answer(s.token, s.session_id, position, move_index, answer)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_herring_window_all_safe_clears_with_replies(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        first = await _ok(s, 1, "safe")
        second = await _ok(s, 2, "safe")
        third = await _ok(s, 3, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
    assert first["result"] == "correct_safe" and first["points_awarded"] == 1
    assert first["reply_uci"] == mainline[31]
    assert first["next_prompt"] == {"move_index": 2, "move_uci": mainline[32]}
    assert first["window_ended"] is False and first["outcome"] is None
    assert second["reply_uci"] == mainline[33]
    assert second["next_prompt"] == {"move_index": 3, "move_uci": mainline[34]}
    assert third["window_ended"] is True and third["outcome"] == "cleared"
    assert third["next_prompt"] is None and third["timer_remaining_ms"] is None
    assert third["window_points"] == 3 and third["session_points"] == 3
    assert window.outcome == int(WindowOutcome.CLEARED) and window.points_scored == 3


@pytest.mark.asyncio
async def test_missed_blunder_forfeits_the_window_safe_points(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        await _ok(s, 2, "safe")
        missed = await _ok(s, 3, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
    assert missed["result"] == "missed"
    assert missed["points_forfeited"] == 2 and missed["points_awarded"] == 0
    assert missed["window_points"] == 0 and missed["session_points"] == 0
    assert missed["window_ended"] is True and missed["outcome"] == "missed"
    assert missed["reply_uci"] is None and missed["better_move"] is None
    assert window.outcome == int(WindowOutcome.MISSED) and window.points_scored == 0


@pytest.mark.asyncio
async def test_timeout_on_safe_costs_one_point_and_the_window_continues(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        timed_out = await _ok(s, 2, "timeout")
        caught = await _ok(s, 3, "blunder")
    assert timed_out["result"] == "timeout_safe"
    assert timed_out["points_awarded"] == 0 and timed_out["points_forfeited"] == 1
    assert timed_out["window_points"] == 0
    assert timed_out["window_ended"] is False and timed_out["next_prompt"]["move_index"] == 3
    assert caught["result"] == "caught" and caught["points_awarded"] == 3
    assert caught["window_points"] == 3
    assert caught["better_move"]["key_uci"] is not None


@pytest.mark.asyncio
async def test_timeout_on_the_blunder_counts_as_missed(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _started(s)
        result = await _ok(s, 1, "timeout")
    assert result["result"] == "timeout_blunder"
    assert result["outcome"] == "missed" and result["window_ended"] is True
    assert result["better_move"] is None


@pytest.mark.asyncio
async def test_false_alarm_keeps_safe_points_and_the_blunder_is_never_served_again(
    test_engine, clock, monkeypatch
) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        alarm = await _ok(s, 2, "blunder")
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
        assert alarm["result"] == "false_alarm" and alarm["points_awarded"] == 0
        assert alarm["window_points"] == 1 and alarm["points_forfeited"] == 0
        assert alarm["window_ended"] is True and alarm["outcome"] == "false_alarm"
        assert alarm["reply_uci"] is None
        assert window.outcome == int(WindowOutcome.FALSE_ALARM) and window.points_scored == 1
        # The blunder ply was never prompted, so no answer row exists for it ...
        assert _BLUNDER_AT_THREE_PLY not in {row.ply for row in rows}
        # ... yet 250 D-17 counts it as served (the window carrying it was served), so the
        # composer never anchors a window on that blunder for the same user again.
        _force_own_shape(monkeypatch, WindowShape(3, 1))
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            windows = await blunder_check_selection.compose_windows(
                session, user_id=s.user_id, rng=random.Random(0)
            )
    assert all(w.blunder_ply != _BLUNDER_AT_THREE_PLY for w in windows)


@pytest.mark.asyncio
async def test_ceiling_answer_past_it_is_graded_as_a_timeout(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        await _started(s)
        clock.advance(_PAST_CEILING_S)
        late = await _ok(s, 1, "blunder")
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert late["result"] == "timeout_blunder" and late["outcome"] == "missed"
    assert rows[0].answer == 1  # the submitted kind is stored, the grade is the timeout
    assert rows[0].server_elapsed_ms == _PAST_CEILING_S * 1000


@pytest.mark.asyncio
async def test_ceiling_allows_the_animation_before_a_fresh_prompt(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        clock.advance(_BEFORE_CEILING_S)
        result = await _ok(s, 1, "safe")
    assert result["result"] == "correct_safe"


@pytest.mark.asyncio
async def test_ceiling_reload_keeps_the_original_prompt_stamp(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        first = await _started(s)
        clock.advance(_RELOAD_DELAY_S)
        second = await _started(s)
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert first["timer_remaining_ms"] == _FULL_TIMER_MS
    assert second["timer_remaining_ms"] == _RELOAD_REMAINING_MS
    assert len(rows) == 1 and rows[0].prompted_at == _T0
    assert second["prompt"] == first["prompt"]


@pytest.mark.asyncio
async def test_ceiling_reload_after_answers_returns_answered_moves_and_real_timer(
    test_engine, clock
) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        clock.advance(_RELOAD_DELAY_S)
        reload_body = await _started(s)
    assert reload_body["answered"] == [
        {
            "move_index": 1,
            "move_uci": mainline[30],
            "reply_uci": mainline[31],
            "result": "correct_safe",
            "points_awarded": 1,
            "points_forfeited": 0,
        }
    ]
    assert reload_body["prompt"] == {"move_index": 2, "move_uci": mainline[32]}
    assert reload_body["timer_remaining_ms"] == _RELOAD_REMAINING_MS
    assert reload_body["window_points"] == 1


@pytest.mark.asyncio
async def test_payload_shapes_leak_no_key_material(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_THREE]) as s:
        gate = (await _start(s.token, s.session_id, 0)).json()
        start = await _started(s)
        first = await _ok(s, 1, "safe")
        reload_body = await _started(s)
        second = await _ok(s, 2, "safe")
    assert set(gate) == _START_KEYS and set(start) == _START_KEYS
    assert set(reload_body) == _START_KEYS
    assert set(first) == _ANSWER_KEYS and set(second) == _ANSWER_KEYS
    for body in (gate, start, first, reload_body, second):
        assert not (_all_keys(body) & _FORBIDDEN_KEYS)
    # Lead-in plus exactly one arrow: no later move of the window is sent before it is answered.
    assert len(start["lead_in_ucis"]) == LEAD_IN_PLIES
    assert start["answered"] == []
    assert set(start["prompt"]) == {"move_index", "move_uci"}


@pytest.mark.asyncio
async def test_double_submit_is_rejected_and_awards_nothing_twice(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        await _ok(s, 1, "safe")
        again = await _answer(s.token, s.session_id, 0, 1, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
    assert again.status_code == 409 and again.json()["detail"] == "stale_prompt"
    assert window.points_scored == 1


@pytest.mark.asyncio
async def test_double_submit_concurrent_yields_one_award(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        first, second = await asyncio.gather(
            _answer(s.token, s.session_id, 0, 1, "safe"),
            _answer(s.token, s.session_id, 0, 1, "safe"),
        )
        window = await _window_row(test_engine, s.session_id, 0)
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert window.points_scored == 1


@pytest.mark.asyncio
async def test_order_prompts_must_be_answered_in_sequence(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        skipped = await _answer(s.token, s.session_id, 0, 2, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
    assert skipped.status_code == 409 and skipped.json()["detail"] == "stale_prompt"
    assert window.points_scored == 0


@pytest.mark.asyncio
async def test_order_windows_must_end_before_the_next_starts(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE, _HERRING_3]) as s:
        blocked = await _start(s.token, s.session_id, 1)
        assert blocked.status_code == 409
        assert blocked.json()["detail"] == "previous_window_open"
        await _started(s, 0)
        await _ok(s, 1, "blunder")
        allowed = await _start(s.token, s.session_id, 1)
    assert allowed.status_code == 200, allowed.text


@pytest.mark.asyncio
async def test_order_answer_before_start_and_after_end_are_rejected(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        early = await _answer(s.token, s.session_id, 0, 1, "blunder")
        await _started(s)
        # A missed blunder ends the window for good (a caught one stays open for its better move).
        await _ok(s, 1, "safe")
        late = await _answer(s.token, s.session_id, 0, 1, "blunder")
        restart = await _start(s.token, s.session_id, 0)
    assert early.status_code == 409 and early.json()["detail"] == "not_started"
    assert late.status_code == 409 and late.json()["detail"] == "window_ended"
    assert restart.status_code == 409 and restart.json()["detail"] == "window_ended"


@pytest.mark.asyncio
async def test_idor_another_users_session_and_window_answer_404(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        other_id, other_token = await register_user(
            "bc-drill-other", beta=True, test_engine=test_engine
        )
        started = await _start(other_token, s.session_id, 0)
        answered = await _answer(other_token, s.session_id, 0, 1, "safe")
        begun = await _begin(other_token, s.session_id, 0)
        unknown_begin = await _begin(s.token, s.session_id, 7)
        unknown_window = await _start(s.token, s.session_id, 7)
        unknown_session = await _start(s.token, s.session_id + 10_000_000, 0)
        window = await _window_row(test_engine, s.session_id, 0)
    assert other_id != s.user_id
    assert started.status_code == 404 and answered.status_code == 404
    assert begun.status_code == 404 and unknown_begin.status_code == 404
    assert unknown_window.status_code == 404 and unknown_session.status_code == 404
    assert window.started_at is None


@pytest.mark.asyncio
async def test_payload_request_bounds_reject_bad_input(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _started(s)
        bad_index = await _answer(s.token, s.session_id, 0, 0, "safe")
        bad_elapsed = await _answer(s.token, s.session_id, 0, 1, "safe", client_elapsed_ms=-1)
        bad_kind = await _answer(s.token, s.session_id, 0, 1, "maybe")
        huge_session = await _start(s.token, 2**31, 0)
    for resp in (bad_index, bad_elapsed, bad_kind, huge_session):
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Finish (D-14)
# ---------------------------------------------------------------------------

_SESSION_RESULT_KEYS = {"session_id", "session_points", "points_possible", "score_pct", "windows"}
_WINDOW_RESULT_KEYS = {"position", "outcome", "points_scored", "points_possible"}


async def _finish(token: str, session_id: int) -> httpx.Response:
    return await _call(token, f"{_BASE}/{session_id}/finish")


async def _play_cleared_and_false_alarm(s: _Setup) -> None:
    """Window 0: a herring answered all safe (3 of 3). Window 1: safe, then a false alarm."""
    await _started(s, 0)
    for move_index in (1, 2, 3):
        await _ok(s, move_index, "safe", position=0)
    await _started(s, 1)
    await _ok(s, 1, "safe", position=1)
    await _ok(s, 2, "blunder", position=1)


@pytest.mark.asyncio
async def test_finish_session_reports_points_possible_and_score_pct(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3, _BLUNDER_AT_THREE]) as s:
        await _play_cleared_and_false_alarm(s)
        resp = await _finish(s.token, s.session_id)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        again = await _finish(s.token, s.session_id)
    assert set(body) == _SESSION_RESULT_KEYS
    assert all(set(w) == _WINDOW_RESULT_KEYS for w in body["windows"])
    # 3 of 3 plus 1 of (2 safe + 3 blunder + 2 better move): the unreached 3 + 2 still count.
    assert body["session_points"] == 4
    assert body["points_possible"] == 10
    assert body["score_pct"] == 40
    assert [(w["outcome"], w["points_scored"], w["points_possible"]) for w in body["windows"]] == [
        ("cleared", 3, 3),
        ("false_alarm", 1, 7),
    ]
    assert again.status_code == 200 and again.json() == body


@pytest.mark.asyncio
async def test_finish_with_an_unended_window_is_rejected(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3, _BLUNDER_AT_ONE]) as s:
        await _started(s, 0)
        for move_index in (1, 2, 3):
            await _ok(s, move_index, "safe", position=0)
        resp = await _finish(s.token, s.session_id)
        session = await _call(s.token, f"{_BASE}")
    assert resp.status_code == 409 and resp.json()["detail"] == "windows_open"
    assert session.status_code == 200  # the open session is still resumable


@pytest.mark.asyncio
async def test_finish_idor_and_unknown_session_answer_404(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        _, other_token = await register_user("bc-drill-fin", beta=True, test_engine=test_engine)
        foreign = await _finish(other_token, s.session_id)
        unknown = await _finish(s.token, s.session_id + 10_000_000)
    assert foreign.status_code == 404 and unknown.status_code == 404


@pytest.mark.asyncio
async def test_finish_then_start_returns_done_session_until_next_day(
    test_engine, clock, monkeypatch
) -> None:
    # The next-day session needs the leftover herring runs of the own game: force own herrings.
    _force_own_shape(monkeypatch, WindowShape(3, None))
    async with _setup(test_engine, [_HERRING_3, _BLUNDER_AT_THREE]) as s:
        await _play_cleared_and_false_alarm(s)
        assert (await _finish(s.token, s.session_id)).status_code == 200
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            headers = {"Authorization": f"Bearer {s.token}"}
            open_after = await client.get(f"{_BASE}/open", headers=headers)
        # Same session day: Start returns the finished session and composes nothing.
        same_day = await _call(s.token, _BASE)
        sessions_after_same_day = await _session_count(test_engine, s.user_id)
        # Past the session's expires_on: Start composes a fresh session.
        clock.advance(_SECONDS_PER_DAY)
        next_day = await _call(s.token, _BASE)
        fresh_id = next_day.json()["session_id"] if next_day.status_code == 200 else None
        try:
            assert open_after.status_code == 200 and open_after.json() is None
            assert same_day.status_code == 200, same_day.text
            assert same_day.json()["session_id"] == s.session_id
            assert sessions_after_same_day == 1
            assert next_day.status_code == 200, next_day.text
            assert fresh_id != s.session_id
        finally:
            await delete_blunder_check_sessions(test_engine, [fresh_id] if fresh_id else [])


async def _start_first(token: str, session_id: int) -> httpx.Response:
    return await _start(token, session_id, 0)


async def _begin_first(token: str, session_id: int) -> httpx.Response:
    return await _begin(token, session_id, 0)


@pytest.mark.asyncio
async def test_non_beta_user_reaches_the_drill_routes(test_engine, clock) -> None:
    """D-18: no drill route answers 403 for a missing beta flag; an unknown session is a 404."""
    _, token = await register_user("bc-drill-nonbeta", beta=False, test_engine=test_engine)
    responses = [
        await _start(token, 1, 0),
        await _begin(token, 1, 0),
        await _answer(token, 1, 0, 1, "safe"),
        await _finish(token, 1),
    ]
    assert [resp.status_code for resp in responses] == [404, 404, 404, 404]


@pytest.mark.asyncio
async def test_guest_reaches_the_drill_routes(test_engine, clock) -> None:
    """D-18: a guest is an authenticated user; the drill routes answer the scoped 404."""
    _, token = await register_user(
        "bc-drill-guest", beta=False, test_engine=test_engine, guest=True
    )
    responses = [
        await _start(token, 1, 0),
        await _begin(token, 1, 0),
        await _answer(token, 1, 0, 1, "safe"),
        await _finish(token, 1),
    ]
    assert [resp.status_code for resp in responses] == [404, 404, 404, 404]


@pytest.mark.asyncio
async def test_non_beta_user_cannot_touch_another_users_session(test_engine, clock) -> None:
    """T-251-09: with the gate gone, scoping by the caller's id still answers 404 (ASVS V4)."""
    async with _setup(test_engine, [_HERRING_3]) as s:
        _, other_token = await register_user(
            "bc-drill-nonbeta-idor", beta=False, test_engine=test_engine
        )
        _, guest_token = await register_user(
            "bc-drill-guest-idor", beta=False, test_engine=test_engine, guest=True
        )
        statuses = [
            (await call(token, s.session_id)).status_code
            for token in (other_token, guest_token)
            for call in (_finish, _start_first, _begin_first)
        ]
        window = await _window_row(test_engine, s.session_id, 0)
    assert statuses == [404] * 6
    assert window.started_at is None


# ---------------------------------------------------------------------------
# Ready gate (quick 261117-sfh): start opens it, begin starts the clock
# ---------------------------------------------------------------------------

_GATE_STUDY_S = 120  # well past ANSWER_CEILING_S


@pytest.mark.asyncio
async def test_ready_gate_start_opens_the_gate_without_a_prompt(test_engine, clock) -> None:
    mainline = _mainline_ucis()
    async with _setup(test_engine, [_HERRING_3]) as s:
        gate = await _start(s.token, s.session_id, 0)
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert gate.status_code == 200, gate.text
    body = gate.json()
    assert body["awaiting_ready"] is True
    assert body["answered"] == []
    assert body["prompt"] == {"move_index": 1, "move_uci": mainline[30]}
    assert body["timer_remaining_ms"] == _FULL_TIMER_MS
    assert window.started_at == _T0
    assert rows == []


@pytest.mark.asyncio
async def test_ready_gate_reload_shows_the_gate_again_with_no_time_lost(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        first = (await _start(s.token, s.session_id, 0)).json()
        clock.advance(_GATE_STUDY_S)
        again = (await _start(s.token, s.session_id, 0)).json()
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert first["awaiting_ready"] is True and again["awaiting_ready"] is True
    assert again["timer_remaining_ms"] == _FULL_TIMER_MS
    assert again["prompt"] == first["prompt"]
    assert rows == []
    assert window.started_at == _T0


@pytest.mark.asyncio
async def test_ready_gate_time_never_counts_toward_the_answer_ceiling(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _start(s.token, s.session_id, 0)
        clock.advance(_GATE_STUDY_S)
        begun = (await _begin(s.token, s.session_id, 0)).json()
        clock.advance(_BEFORE_CEILING_S)
        result = await _ok(s, 1, "safe")
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert begun["awaiting_ready"] is False
    assert begun["timer_remaining_ms"] == _FULL_TIMER_MS
    # Graded on its merits: with the clock at the start stamp this would be a timeout.
    assert result["result"] == "correct_safe"
    assert rows[0].prompted_at == _T0 + datetime.timedelta(seconds=_GATE_STUDY_S)
    assert rows[0].server_elapsed_ms == _BEFORE_CEILING_S * 1000


@pytest.mark.asyncio
async def test_ready_gate_begin_is_idempotent_and_never_buys_time(test_engine, clock) -> None:
    async with _setup(test_engine, [_HERRING_3]) as s:
        await _start(s.token, s.session_id, 0)
        clock.advance(_GATE_STUDY_S)
        first = (await _begin(s.token, s.session_id, 0)).json()
        clock.advance(_RELOAD_DELAY_S)
        second = (await _begin(s.token, s.session_id, 0)).json()
        reload_body = (await _start(s.token, s.session_id, 0)).json()
        window = await _window_row(test_engine, s.session_id, 0)
        rows = await _answer_rows(test_engine, window.id)
    assert first["timer_remaining_ms"] == _FULL_TIMER_MS
    assert (
        second["awaiting_ready"] is False and second["timer_remaining_ms"] == _RELOAD_REMAINING_MS
    )
    assert reload_body["awaiting_ready"] is False
    assert reload_body["timer_remaining_ms"] == _RELOAD_REMAINING_MS
    assert reload_body["prompt"] == first["prompt"]
    assert len(rows) == 1
    assert rows[0].prompted_at == _T0 + datetime.timedelta(seconds=_GATE_STUDY_S)


@pytest.mark.asyncio
async def test_ready_gate_answer_and_begin_out_of_order_are_rejected(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE]) as s:
        before_start = await _begin(s.token, s.session_id, 0)
        await _start(s.token, s.session_id, 0)
        during_gate = await _answer(s.token, s.session_id, 0, 1, "blunder")
        window = await _window_row(test_engine, s.session_id, 0)
        gate_rows = await _answer_rows(test_engine, window.id)
        await _begin(s.token, s.session_id, 0)
        # A missed blunder ends the window for good.
        await _ok(s, 1, "safe")
        after_end = await _begin(s.token, s.session_id, 0)
    assert before_start.status_code == 409 and before_start.json()["detail"] == "not_started"
    assert during_gate.status_code == 409 and during_gate.json()["detail"] == "stale_prompt"
    assert window.points_scored == 0 and gate_rows == []
    assert after_end.status_code == 409 and after_end.json()["detail"] == "window_ended"


@pytest.mark.asyncio
async def test_ready_gate_every_window_opens_on_the_gate(test_engine, clock) -> None:
    async with _setup(test_engine, [_BLUNDER_AT_ONE, _HERRING_3]) as s:
        await _started(s, 0)
        await _ok(s, 1, "safe")  # a missed blunder ends window 0
        second = await _start(s.token, s.session_id, 1)
        second_window = await _window_row(test_engine, s.session_id, 1)
        second_rows = await _answer_rows(test_engine, second_window.id)
    assert second.status_code == 200, second.text
    assert second.json()["awaiting_ready"] is True
    assert second_rows == []
