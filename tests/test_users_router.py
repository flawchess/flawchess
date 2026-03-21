"""Integration tests for GET/PUT /users/me/profile endpoints.

Uses httpx.AsyncClient with ASGITransport to test the FastAPI app directly.
Each test class uses a module-scoped user so registration only happens once per module.
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "user") -> str:
    """Generate a unique email address for each test run."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Register a user and return their JWT access token."""
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login_resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    return login_resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = unique_email("profile")
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await _register_and_login(client, email, password)

    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /users/me/profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_get_profile_returns_null_usernames(self, auth_headers):
        """GET /users/me/profile returns 200 with null usernames for a new user."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/users/me/profile", headers=auth_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert "chess_com_username" in body
        assert "lichess_username" in body
        assert body["chess_com_username"] is None
        assert body["lichess_username"] is None

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self):
        """GET /users/me/profile without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/users/me/profile")

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/me/profile
# ---------------------------------------------------------------------------


class TestPutProfile:
    @pytest.mark.asyncio
    async def test_put_profile_updates_usernames(self):
        """PUT /users/me/profile updates both usernames and GET confirms the values."""
        email = unique_email("profile_update")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token = await _register_and_login(client, email, password)
            headers = {"Authorization": f"Bearer {token}"}

            # Update both usernames
            put_resp = await client.put(
                "/api/users/me/profile",
                json={
                    "chess_com_username": "magnus2024",
                    "lichess_username": "magnus_lichess",
                },
                headers=headers,
            )
            assert put_resp.status_code == 200
            put_body = put_resp.json()
            assert put_body["chess_com_username"] == "magnus2024"
            assert put_body["lichess_username"] == "magnus_lichess"

            # GET confirms updates persisted
            get_resp = await client.get("/api/users/me/profile", headers=headers)
            assert get_resp.status_code == 200
            get_body = get_resp.json()
            assert get_body["chess_com_username"] == "magnus2024"
            assert get_body["lichess_username"] == "magnus_lichess"

    @pytest.mark.asyncio
    async def test_put_profile_unauthenticated(self):
        """PUT /users/me/profile without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/users/me/profile",
                json={"chess_com_username": "testuser"},
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# User isolation — profile returns the authenticated user's own data
# ---------------------------------------------------------------------------


class TestProfileUserIsolation:
    @pytest.mark.asyncio
    async def test_profile_returns_own_email(self):
        """Each user's GET /users/me/profile must return their own email, not another user's."""
        email_a = unique_email("iso_a")
        email_b = unique_email("iso_b")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token_a = await _register_and_login(client, email_a, password)
            token_b = await _register_and_login(client, email_b, password)

            profile_a = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            profile_b = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token_b}"},
            )

        assert profile_a.status_code == 200
        assert profile_b.status_code == 200
        assert profile_a.json()["email"] == email_a
        assert profile_b.json()["email"] == email_b
