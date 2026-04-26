"""Phase 70 router contract tests for POST /api/insights/openings (D-13, D-14).

URL: POST /api/insights/openings
     (insights router prefix="/insights" + @router.post("/openings"), mounted under /api)
"""

from __future__ import annotations

import uuid

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.main import app

OPENINGS_ENDPOINT = "/api/insights/openings"


@pytest_asyncio.fixture
async def auth_headers(test_engine: AsyncEngine) -> dict[str, str]:
    """Register a fresh user and return auth headers for the test."""
    email = f"insights_openings_test_{uuid.uuid4().hex[:8]}@example.com"
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


@pytest.mark.asyncio
async def test_post_openings_endpoint_requires_auth_returns_401() -> None:
    """V4 / V2 ASVS: unauthenticated request to POST /api/insights/openings
    must return 401 Unauthorized."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(OPENINGS_ENDPOINT, json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_openings_endpoint_returns_four_section_response(
    auth_headers: dict[str, str],
) -> None:
    """D-01: authenticated request returns a response with all four sections
    (white_weaknesses, black_weaknesses, white_strengths, black_strengths)
    present, even when all lists are empty.

    A freshly registered user has no imported games, so all sections are empty.
    The endpoint must return 200 with all four keys regardless.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(OPENINGS_ENDPOINT, json={}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "white_weaknesses" in body
    assert "black_weaknesses" in body
    assert "white_strengths" in body
    assert "black_strengths" in body
    assert isinstance(body["white_weaknesses"], list)
    assert isinstance(body["black_weaknesses"], list)
    assert isinstance(body["white_strengths"], list)
    assert isinstance(body["black_strengths"], list)


@pytest.mark.asyncio
async def test_post_openings_endpoint_rejects_invalid_recency_value(
    auth_headers: dict[str, str],
) -> None:
    """Pydantic validation: request body with recency='all_time' (invalid per D-11,
    the accepted recency set uses 'all' not 'all_time') must return 422."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            OPENINGS_ENDPOINT,
            json={"recency": "all_time"},
            headers=auth_headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_openings_endpoint_rejects_user_id_in_request_body(
    auth_headers: dict[str, str],
) -> None:
    """V4 ASVS / T-70-05-02: endpoint must derive user_id from session only.
    OpeningInsightsRequest has extra='forbid', so sending user_id in the body
    returns 422 Unprocessable Entity."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            OPENINGS_ENDPOINT,
            json={"user_id": 999},
            headers=auth_headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_openings_endpoint_does_NOT_apply_full_history_gate(
    auth_headers: dict[str, str],
) -> None:
    """D-14: the endpoint must NOT inherit _validate_full_history_filters.
    A request with mixed filters that would return 400 on the endgame route
    must succeed here with 200.

    This test is a regression gate: if a future maintainer accidentally copies
    the endgame validation block, CI fails.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            OPENINGS_ENDPOINT,
            json={"recency": "month", "time_control": ["bullet"], "rated": True},
            headers=auth_headers,
        )
    # Must be 200, not 400
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_post_openings_endpoint_filter_equivalence(
    auth_headers: dict[str, str],
) -> None:
    """INSIGHT-CORE-01: two requests with identical filter bodies must return
    identical responses (filter determinism).

    A fresh user has no games, so both calls return empty sections — but
    this verifies the route is deterministic and the response shape is stable.
    """
    body = {"recency": "month", "color": "white", "opponent_type": "human"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp1 = await client.post(OPENINGS_ENDPOINT, json=body, headers=auth_headers)
        resp2 = await client.post(OPENINGS_ENDPOINT, json=body, headers=auth_headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
