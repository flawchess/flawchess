"""Google sign-in must not hand a pre-registered account to whoever registered it.

Security review 2026-10-14: email/password signup does not verify the address and
Google sign-in links to an existing account by email. Without the fix, an attacker
registers victim@gmail.com, the victim later signs in with Google, and the attacker's
password and token keep working on the shared account. Covers:

- Google linking an UNVERIFIED password account replaces the password and revokes
  every outstanding token (token_version bump).
- A VERIFIED account (here: one that completed a password reset) links unchanged.
- A returning Google sign-in (already linked) changes nothing.
- Google identities with email_verified false are rejected.
- Pre-feature tokens without the `tv` claim keep working at token_version 0.

Follows tests/test_auth.py's conventions: no rollback fixture, unique emails.
"""

import base64
import json
import urllib.parse
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi_users.jwt import generate_jwt
from sqlalchemy import select, update as sa_update

from app.core.config import settings
from app.core import database as db_module
from app.main import app
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.services import email_service

_CSRF_COOKIE = "flawchess_oauth_csrf"
_OAUTH_STATE_AUDIENCE = "fastapi-users:oauth-state"
_AUTH_AUDIENCE = ["fastapi-users:auth"]
_PROFILE_URL = "/api/users/me/profile"
# conftest patches app.core.database.async_session_maker onto the per-run test DB, so it
# is looked up through the module at call time (an import-time binding hits the dev DB).


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _fake_google_token(sub: str, email: str, *, email_verified: Any = True) -> dict[str, Any]:
    payload = {"sub": sub, "email": email, "email_verified": email_verified}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return {
        "access_token": "fake_access_token",
        "id_token": f"header.{payload_b64}.signature",
        "expires_at": None,
        "refresh_token": None,
    }


def _client(**kwargs: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", **kwargs
    )


async def _google_callback(
    email: str, sub: str, *, email_verified: Any = True
) -> tuple[httpx.Response, dict[str, str]]:
    """Run /auth/google/callback for a mocked Google identity; return (response, fragment)."""
    csrf = f"csrf_{uuid.uuid4().hex}"
    state = generate_jwt(
        {"csrftoken": csrf, "aud": _OAUTH_STATE_AUDIENCE}, settings.SECRET_KEY, lifetime_seconds=600
    )
    async with _client(cookies={_CSRF_COOKIE: csrf}) as client:
        with patch(
            "app.routers.auth.google_oauth_client.get_access_token",
            new=AsyncMock(
                return_value=_fake_google_token(sub, email, email_verified=email_verified)
            ),
        ):
            resp = await client.get(
                "/api/auth/google/callback",
                params={"code": "fakecode", "state": state},
                follow_redirects=False,
            )
    fragment = urllib.parse.urlparse(resp.headers.get("location", "")).fragment
    return resp, dict(urllib.parse.parse_qsl(fragment))


async def _register_and_login(email: str, password: str) -> str:
    async with _client() as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 201
        login = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": password}
        )
        assert login.status_code == 200
        return login.json()["access_token"]


async def _profile_status(token: str) -> int:
    async with _client() as client:
        resp = await client.get(_PROFILE_URL, headers={"Authorization": f"Bearer {token}"})
        return resp.status_code


async def _login_status(email: str, password: str) -> int:
    async with _client() as client:
        resp = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": password}
        )
        return resp.status_code


async def _get_user(email: str) -> User:
    async with db_module.async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))  # ty: ignore[invalid-argument-type]  # SQLAlchemy column comparisons return ColumnElement, not bool
        return result.unique().scalar_one()


async def _oauth_account_count(user_id: int) -> int:
    async with db_module.async_session_maker() as session:
        result = await session.execute(
            select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        )
        return len(result.scalars().all())


class TestGoogleClaimsUnverifiedAccount:
    @pytest.mark.asyncio
    async def test_google_link_replaces_password_and_revokes_tokens(self) -> None:
        """The pre-registered password and its token stop working once Google links."""
        email = unique_email("victim")
        attacker_password = "attacker-pass-123"
        attacker_token = await _register_and_login(email, attacker_password)
        assert await _profile_status(attacker_token) == 200

        resp, fragment = await _google_callback(email, f"sub_{uuid.uuid4().hex}")

        assert resp.status_code == 302
        assert fragment.get("password_replaced") == "1"
        assert await _profile_status(fragment["token"]) == 200
        assert await _profile_status(attacker_token) == 401
        assert await _login_status(email, attacker_password) == 400

        user = await _get_user(email)
        assert user.is_verified is True
        assert user.token_version == 1
        assert user.hashed_password != ""  # forgot-password stays available to the owner
        assert await _oauth_account_count(user.id) == 1

    @pytest.mark.asyncio
    async def test_returning_google_sign_in_changes_nothing(self) -> None:
        """Once linked, later Google sign-ins neither bump the version nor flag a replacement."""
        email = unique_email("returning")
        sub = f"sub_{uuid.uuid4().hex}"
        await _register_and_login(email, "some-pass-123")
        _resp, first = await _google_callback(email, sub)
        assert first.get("password_replaced") == "1"

        resp, second = await _google_callback(email, sub)

        assert resp.status_code == 302
        assert "password_replaced" not in second
        assert await _profile_status(first["token"]) == 200
        assert (await _get_user(email)).token_version == 1

    @pytest.mark.asyncio
    async def test_new_google_account_is_not_flagged(self) -> None:
        email = unique_email("fresh")
        resp, fragment = await _google_callback(email, f"sub_{uuid.uuid4().hex}")

        assert resp.status_code == 302
        assert "password_replaced" not in fragment
        user = await _get_user(email)
        assert user.is_verified is True
        assert user.token_version == 0


class TestVerifiedAccountLinksUnchanged:
    @pytest.mark.asyncio
    async def test_password_reset_verifies_and_revokes_then_google_keeps_password(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A completed reset proves ownership: old tokens die, Google later keeps the password."""
        recorded: dict[str, str] = {}

        async def _fake_send(
            client: httpx.AsyncClient, *, to: str, reset_url: str, user_id: int
        ) -> bool:
            recorded["reset_url"] = reset_url
            return True

        monkeypatch.setattr(email_service, "send_password_reset_email", _fake_send)

        email = unique_email("resetter")
        old_token = await _register_and_login(email, "old-pass-123")
        async with _client() as client:
            forgot = await client.post("/api/auth/forgot-password", json={"email": email})
            assert forgot.status_code == 202
            await email_service.drain_pending_sends()
            reset_token = urllib.parse.parse_qs(urllib.parse.urlparse(recorded["reset_url"]).query)[
                "token"
            ][0]
            reset = await client.post(
                "/api/auth/reset-password",
                json={"token": reset_token, "password": "new-pass-456"},
            )
            assert reset.status_code == 200

        user = await _get_user(email)
        assert user.is_verified is True
        assert user.token_version == 1
        assert await _profile_status(old_token) == 401

        _resp, fragment = await _google_callback(email, f"sub_{uuid.uuid4().hex}")

        assert "password_replaced" not in fragment
        assert await _login_status(email, "new-pass-456") == 200
        assert (await _get_user(email)).token_version == 1


class TestGoogleEmailVerifiedClaim:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("email_verified", [False, "false", None])
    async def test_unverified_google_email_is_rejected(self, email_verified: Any) -> None:
        email = unique_email("unverified_google")
        password = "keep-me-123"
        token = await _register_and_login(email, password)

        resp, _fragment = await _google_callback(
            email, f"sub_{uuid.uuid4().hex}", email_verified=email_verified
        )

        assert resp.status_code == 400
        user = await _get_user(email)
        assert await _oauth_account_count(user.id) == 0
        assert user.token_version == 0
        assert await _profile_status(token) == 200
        assert await _login_status(email, password) == 200


class TestTokenVersionClaim:
    @pytest.mark.asyncio
    async def test_pre_feature_token_without_claim_is_accepted_at_version_zero(self) -> None:
        email = unique_email("legacy_token")
        await _register_and_login(email, "legacy-pass-123")
        user = await _get_user(email)
        legacy = generate_jwt(
            {"sub": str(user.id), "aud": _AUTH_AUDIENCE}, settings.SECRET_KEY, 3600
        )

        assert await _profile_status(legacy) == 200

        async with db_module.async_session_maker() as session:
            await session.execute(sa_update(User).where(User.id == user.id).values(token_version=1))
            await session.commit()

        assert await _profile_status(legacy) == 401
