"""Integration tests for the import API router.

Tests the HTTP layer only. Import service orchestration logic is mocked — see
test_import_service.py for those tests.

Uses httpx AsyncClient with ASGITransport to test the FastAPI app directly
without spinning up a real server.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

import app.services.import_service as import_service
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear job registry before each test to prevent cross-test pollution."""
    import_service._jobs.clear()
    yield
    import_service._jobs.clear()


@pytest.fixture
def no_op_run_import():
    """Patch run_import to be a no-op coroutine so background tasks don't run."""

    async def _noop(job_id: str) -> None:
        pass

    with patch("app.services.import_service.run_import", side_effect=_noop):
        yield


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers for POST /imports."""
    email = f"importer_{uuid.uuid4().hex[:8]}@example.com"
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
# POST /imports
# ---------------------------------------------------------------------------


class TestPostImports:
    @pytest.mark.asyncio
    async def test_post_imports_returns_201_with_job_id(self, no_op_run_import, auth_headers):
        """POST /imports should return 201 with job_id and status pending."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": "testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert len(data["job_id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_post_imports_lichess_returns_201(self, no_op_run_import, auth_headers):
        """POST /imports should work for lichess platform too."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/imports",
                json={"platform": "lichess", "username": "bobfischer"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_duplicate_import_returns_existing_job_with_200(
        self, no_op_run_import, auth_headers
    ):
        """Second POST for same platform should return existing job with 200."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First import
            resp1 = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": "testuser"},
                headers=auth_headers,
            )
            assert resp1.status_code == 201
            job_id_1 = resp1.json()["job_id"]

            # Second import (duplicate)
            resp2 = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": "testuser"},
                headers=auth_headers,
            )

        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["job_id"] == job_id_1

    @pytest.mark.asyncio
    async def test_post_imports_is_immediate_non_blocking(self, no_op_run_import, auth_headers):
        """POST /imports response must come back within 1 second (import is background)."""
        start = time.monotonic()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": "testuser"},
                headers=auth_headers,
            )

        elapsed = time.monotonic() - start
        assert resp.status_code == 201
        assert elapsed < 1.0, f"Response took too long: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_post_imports_invalid_platform_returns_422(self, auth_headers):
        """POST /imports with invalid platform should return 422."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/imports",
                json={"platform": "invalid_platform", "username": "testuser"},
                headers=auth_headers,
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_post_imports_empty_username_returns_422(self, auth_headers):
        """POST /imports with empty username should return 422."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": ""},
                headers=auth_headers,
            )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /imports/{job_id}
# ---------------------------------------------------------------------------


class TestGetImportStatus:
    @pytest.mark.asyncio
    async def test_get_returns_job_progress(self, no_op_run_import, auth_headers):
        """GET /imports/{job_id} should return current progress data."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create a job first
            create_resp = await client.post(
                "/imports",
                json={"platform": "chess.com", "username": "alice"},
                headers=auth_headers,
            )
            job_id = create_resp.json()["job_id"]

            # Poll it
            status_resp = await client.get(f"/imports/{job_id}")

        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["job_id"] == job_id
        assert data["platform"] == "chess.com"
        assert data["username"] == "alice"
        assert data["status"] == "pending"
        assert "games_fetched" in data
        assert "games_imported" in data

    @pytest.mark.asyncio
    async def test_get_unknown_job_id_returns_404(self):
        """GET /imports/{unknown_id} should return 404."""
        # Also mock the DB fallback so we don't need a real DB
        with patch(
            "app.routers.imports.import_job_repository.get_import_job",
            new=AsyncMock(return_value=None),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/imports/00000000-0000-0000-0000-000000000000")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_reflects_updated_progress(self, no_op_run_import, auth_headers):
        """GET should reflect updated games_fetched count."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create a job
            create_resp = await client.post(
                "/imports",
                json={"platform": "lichess", "username": "bob"},
                headers=auth_headers,
            )
            job_id = create_resp.json()["job_id"]

            # Simulate some progress by mutating in-memory state
            job = import_service.get_job(job_id)
            job.games_fetched = 42
            job.games_imported = 40

            # Poll it
            status_resp = await client.get(f"/imports/{job_id}")

        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["games_fetched"] == 42
        assert data["games_imported"] == 40

    @pytest.mark.asyncio
    async def test_get_falls_back_to_db_when_not_in_memory(self):
        """GET should query DB when job not found in in-memory registry."""
        db_job = MagicMock()
        db_job.id = "some-db-job-id"
        db_job.platform = "chess.com"
        db_job.username = "alice"
        db_job.status = "completed"
        db_job.games_fetched = 100
        db_job.games_imported = 98
        db_job.error_message = None

        with patch(
            "app.routers.imports.import_job_repository.get_import_job",
            new=AsyncMock(return_value=db_job),
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/imports/some-db-job-id")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["games_fetched"] == 100
