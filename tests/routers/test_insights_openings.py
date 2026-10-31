"""Router contract tests for POST /api/insights/openings.

URL: POST /api/insights/openings
     (insights router prefix="/insights" + @router.post("/openings"), mounted under /api)
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
from app.schemas.opening_insights import OpeningInsightsResponse

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
    """Unauthenticated request to POST /api/insights/openings
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
    """Authenticated request returns a response with all four sections
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
async def test_post_openings_endpoint_rejects_unknown_field(
    auth_headers: dict[str, str],
) -> None:
    """Pydantic extra='forbid' rejects unknown fields with 422."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            OPENINGS_ENDPOINT,
            json={"unknown_field": "some_value"},
            headers=auth_headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_openings_endpoint_rejects_user_id_in_request_body(
    auth_headers: dict[str, str],
) -> None:
    """Endpoint must derive user_id from session only.
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
    """The endpoint must NOT copy the (since removed) endgame full-history gate.
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
            json={"from_date": "2026-01-01", "time_control": ["bullet"], "rated": True},
            headers=auth_headers,
        )
    # Must be 200, not 400
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_post_openings_endpoint_filter_equivalence(
    auth_headers: dict[str, str],
) -> None:
    """Two requests with identical filter bodies must return
    identical responses (filter determinism).

    A fresh user has no games, so both calls return empty sections — but
    this verifies the route is deterministic and the response shape is stable.
    """
    body = {"from_date": "2026-01-01", "color": "white", "opponent_type": "human"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp1 = await client.post(OPENINGS_ENDPOINT, json=body, headers=auth_headers)
        resp2 = await client.post(OPENINGS_ENDPOINT, json=body, headers=auth_headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


@pytest.fixture
def pinned_now() -> Iterator[datetime.datetime]:
    """Pin dev_now_utc through dependency_overrides; removed on teardown."""
    pinned = datetime.datetime(2026, 3, 10, 12, 0, tzinfo=datetime.UTC)
    app.dependency_overrides[dev_now_utc] = lambda: pinned
    yield pinned
    app.dependency_overrides.pop(dev_now_utc, None)


@pytest.mark.asyncio
async def test_post_openings_endpoint_passes_dev_clock_now_utc(
    auth_headers: dict[str, str], pinned_now: datetime.datetime
) -> None:
    """The router hands the dev_now_utc instant to compute_insights (D-03)."""
    with patch(
        "app.routers.insights.compute_insights",
        new=AsyncMock(return_value=OpeningInsightsResponse()),
    ) as mock_compute:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(OPENINGS_ENDPOINT, json={}, headers=auth_headers)

    assert response.status_code == 200
    mock_compute.assert_awaited_once()
    assert mock_compute.await_args is not None
    assert mock_compute.await_args.kwargs["now_utc"] == pinned_now


@pytest.mark.asyncio
async def test_post_openings_endpoint_response_carries_new_fields(
    auth_headers: dict[str, str],
) -> None:
    """The response exposes the four card lists and both cutoffs, and no longer carries
    the "not clear yet" lists or their counts (D-34)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(OPENINGS_ENDPOINT, json={}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    for key in ("white_weaknesses", "black_weaknesses", "white_strengths", "black_strengths"):
        assert body[key] == []
        assert f"{key}_not_clear" not in body
        assert f"{key}_not_clear_count" not in body
    assert not any("not_clear" in key for key in body)
    # Neither the cutoff nor the eval baseline is echoed: the client never reads them.
    assert not any(key.startswith(("current_cutoff", "eval_baseline")) for key in body)


ENDGAME_INSIGHTS_ENDPOINT = "/api/insights/endgame"


@pytest.mark.asyncio
async def test_endgame_insights_no_longer_gated_by_from_date(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """insights/endgame takes no filters, so from_date no longer 400s.

    This was a silent-regression gate for the v8
    full-history filter gate. The gate is intentionally gone: the report narrates
    the ranked sample, whatever the page filters are, and an undeclared ``from_date``
    query parameter is ignored (the frontend may still send it).
    generate_insights is stubbed so no LLM or findings pipeline runs.
    """
    from app.schemas.insights import (
        EndgameInsightsReport,
        EndgameInsightsResponse,
        SectionInsight,
    )

    calls: list[tuple[int, object]] = []

    async def _stub_generate_insights(user_id: int, session: object) -> EndgameInsightsResponse:
        calls.append((user_id, session))
        return EndgameInsightsResponse(
            report=EndgameInsightsReport(
                summary="Endgames lift your rating; rook endings need work.",
                player_profile="Player around 1500 blitz.",
                overview="Stub overview.",
                recommendations=["Drill rook endings.", "Review time trouble."],
                sections=[
                    SectionInsight(section_id="overall", headline="Stub", bullets=["Stub bullet"])
                ],
                model_used="test",
                prompt_version="endgame_v50",
            ),
            status="fresh",
        )

    monkeypatch.setattr("app.services.insights_llm.generate_insights", _stub_generate_insights)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            ENDGAME_INSIGHTS_ENDPOINT,
            params={"from_date": "2026-03-01"},
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "fresh"
    assert len(calls) == 1
