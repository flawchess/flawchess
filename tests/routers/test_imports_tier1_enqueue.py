"""Integration tests for POST /api/imports/eval/tier1/{game_id}.

Covers:
- test_tier1_enqueue: authenticated non-guest user enqueues an owned game → 200,
  status "enqueued" (or "already_queued" on second call), eval_jobs row exists.
- test_tier1_idor: game owned by another user → 404, no row inserted (T-118-06).
- test_tier1_guest: guest enqueues their own game → 200 "enqueued"; guest on
  another user's game → 404 (T-ey1-01 IDOR guard preserved for guests).
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
from sqlalchemy import func, select, text
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


async def _create_guest(test_engine) -> tuple[int, str]:
    """Create a guest session via POST /api/auth/guest/create and return (user_id, token).

    The guest/create endpoint does not return user_id in the response. We look it
    up from the User table using the most-recently-created guest row to avoid a
    separate /me endpoint call that would require a different auth route.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/guest/create")
    assert resp.status_code == 201, f"guest/create failed: {resp.text}"
    token = str(resp.json()["access_token"])

    # Fetch the newly-created guest's id from the DB.
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        row = await session.execute(
            text("SELECT id FROM users WHERE is_guest = true ORDER BY created_at DESC LIMIT 1")
        )
        user_id = int(row.scalar_one())
    return user_id, token


@pytest_asyncio.fixture
async def guest_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Create a guest user and return (user_id, token). Cleanup on teardown."""
    user_id, token = await _create_guest(test_engine)
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


@pytest.mark.asyncio
async def test_tier1_guest(
    guest_client: tuple[int, str],
    user_client: tuple[int, str],
    test_engine,
) -> None:
    """T-ey1-01: guest enqueues their OWN game → 200 "enqueued", row exists.
    Guest accessing another user's game → 404, no row inserted (IDOR guard preserved).
    """
    guest_id, guest_token = guest_client
    owner_id, _owner_token = user_client
    guest_headers = {"Authorization": f"Bearer {guest_token}"}

    # Seed a game owned by the guest.
    guest_game = _make_game(guest_id)
    guest_game_id = await _seed_game(test_engine, guest_game)

    # Seed a game owned by a different (non-guest) user.
    other_game = _make_game(owner_id)
    other_game_id = await _seed_game(test_engine, other_game)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Guest enqueuing their own game must succeed.
        own_resp = await client.post(f"{TIER1_BASE}/{guest_game_id}", headers=guest_headers)
        # Guest accessing another user's game must 404 (IDOR guard).
        other_resp = await client.post(f"{TIER1_BASE}/{other_game_id}", headers=guest_headers)

    assert own_resp.status_code == 200
    own_body = own_resp.json()
    assert own_body["status"] == "enqueued", (
        f"Guest's own game must be enqueued; got status={own_body['status']!r}"
    )
    assert own_body["game_id"] == guest_game_id

    # Tier-1 eval_jobs row must exist for the guest game.
    job_count = await _count_eval_jobs_for_game(test_engine, guest_game_id)
    assert job_count >= 1, "A tier-1 eval_jobs row must exist after guest enqueue"

    # IDOR: guest must not be able to enqueue another user's game.
    assert other_resp.status_code == 404
    other_job_count = await _count_eval_jobs_for_game(test_engine, other_game_id)
    assert other_job_count == 0, (
        "No eval_jobs row must be inserted for the other user's game (IDOR guard)"
    )
