"""Integration tests for GET /api/library/tactic-comparison (Phase 126).

Coverage:
- test_200_shape              : authenticated request returns 200 with per-TC tcs[] and analyzed_gate (Phase 239)
- test_401_unauthenticated    : no-auth returns 401
- test_422_date_guard         : from_date > to_date returns 422
- test_tactic_families_filter : tactic_families param accepted, response is valid
"""

from __future__ import annotations

import datetime
import uuid

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game
from app.models.game_flaw import GameFlaw

ENDPOINT = "/api/library/tactic-comparison"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(email: str, password: str = "testpass123!") -> tuple[int, str]:
    """Register a user via HTTP and return (user_id, auth_token)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code in (200, 201), f"register failed: {reg.text}"
        user_id = int(reg.json()["id"])

        login = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200, f"login failed: {login.text}"
        token = str(login.json()["access_token"])
    return user_id, token


async def _seed_games(
    test_engine, user_id: int, count: int = 1, *, analyzed: bool = False
) -> list[int]:
    """Insert game rows for the given user via a committed session. Returns game IDs.

    The seeded games default to full_evals_completed_at IS NULL AND
    lichess_evals_at IS NULL, which makes them needs-engine candidates in the
    GLOBAL tier-3 eval lottery (_claim_tier3_derived). Leaving them in the shared
    per-run test DB pollutes the eval_queue lottery tests, which assume their own
    inserted game is the only eligible candidate — caller MUST delete via
    _delete_games in a finally (see test_eval_queue.py for the same discipline).
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    game_ids: list[int] = []
    async with session_maker() as session:
        async with session.begin():
            for _ in range(count):
                game = Game(
                    user_id=user_id,
                    platform="lichess",
                    platform_game_id=str(uuid.uuid4()),
                    platform_url="https://lichess.org/test",
                    pgn="1. e4 e5 *",
                    result="1-0",
                    user_color="white",
                    time_control_str="600+0",
                    time_control_bucket="blitz",
                    time_control_seconds=600,
                    base_time_seconds=600,
                    increment_seconds=0.0,
                    rated=True,
                    is_computer_game=False,
                    ply_count=40,
                    # Analyzed marker for _analyzed_game_ids_subquery (full-analysis lane).
                    full_evals_completed_at=(
                        datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
                        if analyzed
                        else None
                    ),
                    # WR-01: the tactic population also requires blobs_completed_at.
                    blobs_completed_at=(
                        datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
                        if analyzed
                        else None
                    ),
                )
                session.add(game)
                await session.flush()
                game_ids.append(game.id)
    return game_ids


async def _delete_games(test_engine, game_ids: list[int]) -> None:
    """Delete the given games (committed cleanup) so they don't leak into the
    global tier-3 eval lottery shared by other test files."""
    if not game_ids:
        return
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(Game).where(Game.id.in_(game_ids)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_shape(test_engine) -> None:
    """Authenticated request returns 200 with the per-TC response keys (Phase 239 D-02)."""
    email = f"tac-cmp-router-shape-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    game_ids = await _seed_games(test_engine, user_id, count=3, analyzed=True)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"tcs", "analyzed_gate"}
        assert isinstance(body["analyzed_gate"], int)
        assert [tc["tc"] for tc in body["tcs"]] == ["blitz"]
        blitz = body["tcs"][0]
        assert blitz["analyzed_n"] == 3
        assert blitz["below_gate"] is True  # 3 < gate, bullets are still emitted (D-03)
        assert len(blitz["bullets"]) == 38
        for bullet in blitz["bullets"]:
            assert bullet["orientation"] in ("missed", "allowed")
            assert isinstance(bullet["family"], str)
            assert isinstance(bullet["low_sample"], bool)
            assert isinstance(bullet["has_zone"], bool)
    finally:
        await _delete_games(test_engine, game_ids)


@pytest.mark.asyncio
async def test_no_analyzed_games_returns_empty_tcs(test_engine) -> None:
    """A user without analyzed games gets tcs == [] (zero-analyzed TCs are omitted)."""
    email = f"tac-cmp-router-empty-{uuid.uuid4().hex[:8]}@example.com"
    _user_id, token = await _register_and_login(email)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["tcs"] == []


@pytest.mark.asyncio
async def test_401_unauthenticated() -> None:
    """Unauthenticated request returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(ENDPOINT)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_422_date_guard() -> None:
    """from_date > to_date returns 422."""
    email = f"tac-cmp-router-date-{uuid.uuid4().hex[:8]}@example.com"
    _user_id, token = await _register_and_login(email)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            ENDPOINT,
            params={"from_date": "2025-06-01", "to_date": "2025-01-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tactic_families_filter(test_engine) -> None:
    """tactic_families narrows the analyzed population to games with a matching tactic."""
    email = f"tac-cmp-router-fam-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)

    game_ids = await _seed_games(test_engine, user_id, count=3, analyzed=True)
    # One game carries an allowed fork (user plays white: ply 2 is a user move).
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            session.add(
                GameFlaw(
                    user_id=user_id,
                    game_id=game_ids[0],
                    ply=2,
                    severity=1,
                    phase=1,
                    is_miss=False,
                    is_lucky=False,
                    is_reversed=False,
                    is_squandered=False,
                    fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                    allowed_tactic_motif=1,
                    allowed_tactic_confidence=90,
                )
            )

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_filtered = await client.get(
                ENDPOINT,
                params={"tactic_families": ["fork", "mate"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp_unfiltered = await client.get(
                ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp_filtered.status_code == 200
        assert resp_unfiltered.status_code == 200
        filtered = resp_filtered.json()
        unfiltered = resp_unfiltered.json()
        assert set(filtered) == {"tcs", "analyzed_gate"}
        assert [tc["analyzed_n"] for tc in filtered["tcs"]] == [1]
        assert [tc["analyzed_n"] for tc in unfiltered["tcs"]] == [3]
    finally:
        await _delete_games(test_engine, game_ids)
