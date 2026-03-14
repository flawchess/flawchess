"""Integration tests for the stats API router.

Tests the HTTP layer. Uses httpx AsyncClient with ASGITransport to test the
FastAPI app directly without spinning up a real server.

Coverage:
- GET /stats/rating-history: returns 401 without auth
- GET /stats/rating-history: returns structured per-platform data
- GET /stats/rating-history?recency=month: filters by recency
- GET /stats/global: returns 401 without auth
- GET /stats/global: returns WDL by time control and color
- GET /stats/global?recency=year: filters by recency
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
    email = f"stats_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /stats/rating-history
# ---------------------------------------------------------------------------


class TestGetRatingHistory:
    """Tests for GET /stats/rating-history."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/rating-history")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/rating-history", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response contains chess_com and lichess keys with list values."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/rating-history", headers=auth_headers)

        data = resp.json()
        assert "chess_com" in data
        assert "lichess" in data
        assert isinstance(data["chess_com"], list)
        assert isinstance(data["lichess"], list)

    @pytest.mark.asyncio
    async def test_recency_param_accepted(self, auth_headers: dict[str, str]) -> None:
        """recency query param is accepted without error."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/stats/rating-history?recency=month", headers=auth_headers
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_data_point_structure_when_present(
        self, auth_headers: dict[str, str]
    ) -> None:
        """If data points exist, each has date, rating, time_control_bucket fields."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/rating-history", headers=auth_headers)

        data = resp.json()
        # Check structure of any returned data points
        for points in [data["chess_com"], data["lichess"]]:
            for pt in points:
                assert "date" in pt
                assert "rating" in pt
                assert "time_control_bucket" in pt
                assert isinstance(pt["rating"], int)
                assert isinstance(pt["date"], str)


# ---------------------------------------------------------------------------
# GET /stats/global
# ---------------------------------------------------------------------------


class TestGetGlobalStats:
    """Tests for GET /stats/global."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/global")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/global", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response contains by_time_control and by_color keys with list values."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/global", headers=auth_headers)

        data = resp.json()
        assert "by_time_control" in data
        assert "by_color" in data
        assert isinstance(data["by_time_control"], list)
        assert isinstance(data["by_color"], list)

    @pytest.mark.asyncio
    async def test_recency_param_accepted(self, auth_headers: dict[str, str]) -> None:
        """recency query param is accepted without error."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/global?recency=year", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_wdl_category_structure_when_present(
        self, auth_headers: dict[str, str]
    ) -> None:
        """Each WDL category entry has the required fields."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/stats/global", headers=auth_headers)

        data = resp.json()
        required_fields = {"label", "wins", "draws", "losses", "total", "win_pct", "draw_pct", "loss_pct"}
        for categories in [data["by_time_control"], data["by_color"]]:
            for cat in categories:
                for field in required_fields:
                    assert field in cat, f"Missing field: {field}"
                assert isinstance(cat["wins"], int)
                assert isinstance(cat["draws"], int)
                assert isinstance(cat["losses"], int)
                assert isinstance(cat["total"], int)
