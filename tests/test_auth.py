"""Integration tests for FastAPI-Users authentication.

Tests cover: registration, login, JWT auth, 401 protection, and user isolation.
Uses httpx.AsyncClient with ASGITransport to test the FastAPI app directly.

NOTE: Auth tests register real users in PostgreSQL (no rollback fixture).
      Each test uses unique emails generated with uuid4 to avoid conflicts.
"""

import uuid

import httpx
import pytest

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "test") -> str:
    """Generate a unique email address for each test invocation."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def register_user(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    return resp


async def login_user(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    return resp


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_returns_201_with_user_object(self):
        """POST /auth/register should return 201 with id and email."""
        email = unique_email("alice")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await register_user(client, email, "password123")

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["email"] == email
        assert "is_active" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_400(self):
        """Registering the same email twice should return 400."""
        email = unique_email("bob")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await register_user(client, email, "password123")
            resp = await register_user(client, email, "password456")

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_returns_access_token(self):
        """POST /auth/jwt/login should return access_token and token_type bearer."""
        email = unique_email("carol")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await register_user(client, email, "password123")
            resp = await login_user(client, email, "password123")

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_400(self):
        """POST /auth/jwt/login with wrong password should return 400."""
        email = unique_email("dave")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await register_user(client, email, "password123")
            resp = await login_user(client, email, "wrongpassword")

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Auth protection
# ---------------------------------------------------------------------------


class TestAuthProtection:
    @pytest.mark.asyncio
    async def test_analysis_requires_auth(self):
        """POST /openings/positions without Authorization header should return 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                json={"target_hash": 0},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_import_requires_auth(self):
        """POST /imports without Authorization header should return 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/imports",
                json={"platform": "chess.com", "username": "testuser"},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_analysis_with_valid_token_does_not_return_401(self):
        """POST /openings/positions with valid Bearer token should not return 401."""
        email = unique_email("eve")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            await register_user(client, email, "password123")
            login_resp = await login_user(client, email, "password123")
            token = login_resp.json()["access_token"]

            resp = await client.post(
                "/api/openings/positions",
                json={"target_hash": 0},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Should not be 401 — may be 200 with empty results
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------


class TestUserIsolation:
    @pytest.mark.asyncio
    async def test_user_isolation_analysis(self, db_session):
        """User B cannot see User A's games in analysis results."""
        import datetime

        from app.models.game import Game
        from app.models.game_position import GamePosition
        from app.schemas.analysis import AnalysisRequest
        from app.services import analysis_service

        email_a = unique_email("userA")
        email_b = unique_email("userB")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Register user A
            resp_a = await register_user(client, email_a, "password123")
            user_a_id = resp_a.json()["id"]

            # Register user B
            resp_b = await register_user(client, email_b, "password123")
            user_b_id = resp_b.json()["id"]

        # Insert a game for user A with a known full_hash
        KNOWN_HASH = 999_999_888_777
        game = Game(
            user_id=user_a_id,
            platform="chess.com",
            platform_game_id=f"isolation-test-{uuid.uuid4().hex[:8]}",
            black_username="opponent",
            result="1-0",
            user_color="white",
            played_at=datetime.datetime.now(tz=datetime.timezone.utc),
            time_control_bucket="blitz",
            pgn="[Event ?]\n1. e4 *",
            variant="Standard",
            rated=True,
        )
        db_session.add(game)
        await db_session.flush()

        position = GamePosition(
            game_id=game.id,
            user_id=user_a_id,
            ply=1,
            white_hash=KNOWN_HASH,
            black_hash=0,
            full_hash=KNOWN_HASH,
        )
        db_session.add(position)
        await db_session.flush()

        # Query as user B — should see 0 games
        request = AnalysisRequest(target_hash=KNOWN_HASH)
        result = await analysis_service.analyze(db_session, user_b_id, request)

        assert result.stats.total == 0
        assert result.stats.wins == 0
        assert result.games == []

        # Query as user A — should see 1 game
        result_a = await analysis_service.analyze(db_session, user_a_id, request)
        assert result_a.stats.total == 1
