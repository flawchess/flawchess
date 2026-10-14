"""Emails are unique case-insensitively on every write path.

Security review 2026-10-14: guest promotion checked uniqueness with an exact match,
so a guest could promote to "Victim@x.com" while "victim@x.com" existed. FastAPI-Users
looks emails up with func.lower and expects one row, so the victim's login, password
reset and Google sign-in then failed with MultipleResultsFound (a targeted lockout).

Follows tests/test_auth.py's conventions: no rollback fixture, unique emails.
"""

import uuid

import httpx
import pytest
from fastapi_users.exceptions import UserAlreadyExists
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models.user import User
from app.services.guest_service import (
    create_guest_user,
    promote_guest_with_google,
    promote_guest_with_password,
)

PASSWORD = "victim-pass-123"


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_check_login(email: str) -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (
            await client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
        ).status_code == 201


async def _login_status(email: str) -> int:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": PASSWORD}
        )
        return resp.status_code


class TestGuestPromotionCaseInsensitive:
    @pytest.mark.asyncio
    async def test_password_promotion_rejects_case_variant(self, db_session) -> None:
        victim = unique_email("victim")
        await _register_and_check_login(victim)
        guest, _token = await create_guest_user(db_session)

        with pytest.raises(UserAlreadyExists):
            await promote_guest_with_password(db_session, guest, victim.upper(), "attacker-pass-1")

        assert await _login_status(victim) == 200

    @pytest.mark.asyncio
    async def test_google_promotion_rejects_case_variant(self, db_session) -> None:
        victim = unique_email("victim_g")
        await _register_and_check_login(victim)
        guest, _token = await create_guest_user(db_session)

        with pytest.raises(UserAlreadyExists):
            await promote_guest_with_google(
                db_session,
                guest,
                account_id=f"sub_{uuid.uuid4().hex}",
                account_email=victim.upper(),
                access_token="fake_access",
                expires_at=None,
                refresh_token=None,
            )

        assert await _login_status(victim) == 200

    @pytest.mark.asyncio
    async def test_promote_endpoint_returns_409_for_case_variant(self) -> None:
        victim = unique_email("victim_api")
        await _register_and_check_login(victim)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            guest = await client.post("/api/auth/guest/create")
            resp = await client.post(
                "/api/auth/guest/promote/email",
                json={"email": victim.upper(), "password": "attacker-pass-1"},
                headers={"Authorization": f"Bearer {guest.json()['access_token']}"},
            )
        assert resp.status_code == 409
        assert await _login_status(victim) == 200


class TestDatabaseIndex:
    @pytest.mark.asyncio
    async def test_case_variant_insert_violates_unique_index(self, db_session) -> None:
        """ix_users_email_lower closes the gap on every write path, not just the checked ones."""
        email = unique_email("indexed")
        db_session.add(User(email=email, hashed_password="x"))
        await db_session.commit()

        db_session.add(User(email=email.upper(), hashed_password="x"))
        with pytest.raises(IntegrityError, match="ix_users_email_lower"):
            await db_session.commit()
        await db_session.rollback()
