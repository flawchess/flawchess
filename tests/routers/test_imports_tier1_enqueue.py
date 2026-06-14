"""Integration tests for POST /api/imports/eval/tier1/{game_id}.

Covers:
- test_tier1_enqueue: authenticated non-guest user enqueues an owned game → 200,
  status "enqueued" (or "already_queued" on second call), eval_jobs row exists.
- test_tier1_idor: game owned by another user → 404, no row inserted (T-118-06).
- test_tier1_guest: guest user returns status "skipped_guest", 200.
- test_tier1_second_call: calling twice on the same game returns "already_queued".
- test_tier1_noninteger_game_id: non-integer path param → FastAPI 422 (T-118-10).
- test_tier1_requires_auth: no token → 401.

Uses httpx AsyncClient with ASGITransport. Game rows seeded via committed sessions
(not rollback-scoped) so HTTP requests see them through the app's own session path.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.eval_jobs import EvalJob
from app.models.game import Game

TIER1_BASE = "/api/imports/eval/tier1"

# Constants (no magic numbers)
_VALID_PASSWORD = "testpassword123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(email: str, password: str = _VALID_PASSWORD) -> tuple[int, str]:
    """Register a user via HTTP and return (user_id, auth_token)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg_resp = await client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code in (200, 201), f"register failed: {reg_resp.text}"
        user_id = int(reg_resp.json()["id"])

        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200, f"login failed: {login_resp.text}"
        token = str(login_resp.json()["access_token"])

    return user_id, token


def _make_game(user_id: int) -> Game:
    """Build a minimal Game ORM object (no eval data — pending state)."""
    return Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://chess.com/game/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        is_computer_game=False,
        evals_completed_at=None,
        full_evals_completed_at=None,
    )


async def _seed_game(test_engine, game: Game) -> int:
    """Insert a game via committed session and return the assigned id."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        session.add(game)
        await session.commit()
        return int(game.id)  # type: ignore[arg-type]


async def _count_eval_jobs_for_game(test_engine, game_id: int) -> int:
    """Return the number of eval_jobs rows for a game (any status)."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(
            select(func.count()).select_from(EvalJob).where(EvalJob.game_id == game_id)
        )
        return result.scalar_one()


async def _delete_games_and_jobs(test_engine, user_id: int) -> None:
    """Delete all seeded games (cascade-deletes eval_jobs via FK) for cleanup."""
    from sqlalchemy import delete

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.user_id == user_id))
        await session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register a non-guest user and return (user_id, token). Cleanup on teardown."""
    email = f"tier1_owner_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_and_jobs(test_engine, user_id)


@pytest_asyncio.fixture
async def other_user_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register a second non-guest user for IDOR tests."""
    email = f"tier1_other_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_and_jobs(test_engine, user_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier1_requires_auth() -> None:
    """No token → 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"{TIER1_BASE}/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tier1_noninteger_game_id(user_client: tuple[int, str]) -> None:
    """Non-integer game_id → FastAPI 422 (T-118-10)."""
    _user_id, token = user_client
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"{TIER1_BASE}/not-an-int", headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tier1_enqueue(user_client: tuple[int, str], test_engine) -> None:
    """Authenticated non-guest user enqueues an owned game → 200, status enqueued,
    and a tier-1 eval_jobs row exists for the game.
    """
    user_id, token = user_client
    headers = {"Authorization": f"Bearer {token}"}

    game = _make_game(user_id)
    game_id = await _seed_game(test_engine, game)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"{TIER1_BASE}/{game_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    # Freshly-seeded game with no competing enqueue source (Phase 118 removed the
    # tier-2 auto-enqueue), so the explicit tier-1 request always wins the slot.
    assert body["status"] == "enqueued"
    assert body["game_id"] == game_id

    # Verify the tier-1 row exists.
    job_count = await _count_eval_jobs_for_game(test_engine, game_id)
    assert job_count >= 1


@pytest.mark.asyncio
async def test_tier1_second_call_returns_already_queued(
    user_client: tuple[int, str], test_engine
) -> None:
    """Second enqueue on the same game returns already_queued, still one row."""
    user_id, token = user_client
    headers = {"Authorization": f"Bearer {token}"}

    game = _make_game(user_id)
    game_id = await _seed_game(test_engine, game)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp1 = await client.post(f"{TIER1_BASE}/{game_id}", headers=headers)
        resp2 = await client.post(f"{TIER1_BASE}/{game_id}", headers=headers)

    assert resp1.status_code == 200
    assert resp1.json()["status"] == "enqueued"
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_queued"

    # Still exactly one eval_jobs row (idempotent)
    job_count = await _count_eval_jobs_for_game(test_engine, game_id)
    assert job_count == 1


@pytest.mark.asyncio
async def test_tier1_idor(
    user_client: tuple[int, str],
    other_user_client: tuple[int, str],
    test_engine,
) -> None:
    """T-118-06 IDOR guard: game owned by another user → 404, no row inserted."""
    owner_id, _owner_token = user_client
    _attacker_id, attacker_token = other_user_client
    headers = {"Authorization": f"Bearer {attacker_token}"}

    # Seed a game owned by owner (not attacker)
    game = _make_game(owner_id)
    game_id = await _seed_game(test_engine, game)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"{TIER1_BASE}/{game_id}", headers=headers)

    assert response.status_code == 404
    # Verify no eval_jobs row was inserted
    job_count = await _count_eval_jobs_for_game(test_engine, game_id)
    assert job_count == 0


@pytest.mark.asyncio
async def test_tier1_missing_game(user_client: tuple[int, str]) -> None:
    """Game id that doesn't exist → 404."""
    _user_id, token = user_client
    headers = {"Authorization": f"Bearer {token}"}

    nonexistent_game_id = 999_999_999

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(f"{TIER1_BASE}/{nonexistent_game_id}", headers=headers)

    assert response.status_code == 404
