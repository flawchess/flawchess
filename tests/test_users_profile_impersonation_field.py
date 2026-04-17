"""Integration tests for the impersonation field on GET /api/users/me/profile (D-22).

Covers:
- Impersonation token → profile.impersonation == {admin_id, target_email}
- Regular token → profile.impersonation is None
- Guest token → profile.impersonation is None
"""

import uuid

import httpx
import pytest
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.user import User

_DEFAULT_PASSWORD = "pw12345678"


def unique_email(prefix: str = "profimp") -> str:
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


async def make_admin_and_target(
    client: httpx.AsyncClient, test_engine
) -> tuple[int, str, int, str]:
    """Register admin + target; promote admin. Returns (admin_id, admin_token, target_id, target_email)."""
    admin_email = unique_email("admin")
    target_email = unique_email("target")

    admin_id = await register(client, admin_email)
    target_id = await register(client, target_email)
    await set_superuser(test_engine, admin_id, True)
    admin_token = await login(client, admin_email)
    return admin_id, admin_token, target_id, target_email


@pytest.mark.asyncio
async def test_profile_impersonation_populated_when_impersonating(test_engine):
    """With an impersonation token, /users/me/profile.impersonation == {admin_id, target_email} (D-22)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        admin_id, admin_token, target_id, target_email = await make_admin_and_target(
            client, test_engine
        )

        imp_resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert imp_resp.status_code == 200
        imp_token = imp_resp.json()["access_token"]

        profile_resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

    assert profile_resp.status_code == 200
    body = profile_resp.json()
    assert "impersonation" in body, f"missing impersonation key: {body}"
    assert body["impersonation"] == {
        "admin_id": admin_id,
        "target_email": target_email,
    }
    # The profile row itself should reflect the target, not the admin.
    assert body["email"] == target_email


@pytest.mark.asyncio
async def test_profile_impersonation_null_for_regular_token(test_engine):
    """With a regular JWT, profile.impersonation is null."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, token = await register_and_login(client, unique_email("regular"))

        resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "impersonation" in body
    assert body["impersonation"] is None


@pytest.mark.asyncio
async def test_profile_impersonation_null_for_guest_token(test_engine):
    """With a guest JWT, profile.impersonation is null."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        guest_resp = await client.post("/api/auth/guest/create")
        assert guest_resp.status_code == 201, f"guest create: {guest_resp.status_code} {guest_resp.text}"
        guest_token = guest_resp.json()["access_token"]

        resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {guest_token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "impersonation" in body
    assert body["impersonation"] is None
