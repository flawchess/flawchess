"""Integration tests for GET /api/admin/users/search (phase 62).

Covers D-12 (min query length), D-13 (superuser-gated, ≤20 results, response shape),
and the superuser-exclusion hygiene requirement from Plan 02 must_haves.
"""

import uuid

import httpx
import pytest
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.user import User

_DEFAULT_PASSWORD = "pw12345678"


# ---------------------------------------------------------------------------
# Helpers (duplicated lightweight versions of test_impersonation.py helpers)
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "search") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def register(
    client: httpx.AsyncClient, email: str, password: str = _DEFAULT_PASSWORD
) -> int:
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code in (200, 201), f"register failed: {resp.status_code} {resp.text}"
    return int(resp.json()["id"])


async def login(
    client: httpx.AsyncClient, email: str, password: str = _DEFAULT_PASSWORD
) -> str:
    resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return str(resp.json()["access_token"])


async def register_and_login(
    client: httpx.AsyncClient, email: str, password: str = _DEFAULT_PASSWORD
) -> tuple[int, str]:
    user_id = await register(client, email, password)
    token = await login(client, email, password)
    return user_id, token


async def set_superuser(test_engine, user_id: int, is_superuser: bool) -> None:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(
            sa_update(User).where(User.id == user_id).values(is_superuser=is_superuser)
        )
        await session.commit()


async def set_user_fields(test_engine, user_id: int, **values) -> None:
    """UPDATE arbitrary columns on the users row (chess_com_username, lichess_username, etc.)."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(
            sa_update(User).where(User.id == user_id).values(**values)
        )
        await session.commit()


async def make_superuser(
    client: httpx.AsyncClient, test_engine
) -> tuple[int, str]:
    """Register + promote + re-login a superuser. Returns (id, token)."""
    email = unique_email("admin")
    user_id = await register(client, email)
    await set_superuser(test_engine, user_id, True)
    token = await login(client, email)
    return user_id, token


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_requires_superuser(test_engine):
    """Non-superuser caller hitting /admin/users/search gets 403 (D-13)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, regular_token = await register_and_login(client, unique_email("regular"))

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": "anything"},
            headers={"Authorization": f"Bearer {regular_token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_search_short_query_returns_empty(test_engine):
    """Query shorter than 2 characters returns an empty list (D-12)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": "a"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_by_email_ilike(test_engine):
    """Superuser can search for part of a user's email and see them."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        target_email = unique_email("needle")
        target_id = await register(client, target_email)

        # Query the unique prefix "needle" (case-mixed to exercise ILIKE)
        resp = await client.get(
            "/api/admin/users/search",
            params={"q": "NEEDLE"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    ids = {row["id"] for row in body}
    assert target_id in ids, f"target {target_id} ({target_email}) missing from results: {body}"


@pytest.mark.asyncio
async def test_search_by_chess_com_username(test_engine):
    """Searching for a chess_com_username (ILIKE, case-insensitive) finds the user."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        target_id = await register(client, unique_email("ccom"))
        # Pick a username unique enough not to collide with other test rows.
        unique_suffix = uuid.uuid4().hex[:8]
        await set_user_fields(
            test_engine, target_id, chess_com_username=f"MagnusC_{unique_suffix}"
        )

        # Lowercase query should still match (ILIKE).
        resp = await client.get(
            "/api/admin/users/search",
            params={"q": f"magnusc_{unique_suffix}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert target_id in ids


@pytest.mark.asyncio
async def test_search_by_lichess_username(test_engine):
    """Searching for a lichess_username (ILIKE) finds the user."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        target_id = await register(client, unique_email("lich"))
        unique_suffix = uuid.uuid4().hex[:8]
        await set_user_fields(
            test_engine, target_id, lichess_username=f"DrNykterstein_{unique_suffix}"
        )

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": f"DRNYKTERSTEIN_{unique_suffix}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert target_id in ids


@pytest.mark.asyncio
async def test_search_by_exact_id(test_engine):
    """Numeric query matches exact user id."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        target_id = await register(client, unique_email("byid"))

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": str(target_id)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert target_id in ids


@pytest.mark.asyncio
async def test_search_excludes_superusers(test_engine):
    """Another superuser matching ILIKE on email MUST NOT appear in results (hygiene)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        # Create another superuser whose email contains a unique shared prefix.
        unique_suffix = uuid.uuid4().hex[:8]
        super_email = f"supersearch_{unique_suffix}@example.com"
        super_id = await register(client, super_email)
        await set_superuser(test_engine, super_id, True)

        # Also create a regular user sharing the prefix — for contrast.
        regular_email = f"supersearch_{unique_suffix}_regular@example.com"
        regular_id = await register(client, regular_email)

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": f"supersearch_{unique_suffix}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    ids = {row["id"] for row in resp.json()}
    assert regular_id in ids, "regular user should be returned"
    assert super_id not in ids, "superusers must be excluded from search results"


@pytest.mark.asyncio
async def test_search_result_limit_20(test_engine):
    """Creating 25 matching users must return at most 20 rows."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        unique_suffix = uuid.uuid4().hex[:8]
        # Register 25 users all sharing the unique suffix in their email.
        for i in range(25):
            await register(client, f"limit_{unique_suffix}_{i}@example.com")

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": f"limit_{unique_suffix}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) <= 20, f"expected ≤20 results, got {len(body)}"


@pytest.mark.asyncio
async def test_search_response_shape(test_engine):
    """Every row carries id, email, chess_com_username, lichess_username, is_guest, last_login (D-13)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        target_email = unique_email("shape")
        target_id = await register(client, target_email)

        resp = await client.get(
            "/api/admin/users/search",
            params={"q": "shape"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    # Find the target row; don't assume ordering.
    matching = [row for row in body if row["id"] == target_id]
    assert matching, f"target {target_id} missing from shape-test results: {body}"
    row = matching[0]
    for key in ("id", "email", "chess_com_username", "lichess_username", "is_guest", "last_login"):
        assert key in row, f"missing key {key} in row {row}"
    assert row["email"] == target_email
    assert row["is_guest"] is False
