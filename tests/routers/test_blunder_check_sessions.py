"""Integration tests for the blunder-check router's beta gate and open-session read.

Coverage:
- test_open_session_anon_401          : no token -> 401 (D-01)
- test_open_session_non_beta_403      : logged-in user with beta_enabled false -> 403 (D-01)
- test_open_session_beta_no_session_null : beta user without a session -> 200, body null
- test_open_session_beta_returns_progress : exact response key sets, derived fields
- test_open_session_never_returns_other_users_session : user-id scoping (T-249-03)
"""

from __future__ import annotations

import asyncio
import datetime
import random
import uuid

import chess
import httpx
import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.user import User
from app.services import blunder_check_selection
from app.services.blunder_check_candidates import points_possible
from app.services.blunder_check_rules import BLUNDER_CHECK_SESSION_WINDOWS, SlotPlan, WindowShape
from tests.blunder_check_seed import (
    SeedBlunder,
    delete_blunder_check_sessions,
    delete_games,
    flat_evals,
    seed_judged_game,
    with_user_blunder,
)

_URL = "/api/blunder-check/sessions/open"
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_SESSION_KEYS = {"session_id", "window_count", "current_position", "session_points", "windows"}
_WINDOW_KEYS = {"position", "state", "outcome", "points_scored"}
_TS = datetime.datetime(2026, 11, 10, 12, 0, tzinfo=datetime.timezone.utc)


async def _register(prefix: str, *, beta: bool, test_engine) -> tuple[int, str]:
    """Register + log in a user over HTTP; optionally flip beta_enabled via direct UPDATE."""
    email = f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"
    password = "testpass123!"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (200, 201), reg.text
        user_id = int(reg.json()["id"])
        login = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": password}
        )
        assert login.status_code == 200, login.text
        token = str(login.json()["access_token"])
    if beta:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            await session.execute(update(User).where(User.id == user_id).values(beta_enabled=True))
            await session.commit()
    return user_id, token


async def _insert_session(
    test_engine, user_id: int, outcomes: list[WindowOutcome | None], points: list[int]
) -> int:
    """Insert an open session with one window per outcome. Returns the session id."""
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            header = BlunderCheckSession(user_id=user_id, window_count=len(outcomes))
            session.add(header)
            await session.flush()
            for position, (outcome, scored) in enumerate(zip(outcomes, points, strict=True)):
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
                        points_scored=scored,
                        outcome=None if outcome is None else int(outcome),
                        started_at=_TS if outcome is not None else None,
                    )
                )
            return header.id


async def _delete_sessions(test_engine, session_ids: list[int]) -> None:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            await session.execute(
                delete(BlunderCheckSession).where(BlunderCheckSession.id.in_(session_ids))
            )


async def _get(token: str | None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(_URL, headers=headers)


@pytest.mark.asyncio
async def test_open_session_anon_401() -> None:
    assert (await _get(None)).status_code == 401


@pytest.mark.asyncio
async def test_open_session_non_beta_403(test_engine) -> None:
    _, token = await _register("bc-nonbeta", beta=False, test_engine=test_engine)
    assert (await _get(token)).status_code == 403


@pytest.mark.asyncio
async def test_open_session_beta_no_session_null(test_engine) -> None:
    _, token = await _register("bc-beta-empty", beta=True, test_engine=test_engine)
    resp = await _get(token)
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_open_session_beta_returns_progress(test_engine) -> None:
    user_id, token = await _register("bc-beta-progress", beta=True, test_engine=test_engine)
    session_id = await _insert_session(
        test_engine, user_id, [WindowOutcome.MISSED, None], points=[3, 0]
    )
    # A missed window is done; a caught one would stay current until its better move is played.
    try:
        resp = await _get(token)
    finally:
        await _delete_sessions(test_engine, [session_id])
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == _SESSION_KEYS
    assert body["session_id"] == session_id
    assert body["window_count"] == 2
    assert body["current_position"] == 1
    assert body["session_points"] == 3
    assert [set(w) for w in body["windows"]] == [_WINDOW_KEYS, _WINDOW_KEYS]
    assert body["windows"][0] == {
        "position": 0,
        "state": "ended",
        "outcome": "missed",
        "points_scored": 3,
    }
    assert body["windows"][1]["state"] == "pending"
    assert body["windows"][1]["outcome"] is None


@pytest.mark.asyncio
async def test_open_session_never_returns_other_users_session(test_engine) -> None:
    owner_id, _ = await _register("bc-owner", beta=True, test_engine=test_engine)
    _, other_token = await _register("bc-other", beta=True, test_engine=test_engine)
    session_id = await _insert_session(test_engine, owner_id, [None], points=[0])
    try:
        resp = await _get(other_token)
    finally:
        await _delete_sessions(test_engine, [session_id])
    assert resp.status_code == 200
    assert resp.json() is None


# ---------------------------------------------------------------------------
# POST /sessions (plan 03 tracer): compose + persist from the user's own games
# ---------------------------------------------------------------------------

_START_URL = "/api/blunder-check/sessions"
_FORBIDDEN_KEYS = {"game_id", "ply", "case", "is_own"}
_USER_BLUNDER_PLY = 40  # user is white (even plies); 20 clean user moves precede it
_BLUNDER_DROP_CP = 600
_SEED_GAMES = 7
_RNG_SEED = 7


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


async def _seed_own_games(test_engine, user_id: int, count: int) -> list[int]:
    """`count` fully evaluated own games: a long clean stretch, then one findable user blunder."""
    evals = with_user_blunder(flat_evals(61, 0), _USER_BLUNDER_PLY, _BLUNDER_DROP_CP)
    return [
        await seed_judged_game(
            test_engine,
            user_id=user_id,
            evals_cp=evals,
            blunders=[SeedBlunder(ply=_USER_BLUNDER_PLY)],
        )
        for _ in range(count)
    ]


def _force_own_blunder_slots(monkeypatch) -> None:
    """Every slot is an own blunder window: these tests cover persistence and the API, not the
    mix (250 D-15 converts own slots to foreign, never the reverse, so a random plan with
    foreign slots would shorten a session that only has own supply)."""
    shape = WindowShape(3, 1)
    monkeypatch.setattr(
        blunder_check_selection, "draw_slot_plan", lambda rng: SlotPlan("own", shape)
    )
    monkeypatch.setattr(blunder_check_selection, "draw_blunder_shape", lambda rng: shape)
    monkeypatch.setattr(blunder_check_selection, "draw_herring_shape", lambda rng: shape)


async def _post(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(_START_URL, headers={"Authorization": f"Bearer {token}"})


async def _windows_of(test_engine, session_id: int) -> list[BlunderCheckWindow]:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        rows = (
            await session.execute(
                select(BlunderCheckWindow)
                .where(BlunderCheckWindow.session_id == session_id)
                .order_by(BlunderCheckWindow.position)
            )
        ).scalars()
        return list(rows)


def _board_at_ply(window: BlunderCheckWindow, ply: int) -> chess.Board:
    """Replay the window snapshot to the board BEFORE the move at `ply`."""
    board = chess.Board(window.start_fen)
    lead_start = window.first_ply - window.lead_in_plies
    for uci in window.move_ucis.split()[: ply - lead_start]:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)
    return board


@pytest.mark.asyncio
async def test_start_session_composes_six_own_windows(test_engine, monkeypatch) -> None:
    _force_own_blunder_slots(monkeypatch)
    monkeypatch.setattr(
        blunder_check_selection, "new_session_rng", lambda: random.Random(_RNG_SEED)
    )
    user_id, token = await _register("bc-start", beta=True, test_engine=test_engine)
    game_ids = await _seed_own_games(test_engine, user_id, _SEED_GAMES)
    session_id: int | None = None
    try:
        resp = await _post(token)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        session_id = body["session_id"]
        assert body["window_count"] == BLUNDER_CHECK_SESSION_WINDOWS
        assert set(body) == _SESSION_KEYS
        assert not (_all_keys(body) & _FORBIDDEN_KEYS)
        windows = await _windows_of(test_engine, session_id)
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, game_ids)
    assert [w.position for w in windows] == list(range(BLUNDER_CHECK_SESSION_WINDOWS))
    assert len({w.game_id for w in windows}) == BLUNDER_CHECK_SESSION_WINDOWS
    for window in windows:
        assert window.is_own is True
        chess.Board(window.start_fen)  # parses
        expected = points_possible(WindowShape(window.window_length, window.blunder_position))
        assert window.points_possible == expected
        last_judged = window.blunder_ply if window.blunder_ply is not None else window.first_ply
        _board_at_ply(window, last_judged)  # every snapshot move up to it is legal
        if window.blunder_ply is not None:
            board = _board_at_ply(window, window.blunder_ply)
            assert window.key_uci is not None
            assert chess.Move.from_uci(window.key_uci) in board.legal_moves


@pytest.mark.asyncio
async def test_start_session_non_beta_403(test_engine) -> None:
    _, token = await _register("bc-start-nonbeta", beta=False, test_engine=test_engine)
    assert (await _post(token)).status_code == 403


@pytest.mark.asyncio
async def test_start_session_no_supply_409(test_engine) -> None:
    _, token = await _register("bc-start-empty", beta=True, test_engine=test_engine)
    resp = await _post(token)
    assert resp.status_code == 409


async def _window_count(test_engine, user_id: int) -> int:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(BlunderCheckWindow)
                .where(BlunderCheckWindow.user_id == user_id)
            )
        ).scalar_one()


@pytest.mark.asyncio
async def test_resume_second_post_returns_same_session(test_engine, monkeypatch) -> None:
    _force_own_blunder_slots(monkeypatch)
    user_id, token = await _register("bc-resume", beta=True, test_engine=test_engine)
    game_ids = await _seed_own_games(test_engine, user_id, _SEED_GAMES)
    session_id: int | None = None
    try:
        first = await _post(token)
        assert first.status_code == 200, first.text
        session_id = first.json()["session_id"]
        rows_after_first = await _window_count(test_engine, user_id)
        second = await _post(token)
        assert second.status_code == 200, second.text
        assert second.json()["session_id"] == session_id
        assert await _window_count(test_engine, user_id) == rows_after_first
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, game_ids)


@pytest.mark.asyncio
async def test_concurrent_start_yields_one_open_session(test_engine, monkeypatch) -> None:
    _force_own_blunder_slots(monkeypatch)
    """Two simultaneous POSTs from independent clients (own DB session each) leave one open row."""
    user_id, token = await _register("bc-concurrent", beta=True, test_engine=test_engine)
    game_ids = await _seed_own_games(test_engine, user_id, _SEED_GAMES)
    session_id: int | None = None
    try:
        resp_a, resp_b = await asyncio.gather(_post(token), _post(token))
        assert resp_a.status_code == 200, resp_a.text
        assert resp_b.status_code == 200, resp_b.text
        session_id = resp_a.json()["session_id"]
        assert resp_b.json()["session_id"] == session_id
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session:
            open_count = (
                await session.execute(
                    select(func.count())
                    .select_from(BlunderCheckSession)
                    .where(
                        BlunderCheckSession.user_id == user_id, BlunderCheckSession.status == "open"
                    )
                )
            ).scalar_one()
        assert open_count == 1
        assert await _window_count(test_engine, user_id) == BLUNDER_CHECK_SESSION_WINDOWS
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, game_ids)


@pytest.mark.asyncio
async def test_open_session_after_start_reports_pending_windows(test_engine, monkeypatch) -> None:
    _force_own_blunder_slots(monkeypatch)
    user_id, token = await _register("bc-open-after", beta=True, test_engine=test_engine)
    game_ids = await _seed_own_games(test_engine, user_id, _SEED_GAMES)
    session_id: int | None = None
    try:
        started = await _post(token)
        assert started.status_code == 200, started.text
        session_id = started.json()["session_id"]
        resp = await _get(token)
    finally:
        await delete_blunder_check_sessions(test_engine, [session_id] if session_id else [])
        await delete_games(test_engine, game_ids)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["current_position"] == 0
    assert body["session_points"] == 0
    assert [w["state"] for w in body["windows"]] == ["pending"] * BLUNDER_CHECK_SESSION_WINDOWS
