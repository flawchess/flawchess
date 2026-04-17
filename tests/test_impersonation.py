"""Integration + unit tests for admin impersonation (phase 62).

Covers D-01..D-06 and D-23 from .planning/phases/62-admin-user-impersonation/62-CONTEXT.md.

Each test:
- Uses httpx.AsyncClient with ASGITransport to hit the full FastAPI app directly.
- Promotes users to superuser via direct DB UPDATE (there is no admin-only "promote" API).
- Avoids the fastapi-users "Invalid password" flow by registering then logging in with a
  password meeting fastapi-users' default CommonPasswordValidator + MinLengthValidator.
"""

import uuid
from datetime import datetime, timezone

import httpx
import pytest
from fastapi_users.jwt import decode_jwt
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.main import app
from app.models.user import User

_JWT_AUDIENCE = ["fastapi-users:auth"]
IMPERSONATION_TTL_SECONDS = 3600  # must equal app/users.py constant
_TTL_TOLERANCE_SECONDS = 30
_DEFAULT_PASSWORD = "pw12345678"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "imp") -> str:
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
    """Flip the is_superuser flag directly in the DB."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(
            sa_update(User).where(User.id == user_id).values(is_superuser=is_superuser)
        )
        await session.commit()


async def get_user_row(test_engine, user_id: int) -> User | None:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.unique().scalar_one_or_none()


async def make_admin_and_target(
    client: httpx.AsyncClient,
    test_engine,
) -> tuple[int, str, int, str]:
    """Register an admin + target user; promote admin to superuser.

    Returns (admin_id, admin_token_after_promotion, target_id, target_token).
    The admin_token is re-issued via login AFTER promotion so it reflects the
    current is_superuser state in any downstream dependency that caches claims
    (current fastapi-users stack re-reads the User row per request, so this is
    defensive — existing tokens still work).
    """
    admin_email = unique_email("admin")
    target_email = unique_email("target")

    admin_id = await register(client, admin_email)
    target_id, target_token = await register_and_login(client, target_email)

    await set_superuser(test_engine, admin_id, True)
    admin_token = await login(client, admin_email)
    return admin_id, admin_token, target_id, target_token


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_impersonate_issues_token_with_claims(test_engine):
    """POST /api/admin/impersonate/{id} returns a JWT with the expected claims + TTL (D-01, D-03)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        admin_id, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)

        before = datetime.now(timezone.utc).timestamp()
        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        after = datetime.now(timezone.utc).timestamp()

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["target_id"] == target_id

    claims = decode_jwt(
        body["access_token"], settings.SECRET_KEY, _JWT_AUDIENCE
    )
    assert claims["sub"] == str(target_id)
    assert claims["act_as"] == target_id
    assert claims["admin_id"] == admin_id
    assert claims["is_impersonation"] is True
    # Exp ≈ now + 3600s with a tolerance window for wall-clock jitter.
    exp_delta = claims["exp"] - ((before + after) / 2)
    assert (
        IMPERSONATION_TTL_SECONDS - _TTL_TOLERANCE_SECONDS
        <= exp_delta
        <= IMPERSONATION_TTL_SECONDS + _TTL_TOLERANCE_SECONDS
    ), f"exp delta {exp_delta}s not within tolerance of {IMPERSONATION_TTL_SECONDS}s"


@pytest.mark.asyncio
async def test_impersonate_rejects_non_superuser(test_engine):
    """Regular (non-superuser) caller hitting /admin/impersonate gets 403."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, regular_token = await register_and_login(client, unique_email("regular"))
        target_id, _ = await register_and_login(client, unique_email("target2"))

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {regular_token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_impersonate_rejects_target_superuser(test_engine):
    """Cannot impersonate a user who is themselves a superuser (D-05)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        admin_id, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)
        # Promote target too — now both admin and target are superusers.
        await set_superuser(test_engine, target_id, True)

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_impersonate_rejects_nonexistent_user(test_engine):
    """Impersonating a non-existent user_id returns 404."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token, _, _ = await make_admin_and_target(client, test_engine)

        resp = await client.post(
            "/api/admin/impersonate/9999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_impersonate_rejects_inactive_user(test_engine):
    """Impersonating an inactive user returns 404."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)
        # Deactivate the target via direct DB update.
        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_maker() as session:
            await session.execute(
                sa_update(User).where(User.id == target_id).values(is_active=False)
            )
            await session.commit()

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_impersonation_token_returns_target_user(test_engine):
    """Calling /users/me/profile with an impersonation token returns the target user (D-23)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        imp_token = resp.json()["access_token"]

        profile_resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

    assert profile_resp.status_code == 200
    target_row = await get_user_row(test_engine, target_id)
    assert target_row is not None
    assert profile_resp.json()["email"] == target_row.email


@pytest.mark.asyncio
async def test_nested_impersonation_rejected(test_engine):
    """Holding an impersonation token of B, attempting to impersonate C must 403 (D-04)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token, b_id, _ = await make_admin_and_target(client, test_engine)
        c_id, _ = await register_and_login(client, unique_email("victim_c"))

        # Admin impersonates B — gets an impersonation token.
        resp = await client.post(
            f"/api/admin/impersonate/{b_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        b_imp_token = resp.json()["access_token"]

        # Using B's impersonation token, try to impersonate C — must 403.
        nested_resp = await client.post(
            f"/api/admin/impersonate/{c_id}",
            headers={"Authorization": f"Bearer {b_imp_token}"},
        )

    assert nested_resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_demoted_invalidates_token(test_engine):
    """After admin loses is_superuser, the impersonation token must be rejected (D-02)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        admin_id, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        imp_token = resp.json()["access_token"]

        # Demote admin.
        await set_superuser(test_engine, admin_id, False)

        # Impersonation token must now be rejected.
        profile_resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

    assert profile_resp.status_code == 401


@pytest.mark.asyncio
async def test_target_promoted_invalidates_token(test_engine):
    """After target becomes a superuser, the impersonation token must be rejected (D-02 / D-05)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        imp_token = resp.json()["access_token"]

        # Promote target to superuser.
        await set_superuser(test_engine, target_id, True)

        profile_resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

    assert profile_resp.status_code == 401


@pytest.mark.asyncio
async def test_regular_jwt_still_works(test_engine):
    """Non-impersonation JWTs continue to work unchanged (regression guard for ClaimAwareJWTStrategy)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, token = await register_and_login(client, unique_email("regular_jwt"))

        profile_resp = await client.get(
            "/api/users/me/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert profile_resp.status_code == 200


@pytest.mark.asyncio
async def test_impersonation_does_not_update_last_login(test_engine):
    """Issuing + using an impersonation token must not update either user's last_login (D-06)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        admin_id, admin_token, target_id, _ = await make_admin_and_target(client, test_engine)

        admin_before = await get_user_row(test_engine, admin_id)
        target_before = await get_user_row(test_engine, target_id)
        assert admin_before is not None and target_before is not None

        resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        imp_token = resp.json()["access_token"]

        # Make a few authenticated calls under the impersonation token.
        for _ in range(3):
            r = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {imp_token}"},
            )
            assert r.status_code == 200

        admin_after = await get_user_row(test_engine, admin_id)
        target_after = await get_user_row(test_engine, target_id)

    assert admin_after is not None and target_after is not None
    assert admin_after.last_login == admin_before.last_login, (
        "admin.last_login must not change when issuing an impersonation token"
    )
    assert target_after.last_login == target_before.last_login, (
        "target.last_login must not change when admin uses an impersonation token"
    )
