"""Password policy (length 8-128) and the per-email login failure limiter.

Security review 2026-10-14: the backend accepted any password (the 8-char rule
lived only in the frontend) and password login had no brute-force protection.

Follows tests/test_auth.py's conventions: no rollback fixture, unique emails.
"""

import urllib.parse
import uuid
from typing import Any

import httpx
import pytest

from app.core import ip_rate_limiter
from app.core.ip_rate_limiter import _SlidingWindowRateLimiter
from app.core.login_rate_limiter import (
    _LOGIN_FAILURE_MAX_ATTEMPTS,
    _LOGIN_FAILURE_WINDOW_SECONDS,
)
from app.core.password_policy import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    password_policy_violation,
)
from app.main import app
from app.services import email_service

GOOD_PASSWORD = "good-password-123"


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _register(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    return await client.post("/api/auth/register", json={"email": email, "password": password})


async def _login(client: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    return await client.post("/api/auth/jwt/login", data={"username": email, "password": password})


class TestPasswordPolicyRule:
    @pytest.mark.parametrize(
        ("length", "accepted"),
        [
            (MIN_PASSWORD_LENGTH - 1, False),
            (MIN_PASSWORD_LENGTH, True),
            (MAX_PASSWORD_LENGTH, True),
            (MAX_PASSWORD_LENGTH + 1, False),
        ],
    )
    def test_length_bounds(self, length: int, accepted: bool) -> None:
        assert (password_policy_violation("x" * length) is None) is accepted

    def test_no_composition_rules(self) -> None:
        assert password_policy_violation("aaaaaaaa") is None


class TestPasswordPolicyEndpoints:
    @pytest.mark.asyncio
    async def test_register_rejects_short_password(self) -> None:
        async with _client() as client:
            resp = await _register(client, unique_email("short"), "x" * (MIN_PASSWORD_LENGTH - 1))
        assert resp.status_code == 400
        detail: dict[str, Any] = resp.json()["detail"]
        assert detail["code"] == "REGISTER_INVALID_PASSWORD"
        assert str(MIN_PASSWORD_LENGTH) in detail["reason"]

    @pytest.mark.asyncio
    async def test_register_rejects_overlong_password(self) -> None:
        async with _client() as client:
            resp = await _register(client, unique_email("long"), "x" * (MAX_PASSWORD_LENGTH + 1))
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_reset_rejects_short_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        recorded: dict[str, str] = {}

        async def _fake_send(
            client: httpx.AsyncClient, *, to: str, reset_url: str, user_id: int
        ) -> bool:
            recorded["reset_url"] = reset_url
            return True

        monkeypatch.setattr(email_service, "send_password_reset_email", _fake_send)
        email = unique_email("reset_short")
        async with _client() as client:
            assert (await _register(client, email, GOOD_PASSWORD)).status_code == 201
            assert (
                await client.post("/api/auth/forgot-password", json={"email": email})
            ).status_code == 202
            await email_service.drain_pending_sends()
            token = urllib.parse.parse_qs(urllib.parse.urlparse(recorded["reset_url"]).query)[
                "token"
            ][0]
            resp = await client.post(
                "/api/auth/reset-password", json={"token": token, "password": "short"}
            )
            assert resp.status_code == 400
            assert resp.json()["detail"]["code"] == "RESET_PASSWORD_INVALID_PASSWORD"
            assert (await _login(client, email, GOOD_PASSWORD)).status_code == 200

    @pytest.mark.asyncio
    async def test_guest_promotion_rejects_short_password_and_stays_guest(self) -> None:
        async with _client() as client:
            guest = await client.post("/api/auth/guest/create")
            assert guest.status_code == 201
            headers = {"Authorization": f"Bearer {guest.json()['access_token']}"}
            resp = await client.post(
                "/api/auth/guest/promote/email",
                json={"email": unique_email("promote_short"), "password": "short"},
                headers=headers,
            )
            assert resp.status_code == 400
            detail: dict[str, Any] = resp.json()["detail"]
            assert detail["code"] == "REGISTER_INVALID_PASSWORD"
            assert str(MIN_PASSWORD_LENGTH) in detail["reason"]
            profile = await client.get("/api/users/me/profile", headers=headers)
            assert profile.status_code == 200
            assert profile.json()["is_guest"] is True


class TestLoginFailureLimiter:
    @pytest.mark.asyncio
    async def test_blocks_after_max_failures_even_with_correct_password(self) -> None:
        email = unique_email("bruteforced")
        other = unique_email("bystander")
        async with _client() as client:
            assert (await _register(client, email, GOOD_PASSWORD)).status_code == 201
            assert (await _register(client, other, GOOD_PASSWORD)).status_code == 201
            for _ in range(_LOGIN_FAILURE_MAX_ATTEMPTS):
                assert (await _login(client, email, "wrong-password")).status_code == 400

            blocked = await _login(client, email.upper(), GOOD_PASSWORD)
            assert blocked.status_code == 429
            assert blocked.json()["detail"] == "LOGIN_RATE_LIMITED"
            assert (await _login(client, other, GOOD_PASSWORD)).status_code == 200

    @pytest.mark.asyncio
    async def test_unknown_email_is_limited_the_same_way(self) -> None:
        """No enumeration: a non-existent email hits the same 429 after the same count."""
        email = unique_email("ghost")
        async with _client() as client:
            for _ in range(_LOGIN_FAILURE_MAX_ATTEMPTS):
                assert (await _login(client, email, "wrong-password")).status_code == 400
            assert (await _login(client, email, "wrong-password")).status_code == 429

    @pytest.mark.asyncio
    async def test_successful_logins_are_not_counted(self) -> None:
        email = unique_email("frequent")
        async with _client() as client:
            assert (await _register(client, email, GOOD_PASSWORD)).status_code == 201
            for _ in range(_LOGIN_FAILURE_MAX_ATTEMPTS + 2):
                assert (await _login(client, email, GOOD_PASSWORD)).status_code == 200

    @pytest.mark.asyncio
    async def test_block_lifts_when_window_slides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = {"now": 1_000_000.0}
        monkeypatch.setattr(ip_rate_limiter.time, "monotonic", lambda: clock["now"])
        email = unique_email("patient")
        async with _client() as client:
            assert (await _register(client, email, GOOD_PASSWORD)).status_code == 201
            for _ in range(_LOGIN_FAILURE_MAX_ATTEMPTS):
                await _login(client, email, "wrong-password")
            assert (await _login(client, email, GOOD_PASSWORD)).status_code == 429

            clock["now"] += _LOGIN_FAILURE_WINDOW_SECONDS + 1
            assert (await _login(client, email, GOOD_PASSWORD)).status_code == 200


class TestLimiterPrimitives:
    def test_is_blocked_does_not_count(self) -> None:
        limiter = _SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
        for _ in range(5):
            assert limiter.is_blocked("k") is False
        limiter.record("k")
        assert limiter.is_blocked("k") is False
        limiter.record("k")
        assert limiter.is_blocked("k") is True
        assert limiter.is_allowed("k") is False
