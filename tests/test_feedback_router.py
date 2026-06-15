"""Integration tests for the POST /api/feedback endpoint.

Coverage:
- TestFeedbackPersist: 201 response + row written (D-04)
- TestFeedbackValidation: empty text → 422; over-max text → 422 (D-03/D-07)
- TestFeedbackRateLimit: 6th submission within window → 429 (D-07)
- TestFeedbackGuest: guest user can submit feedback → 201 (D-08)
- TestFeedbackAuth: unauthenticated request → 401
- TestEloBucket: elo_bucket boundary values (D-05)
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app
from app.schemas.feedback import _MAX_FEEDBACK_LEN


# ---------------------------------------------------------------------------
# Auth fixture (module-scoped: register + login once per module)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = f"feedback_test_{uuid.uuid4().hex[:8]}@example.com"
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
# Standard feedback body
# ---------------------------------------------------------------------------

_STANDARD_FEEDBACK_BODY = {
    "text": "This is a great analysis feature!",
    "rating": 5,
    "page_url": "/openings",
}


# ---------------------------------------------------------------------------
# TestFeedbackPersist — D-04/D-05
# ---------------------------------------------------------------------------


class TestFeedbackPersist:
    """Verify POST /api/feedback persists a row and returns 201 (D-04)."""

    @pytest.mark.asyncio
    async def test_create_returns_201_with_response(self, auth_headers: dict[str, str]) -> None:
        """POST /api/feedback returns 201 with id and created_at fields."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/feedback",
                json=_STANDARD_FEEDBACK_BODY,
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "created_at" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_create_without_rating_returns_201(self, auth_headers: dict[str, str]) -> None:
        """POST /api/feedback with no rating returns 201 (rating is optional)."""
        body = {"text": "Feedback without rating", "page_url": "/endgames"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/feedback", json=body, headers=auth_headers)

        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# TestFeedbackValidation — D-03/D-07
# ---------------------------------------------------------------------------


class TestFeedbackValidation:
    """Verify validation: empty text → 422; over-max text → 422 (D-03/D-07)."""

    @pytest.mark.asyncio
    async def test_empty_text_returns_422(self, auth_headers: dict[str, str]) -> None:
        """POST /api/feedback with empty text returns 422."""
        body = {"text": "", "page_url": "/openings"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/feedback", json=body, headers=auth_headers)

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_over_max_text_returns_422(self, auth_headers: dict[str, str]) -> None:
        """POST /api/feedback with text exceeding max length returns 422."""
        too_long_text = "x" * (_MAX_FEEDBACK_LEN + 1)
        body = {"text": too_long_text, "page_url": "/openings"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/feedback", json=body, headers=auth_headers)

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_rating_returns_422(self, auth_headers: dict[str, str]) -> None:
        """POST /api/feedback with an out-of-range rating (> 5) returns 422."""
        body = {"text": "Some feedback", "rating": 6, "page_url": "/openings"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/feedback", json=body, headers=auth_headers)

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TestFeedbackRateLimit — D-07
# ---------------------------------------------------------------------------


class TestFeedbackRateLimit:
    """Verify per-user rate limit: 6th submission in window → 429 (D-07)."""

    @pytest.mark.asyncio
    async def test_sixth_submission_returns_429(self) -> None:
        """6th POST /api/feedback within the window returns 429 for the same user."""

        # Use a dedicated rate-limit test user to avoid polluting other tests
        email = f"rate_limit_test_{uuid.uuid4().hex[:8]}@example.com"
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
            headers = {"Authorization": f"Bearer {token}"}

            # Submit 5 times (all should succeed)
            for i in range(5):
                resp = await client.post(
                    "/api/feedback",
                    json={"text": f"Feedback #{i + 1}", "page_url": "/openings"},
                    headers=headers,
                )
                assert resp.status_code == 201, f"Expected 201 on submission #{i + 1}"

            # 6th submission should be rate-limited
            resp = await client.post(
                "/api/feedback",
                json={"text": "Sixth feedback", "page_url": "/openings"},
                headers=headers,
            )

        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# TestFeedbackGuest — D-08
# ---------------------------------------------------------------------------


class TestFeedbackGuest:
    """Verify guest users can submit feedback (D-08)."""

    @pytest.mark.asyncio
    async def test_guest_can_submit_feedback(self) -> None:
        """Guest session created via POST /auth/guest/create can submit feedback."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create a guest session
            guest_resp = await client.post("/api/auth/guest/create")
            assert guest_resp.status_code == 201
            guest_token = guest_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {guest_token}"}

            # Submit feedback as guest
            resp = await client.post(
                "/api/feedback",
                json={"text": "Feedback from a guest user", "page_url": "/"},
                headers=headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data


# ---------------------------------------------------------------------------
# TestFeedbackAuth
# ---------------------------------------------------------------------------


class TestFeedbackAuth:
    """Verify unauthenticated requests return 401."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self) -> None:
        """POST /api/feedback without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/feedback", json=_STANDARD_FEEDBACK_BODY)

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestEloBucket — D-05 (boundary values)
# ---------------------------------------------------------------------------


class TestEloBucket:
    """Verify elo_bucket(rating) boundary values (D-05)."""

    def test_elo_bucket_below_800_returns_none(self) -> None:
        """Ratings below 800 return None (sub-800 floor)."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(0) is None
        assert elo_bucket(799) is None

    def test_elo_bucket_800_boundary(self) -> None:
        """Rating 800 maps to bucket 800."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(800) == 800
        assert elo_bucket(1199) == 800

    def test_elo_bucket_1200_boundary(self) -> None:
        """Rating 1200 maps to bucket 1200."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(1200) == 1200
        assert elo_bucket(1599) == 1200

    def test_elo_bucket_1600_boundary(self) -> None:
        """Rating 1600 maps to bucket 1600."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(1600) == 1600
        assert elo_bucket(1999) == 1600

    def test_elo_bucket_2000_boundary(self) -> None:
        """Rating 2000 maps to bucket 2000."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(2000) == 2000
        assert elo_bucket(2399) == 2000

    def test_elo_bucket_2400_and_above(self) -> None:
        """Rating 2400+ maps to bucket 2400."""
        from app.services.feedback_service import elo_bucket

        assert elo_bucket(2400) == 2400
        assert elo_bucket(3000) == 2400
