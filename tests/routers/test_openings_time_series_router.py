"""Router contract tests for POST /api/openings/time-series.

URL: POST /api/openings/time-series
     (openings router prefix="/openings" + @router.post("/time-series"), mounted under /api)

Covers the dev-clock plumbing (D-03): the router hands the dev_now_utc instant to the
service, which anchors the per-colour current-repertoire cutoff behind is_current.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.dev_clock import dev_now_utc
from app.main import app
from app.schemas.openings import TimeSeriesResponse

TIME_SERIES_ENDPOINT = "/api/openings/time-series"


@pytest_asyncio.fixture
async def auth_headers(test_engine: AsyncEngine) -> dict[str, str]:
    """Register a fresh user and return auth headers for the test."""
    email = f"openings_time_series_test_{uuid.uuid4().hex[:8]}@example.com"
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


@pytest.fixture
def pinned_now() -> Iterator[datetime.datetime]:
    """Pin dev_now_utc through dependency_overrides; removed on teardown."""
    pinned = datetime.datetime(2026, 3, 10, 12, 0, tzinfo=datetime.UTC)
    app.dependency_overrides[dev_now_utc] = lambda: pinned
    yield pinned
    app.dependency_overrides.pop(dev_now_utc, None)


@pytest.mark.asyncio
async def test_time_series_requires_auth_returns_401() -> None:
    """Unauthenticated request to POST /api/openings/time-series returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(TIME_SERIES_ENDPOINT, json={"bookmarks": []})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_time_series_passes_dev_clock_now_utc(
    auth_headers: dict[str, str], pinned_now: datetime.datetime
) -> None:
    """The router hands the dev_now_utc instant to the service (D-03)."""
    with patch(
        "app.services.openings_service.get_time_series",
        new=AsyncMock(return_value=TimeSeriesResponse(series=[])),
    ) as mock_service:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                TIME_SERIES_ENDPOINT, json={"bookmarks": []}, headers=auth_headers
            )

    assert response.status_code == 200
    mock_service.assert_awaited_once()
    assert mock_service.await_args is not None
    assert mock_service.await_args.kwargs["now_utc"] == pinned_now
