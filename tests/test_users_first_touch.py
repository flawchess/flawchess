"""Integration tests for POST /users/me/first-touch (growth report item 16).

First-touch attribution is first-write-wins and only lands on freshly created
accounts; client-supplied strings are sanitized (host lowercased, path stripped
of query/fragment, over-long values truncated instead of rejected).
"""

import datetime
import uuid

import httpx
import pytest
from sqlalchemy import select, update

from app.core import database as db_module
from app.main import app
from app.models.user import User
from app.routers.users import FIRST_TOUCH_MAX_ACCOUNT_AGE
from app.schemas.users import FIRST_TOUCH_UTM_MAX_LEN

_PASSWORD = "testpassword123"

# Resolve the session maker at call time via the module: conftest swaps
# db_module.async_session_maker for the per-run test DB, and a module-level
# `from app.core.database import async_session_maker` would bind the DEV DB.


async def _register(client: httpx.AsyncClient) -> tuple[int, dict[str, str]]:
    """Register a fresh user; return (user_id, auth headers)."""
    email = f"first_touch_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/auth/register", json={"email": email, "password": _PASSWORD})
    login = await client.post(
        "/api/auth/jwt/login", data={"username": email, "password": _PASSWORD}
    )
    return int(reg.json()["id"]), {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _load(user_id: int) -> User:
    async with db_module.async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.unique().scalar_one()


async def _first_touch_is_sql_null(user_id: int) -> bool:
    """True SQL NULL check: a JSON `null` would also load as Python None."""
    async with db_module.async_session_maker() as session:
        result = await session.execute(select(User.first_touch.is_(None)).where(User.id == user_id))
        return bool(result.scalar_one())


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_records_sanitized_first_touch() -> None:
    async with _client() as client:
        user_id, headers = await _register(client)
        resp = await client.post(
            "/api/users/me/first-touch",
            json={
                "referrer_host": " WWW.Reddit.com ",
                "utm_source": "reddit",
                "utm_medium": "social",
                "utm_campaign": "x" * (FIRST_TOUCH_UTM_MAX_LEN + 50),
                "landing_path": "/auth/callback?code=abc#token=secret",
            },
            headers=headers,
        )

    assert resp.status_code == 204
    user = await _load(user_id)
    assert user.first_touch == {
        "referrer_host": "www.reddit.com",
        "utm_source": "reddit",
        "utm_medium": "social",
        "utm_campaign": "x" * FIRST_TOUCH_UTM_MAX_LEN,
        "landing_path": "/auth/callback",
    }


@pytest.mark.asyncio
async def test_first_write_wins() -> None:
    async with _client() as client:
        user_id, headers = await _register(client)
        first = await client.post(
            "/api/users/me/first-touch", json={"utm_source": "reddit"}, headers=headers
        )
        second = await client.post(
            "/api/users/me/first-touch", json={"utm_source": "youtube"}, headers=headers
        )

    assert first.status_code == second.status_code == 204
    assert (await _load(user_id)).first_touch == {"utm_source": "reddit"}


@pytest.mark.asyncio
async def test_direct_visit_is_stamped_with_null_source() -> None:
    """A direct visit stores an empty object, so "direct" differs from "never recorded"."""
    async with _client() as client:
        user_id, headers = await _register(client)
        resp = await client.post(
            "/api/users/me/first-touch",
            json={"referrer_host": "  ", "landing_path": "no-leading-slash"},
            headers=headers,
        )

    assert resp.status_code == 204
    assert (await _load(user_id)).first_touch == {}


@pytest.mark.asyncio
async def test_old_account_is_not_attributed() -> None:
    """An account older than the window (existing user, new device) stays unrecorded."""
    async with _client() as client:
        user_id, headers = await _register(client)
        backdated = datetime.datetime.now(datetime.UTC) - FIRST_TOUCH_MAX_ACCOUNT_AGE * 2
        async with db_module.async_session_maker() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(created_at=backdated)
            )
            await session.commit()
        resp = await client.post(
            "/api/users/me/first-touch", json={"utm_source": "reddit"}, headers=headers
        )

    assert resp.status_code == 204
    assert await _first_touch_is_sql_null(user_id)


@pytest.mark.asyncio
async def test_requires_auth() -> None:
    async with _client() as client:
        resp = await client.post("/api/users/me/first-touch", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_new_account_starts_as_sql_null() -> None:
    """Guards none_as_null: the ORM insert must leave SQL NULL, or the
    `first_touch IS NULL` first-write-wins predicate never matches."""
    async with _client() as client:
        user_id, _headers = await _register(client)
    assert await _first_touch_is_sql_null(user_id)
