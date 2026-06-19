"""Integration tests for GET /api/library/tactic-comparison (Phase 126).

Coverage:
- test_200_shape              : authenticated request returns 200 with bullets/analyzed_n/analyzed_gate/below_gate
- test_401_unauthenticated    : no-auth returns 401
- test_422_date_guard         : from_date > to_date returns 422
- test_tactic_families_filter : tactic_families param accepted, response is valid
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game

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


async def _seed_games(test_engine, user_id: int, count: int = 1) -> None:
    """Insert game rows for the given user via a committed session."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            for _ in range(count):
                session.add(
                    Game(
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
                    )
                )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_200_shape(test_engine) -> None:
    """Authenticated request returns 200 with correct response keys."""
    email = f"tac-cmp-router-shape-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            ENDPOINT,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "bullets" in body
    assert "analyzed_n" in body
    assert "analyzed_gate" in body
    assert "below_gate" in body
    assert isinstance(body["bullets"], list)
    assert isinstance(body["analyzed_n"], int)
    assert isinstance(body["analyzed_gate"], int)
    assert isinstance(body["below_gate"], bool)


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
    """tactic_families param is accepted and response is valid TacticComparisonResponse."""
    email = f"tac-cmp-router-fam-{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)

    # Seed a few games so we get a real (below-gate but valid) response
    await _seed_games(test_engine, user_id, count=3)

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
    # Both responses must have the required keys
    for body in [resp_filtered.json(), resp_unfiltered.json()]:
        assert "bullets" in body
        assert "analyzed_n" in body
        assert "below_gate" in body
