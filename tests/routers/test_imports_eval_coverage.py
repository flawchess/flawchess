"""Integration tests for GET /api/imports/eval-coverage.

Covers:
- T-91-14: Unauthenticated access returns 401
- T-91-15: Cross-user data scoping (User A's pending count not visible to User B)
- Response shape: pending_count, total_count, pct_complete
- Zero-games edge case: pct_complete=100 (no division-by-zero)
- All-complete case: pending_count=0, pct_complete=100
- Partial case: correct pending count and rounded pct

Uses httpx AsyncClient with ASGITransport. Game rows are seeded directly via
committed DB sessions (not the rollback-scoped db_session fixture) because HTTP
requests go through an independent session path.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game

EVAL_COVERAGE_ENDPOINT = "/api/imports/eval-coverage"

# Constants per CLAUDE.md no-magic-numbers rule
PARTIAL_PENDING_COUNT = 3
PARTIAL_TOTAL_COUNT = 10
PARTIAL_EXPECTED_PCT = 70  # round(100 * (10 - 3) / 10) = 70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(user_id: int, evals_completed_at: datetime.datetime | None = None) -> Game:
    """Build a minimal Game ORM object for seeding tests."""
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
        evals_completed_at=evals_completed_at,
    )


_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)


async def _register_and_login(email: str, password: str = "testpassword123") -> tuple[int, str]:
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


async def _seed_games_for_user(
    test_engine,
    user_id: int,
    games: list[Game],
) -> None:
    """Insert game rows for the given user via a committed session.

    Uses a dedicated session (not db_session) so the data is visible to HTTP
    requests through the app's own session path.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        for game in games:
            game.user_id = user_id
            session.add(game)
        await session.commit()


async def _delete_games_for_user(test_engine, user_id: int) -> None:
    """Delete all seeded games for cleanup after test."""
    from sqlalchemy import delete

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.user_id == user_id))
        await session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_a_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User A and return (user_id, token). Cleanup games on teardown."""
    email = f"eval_cov_a_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


@pytest_asyncio.fixture
async def user_b_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User B and return (user_id, token). Cleanup games on teardown."""
    email = f"eval_cov_b_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_coverage_requires_auth() -> None:
    """T-91-14: GET /api/imports/eval-coverage without token returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_eval_coverage_zero_games(user_a_client: tuple[int, str]) -> None:
    """Authenticated user with no games returns pct_complete=100 (no division-by-zero)."""
    _user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"pending_count": 0, "total_count": 0, "pct_complete": 100}


@pytest.mark.asyncio
async def test_eval_coverage_all_complete(user_a_client: tuple[int, str], test_engine) -> None:
    """User with 5 games all having evals_completed_at set returns pct_complete=100."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"pending_count": 0, "total_count": 5, "pct_complete": 100}


@pytest.mark.asyncio
async def test_eval_coverage_partial(user_a_client: tuple[int, str], test_engine) -> None:
    """User with 10 games where 3 are pending returns pending_count=3, pct_complete=70."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    complete_games = [
        _make_game(user_id, evals_completed_at=_NOW)
        for _ in range(PARTIAL_TOTAL_COUNT - PARTIAL_PENDING_COUNT)
    ]
    pending_games = [
        _make_game(user_id, evals_completed_at=None) for _ in range(PARTIAL_PENDING_COUNT)
    ]
    await _seed_games_for_user(test_engine, user_id, complete_games + pending_games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "pending_count": PARTIAL_PENDING_COUNT,
        "total_count": PARTIAL_TOTAL_COUNT,
        "pct_complete": PARTIAL_EXPECTED_PCT,
    }


@pytest.mark.asyncio
async def test_eval_coverage_scoped_to_user(
    user_a_client: tuple[int, str],
    user_b_client: tuple[int, str],
    test_engine,
) -> None:
    """T-91-15: User B sees their own data only — User A's pending count is not leaked."""
    user_a_id, _token_a = user_a_client
    _user_b_id, token_b = user_b_client
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Seed 5 pending games for User A
    user_a_games = [_make_game(user_a_id, evals_completed_at=None) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_a_id, user_a_games)

    # User B has no games — should NOT see User A's pending count
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers_b)

    assert response.status_code == 200
    assert response.json() == {"pending_count": 0, "total_count": 0, "pct_complete": 100}
