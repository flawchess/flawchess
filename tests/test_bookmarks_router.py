"""Integration tests for the position bookmarks API router.

Tests the HTTP contract via httpx AsyncClient with ASGITransport.
The repository layer is already tested in test_bookmark_repository.py —
these tests verify the HTTP layer: status codes, request/response shape,
auth enforcement, and the full CRUD lifecycle.

Coverage:
- TestBookmarkCRUD: create (201), list (200), update (200), delete (204), 404 cases
- TestBookmarkReorder: PUT /reorder assigns correct sort_order values
- TestBookmarkMatchSide: PATCH /{id}/match-side updates match_side and recomputes target_hash
- TestBookmarkAuth: unauthenticated requests return 401
- TestBookmarkSuggestions: GET /suggestions returns structured response for new user
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app

# ---------------------------------------------------------------------------
# Standard bookmark body for creation
# ---------------------------------------------------------------------------

_STANDARD_BOOKMARK_BODY = {
    "label": "Test",
    "target_hash": "1234567890",
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "moves": ["e4"],
    "color": "white",
    "match_side": "full",
}


# ---------------------------------------------------------------------------
# Auth fixture (module-scoped: register + login once per module)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = f"bookmarks_test_{uuid.uuid4().hex[:8]}@example.com"
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
# Helper to create a bookmark via HTTP and return the parsed response body
# ---------------------------------------------------------------------------


async def _create_bookmark(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    label: str = "Test Bookmark",
) -> dict:
    """POST /api/position-bookmarks and return JSON body. Asserts 201."""
    body = dict(_STANDARD_BOOKMARK_BODY)
    body["label"] = label
    resp = await client.post("/api/position-bookmarks", json=body, headers=auth_headers)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# TestBookmarkCRUD — Full lifecycle through HTTP
# ---------------------------------------------------------------------------


class TestBookmarkCRUD:
    """Verify CRUD operations through the HTTP layer."""

    @pytest.mark.asyncio
    async def test_create_returns_201_with_bookmark(
        self, auth_headers: dict[str, str]
    ) -> None:
        """POST /position-bookmarks returns 201 with correct response shape."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/position-bookmarks",
                json=_STANDARD_BOOKMARK_BODY,
                headers=auth_headers,
            )

        assert resp.status_code == 201
        data = resp.json()

        # Required fields must be present
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["label"] == "Test"
        # target_hash serialized as string for JS BigInt safety
        assert data["target_hash"] == "1234567890"
        assert "fen" in data
        assert isinstance(data["moves"], list)
        assert data["moves"] == ["e4"]
        assert data["color"] == "white"
        assert data["match_side"] == "full"
        assert "sort_order" in data

    @pytest.mark.asyncio
    async def test_list_returns_created_bookmarks(
        self, auth_headers: dict[str, str]
    ) -> None:
        """GET /position-bookmarks returns both created bookmarks."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create 2 bookmarks
            bkm1 = await _create_bookmark(client, auth_headers, "First Bookmark")
            bkm2 = await _create_bookmark(client, auth_headers, "Second Bookmark")

            resp = await client.get("/api/position-bookmarks", headers=auth_headers)

        assert resp.status_code == 200
        bookmarks = resp.json()
        assert isinstance(bookmarks, list)
        ids = [b["id"] for b in bookmarks]
        assert bkm1["id"] in ids
        assert bkm2["id"] in ids

    @pytest.mark.asyncio
    async def test_update_label(self, auth_headers: dict[str, str]) -> None:
        """PUT /{id} updates the label; other fields remain unchanged."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await _create_bookmark(client, auth_headers, "Original Label")
            bkm_id = created["id"]
            original_hash = created["target_hash"]
            original_sort_order = created["sort_order"]

            resp = await client.put(
                f"/api/position-bookmarks/{bkm_id}",
                json={"label": "Updated Label"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        updated = resp.json()
        assert updated["label"] == "Updated Label"
        assert updated["target_hash"] == original_hash  # unchanged
        assert updated["sort_order"] == original_sort_order  # unchanged

    @pytest.mark.asyncio
    async def test_delete_returns_204(self, auth_headers: dict[str, str]) -> None:
        """DELETE /{id} returns 204 and removes the bookmark from the list."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await _create_bookmark(client, auth_headers, "To Delete")
            bkm_id = created["id"]

            del_resp = await client.delete(
                f"/api/position-bookmarks/{bkm_id}", headers=auth_headers
            )
            assert del_resp.status_code == 204

            # Confirm removal
            list_resp = await client.get("/api/position-bookmarks", headers=auth_headers)
            ids = [b["id"] for b in list_resp.json()]
            assert bkm_id not in ids

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(
        self, auth_headers: dict[str, str]
    ) -> None:
        """DELETE with a non-existent ID returns 404."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                "/api/position-bookmarks/999999999", headers=auth_headers
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(
        self, auth_headers: dict[str, str]
    ) -> None:
        """PUT with a non-existent ID returns 404."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/position-bookmarks/999999999",
                json={"label": "Ghost"},
                headers=auth_headers,
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestBookmarkReorder — Drag-reorder via HTTP
# ---------------------------------------------------------------------------


class TestBookmarkReorder:
    """Verify PUT /reorder assigns correct sort_order values."""

    @pytest.mark.asyncio
    async def test_reorder_assigns_new_sort_order(
        self, auth_headers: dict[str, str]
    ) -> None:
        """Create 3 bookmarks, reorder them reversed — sort_order reflects new positions."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            b1 = await _create_bookmark(client, auth_headers, "Reorder A")
            b2 = await _create_bookmark(client, auth_headers, "Reorder B")
            b3 = await _create_bookmark(client, auth_headers, "Reorder C")

            # Reorder: b3, b1, b2 (reversed first + last swapped)
            resp = await client.put(
                "/api/position-bookmarks/reorder",
                json={"ids": [b3["id"], b1["id"], b2["id"]]},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        reordered = resp.json()
        assert isinstance(reordered, list)

        order_map = {b["id"]: b["sort_order"] for b in reordered}
        # b3 first -> sort_order 0, b1 second -> 1, b2 third -> 2
        assert order_map[b3["id"]] == 0
        assert order_map[b1["id"]] == 1
        assert order_map[b2["id"]] == 2


# ---------------------------------------------------------------------------
# TestBookmarkMatchSide — match_side PATCH endpoint
# ---------------------------------------------------------------------------


class TestBookmarkMatchSide:
    """Verify PATCH /{id}/match-side updates match_side and recomputes target_hash."""

    @pytest.mark.asyncio
    async def test_update_match_side_mine(self, auth_headers: dict[str, str]) -> None:
        """PATCH match-side to 'mine' changes match_side and updates target_hash.

        The initial bookmark was created with match_side='full', target_hash='1234567890'.
        After switching to 'mine', the target_hash must be recomputed from the stored FEN
        (white_hash for a white bookmark) — so it changes from the original value.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create with match_side="both" (a valid non-full side to start)
            body = {
                "label": "Match Side Test",
                # Real FEN after 1.e4 — a board with a genuine position so
                # the repository can compute real white/black hashes from it
                "target_hash": "1234567890",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "moves": ["e4"],
                "color": "white",
                "match_side": "full",
            }
            created = await client.post(
                "/api/position-bookmarks", json=body, headers=auth_headers
            )
            assert created.status_code == 201
            bkm_id = created.json()["id"]
            original_hash = created.json()["target_hash"]

            resp = await client.patch(
                f"/api/position-bookmarks/{bkm_id}/match-side",
                json={"match_side": "mine"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        updated = resp.json()
        assert updated["match_side"] == "mine"
        # target_hash must have changed — 'mine' for white uses white_hash, not full_hash
        assert updated["target_hash"] != original_hash

    @pytest.mark.asyncio
    async def test_update_match_side_nonexistent_returns_404(
        self, auth_headers: dict[str, str]
    ) -> None:
        """PATCH /999999999/match-side returns 404."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                "/api/position-bookmarks/999999999/match-side",
                json={"match_side": "mine"},
                headers=auth_headers,
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestBookmarkAuth — Auth gates
# ---------------------------------------------------------------------------


class TestBookmarkAuth:
    """Verify unauthenticated requests are rejected with 401."""

    @pytest.mark.asyncio
    async def test_list_requires_auth(self) -> None:
        """GET /position-bookmarks without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/position-bookmarks")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_requires_auth(self) -> None:
        """POST /position-bookmarks without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/position-bookmarks", json=_STANDARD_BOOKMARK_BODY
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestBookmarkSuggestions — Suggestions endpoint
# ---------------------------------------------------------------------------


class TestBookmarkSuggestions:
    """Verify GET /suggestions returns a structured response."""

    @pytest.mark.asyncio
    async def test_suggestions_returns_200_empty_for_new_user(
        self, auth_headers: dict[str, str]
    ) -> None:
        """GET /suggestions returns 200 with an empty suggestions list for a user with no games."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/position-bookmarks/suggestions", headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.json()
        # The module-scoped user has no game data, so suggestions must be empty
        assert data["suggestions"] == []

    @pytest.mark.asyncio
    async def test_suggestions_structure(self, auth_headers: dict[str, str]) -> None:
        """Response has 'suggestions' key with a list value."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/position-bookmarks/suggestions", headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
