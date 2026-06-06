"""Integration tests for the library API router.

Tests the HTTP layer for GET /api/library/games and GET /api/library/flaw-stats.
Uses httpx AsyncClient with ASGITransport to test the FastAPI app directly.

Coverage:
- GET /library/games: requires auth
- GET /library/games?color=white: accepted, returns only white games
- GET /library/games?color=black: accepted, returns only black games
- GET /library/flaw-stats: requires auth
- GET /library/flaw-stats?color=white: accepted, returns 200
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = f"library_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /library/games
# ---------------------------------------------------------------------------


class TestGetLibraryGames:
    """Tests for GET /library/games."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200 for a new user with no games."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response contains games, matched_count, offset, limit keys."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games", headers=auth_headers)

        body = resp.json()
        assert "games" in body
        assert "matched_count" in body
        assert "offset" in body
        assert "limit" in body
        assert isinstance(body["games"], list)
        assert isinstance(body["matched_count"], int)

    @pytest.mark.asyncio
    async def test_color_white_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=white is accepted and returns the standard games structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"color": "white"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "games" in body
        assert "matched_count" in body
        # For a new user without games, matched_count must be 0 under white filter.
        assert body["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_color_black_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=black is accepted and returns the standard games structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"color": "black"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "games" in body
        assert body["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_color_white_and_black_counts_match_total(
        self, auth_headers: dict[str, str]
    ) -> None:
        """matched_count(white) + matched_count(black) <= matched_count(unfiltered).

        For a fresh test user with no games all three are 0. The assertion is
        direction-invariant so it stays valid when games are seeded in future.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_all = await client.get("/api/library/games", headers=auth_headers)
            resp_white = await client.get(
                "/api/library/games", params={"color": "white"}, headers=auth_headers
            )
            resp_black = await client.get(
                "/api/library/games", params={"color": "black"}, headers=auth_headers
            )

        total = resp_all.json()["matched_count"]
        white_n = resp_white.json()["matched_count"]
        black_n = resp_black.json()["matched_count"]

        assert white_n + black_n <= total


# ---------------------------------------------------------------------------
# GET /library/flaw-stats
# ---------------------------------------------------------------------------


class TestGetFlawStats:
    """Tests for GET /library/flaw-stats."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response has the flaw-stats structure keys."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats", headers=auth_headers)

        body = resp.json()
        required = {
            "per_severity_counts",
            "rates",
            "tag_distribution",
            "trend",
            "analyzed_pct",
            "analyzed_n",
            "total_n",
        }
        for field in required:
            assert field in body, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_color_white_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=white is accepted and returns 200 with the standard flaw-stats structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaw-stats",
                params={"color": "white"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "total_n" in body
        # For a new user without games, total_n must be 0 under white filter.
        assert body["total_n"] == 0

    @pytest.mark.asyncio
    async def test_color_black_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=black is accepted and returns 200 with the standard flaw-stats structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaw-stats",
                params={"color": "black"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_n"] == 0

    @pytest.mark.asyncio
    async def test_color_white_and_black_total_n_sum_matches_unfiltered(
        self, auth_headers: dict[str, str]
    ) -> None:
        """total_n(white) + total_n(black) <= total_n(unfiltered).

        The inequality holds because unfiltered includes any games with NULL
        user_color (rare but possible). For a new user all three are 0.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_all = await client.get("/api/library/flaw-stats", headers=auth_headers)
            resp_white = await client.get(
                "/api/library/flaw-stats", params={"color": "white"}, headers=auth_headers
            )
            resp_black = await client.get(
                "/api/library/flaw-stats", params={"color": "black"}, headers=auth_headers
            )

        total = resp_all.json()["total_n"]
        white_n = resp_white.json()["total_n"]
        black_n = resp_black.json()["total_n"]

        assert white_n + black_n <= total
