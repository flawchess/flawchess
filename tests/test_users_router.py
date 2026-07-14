"""Integration tests for GET/PUT /users/me/profile endpoints.

Uses httpx.AsyncClient with ASGITransport to test the FastAPI app directly.
Each test class uses a module-scoped user so registration only happens once per module.
"""

import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "user") -> str:
    """Generate a unique email address for each test run."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def _register_and_login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Register a user and return their JWT access token."""
    await client.post("/api/auth/register", json={"email": email, "password": password})
    login_resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    return login_resp.json()["access_token"]


async def _register_login_and_get_id(
    client: httpx.AsyncClient, email: str, password: str
) -> tuple[int, str]:
    """Register a user, login, and return (user_id, access_token).

    Used by BETA-01 tests that need to flip `beta_enabled` via a direct DB
    UPDATE — matches the "direct DB op only" contract from BETA-01 / T-66-04.
    """
    reg = await client.post("/api/auth/register", json={"email": email, "password": password})
    user_id = int(reg.json()["id"])
    login_resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    return user_id, login_resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = unique_email("profile")
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        token = await _register_and_login(client, email, password)

    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /users/me/profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_get_profile_returns_null_usernames(self, auth_headers):
        """GET /users/me/profile returns 200 with null usernames for a new user."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/users/me/profile", headers=auth_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert "chess_com_username" in body
        assert "lichess_username" in body
        assert body["chess_com_username"] is None
        assert body["lichess_username"] is None

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self):
        """GET /users/me/profile without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/users/me/profile")

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/me/profile
# ---------------------------------------------------------------------------


class TestPutProfile:
    @pytest.mark.asyncio
    async def test_put_profile_updates_usernames(self):
        """PUT /users/me/profile updates both usernames and GET confirms the values."""
        email = unique_email("profile_update")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token = await _register_and_login(client, email, password)
            headers = {"Authorization": f"Bearer {token}"}

            # Update both usernames
            put_resp = await client.put(
                "/api/users/me/profile",
                json={
                    "chess_com_username": "magnus2024",
                    "lichess_username": "magnus_lichess",
                },
                headers=headers,
            )
            assert put_resp.status_code == 200
            put_body = put_resp.json()
            assert put_body["chess_com_username"] == "magnus2024"
            assert put_body["lichess_username"] == "magnus_lichess"

            # GET confirms updates persisted
            get_resp = await client.get("/api/users/me/profile", headers=headers)
            assert get_resp.status_code == 200
            get_body = get_resp.json()
            assert get_body["chess_com_username"] == "magnus2024"
            assert get_body["lichess_username"] == "magnus_lichess"

    @pytest.mark.asyncio
    async def test_put_profile_unauthenticated(self):
        """PUT /users/me/profile without auth returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/users/me/profile",
                json={"chess_com_username": "testuser"},
            )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# User isolation — profile returns the authenticated user's own data
# ---------------------------------------------------------------------------


class TestProfileUserIsolation:
    @pytest.mark.asyncio
    async def test_profile_returns_own_email(self):
        """Each user's GET /users/me/profile must return their own email, not another user's."""
        email_a = unique_email("iso_a")
        email_b = unique_email("iso_b")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token_a = await _register_and_login(client, email_a, password)
            token_b = await _register_and_login(client, email_b, password)

            profile_a = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            profile_b = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token_b}"},
            )

        assert profile_a.status_code == 200
        assert profile_b.status_code == 200
        assert profile_a.json()["email"] == email_a
        assert profile_b.json()["email"] == email_b


# ---------------------------------------------------------------------------
# BETA-01: beta_enabled flag round-trip through /users/me/profile
# ---------------------------------------------------------------------------


class TestProfileBetaEnabled:
    @pytest.mark.asyncio
    async def test_profile_returns_beta_enabled_default_false(self):
        """BETA-01: a newly registered user has beta_enabled=False by default."""
        email = unique_email("beta_default")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token = await _register_and_login(client, email, password)
            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "beta_enabled" in body
        assert body["beta_enabled"] is False

    @pytest.mark.asyncio
    async def test_profile_returns_beta_enabled_true_after_db_flip(self):
        """BETA-01: direct DB UPDATE is the only way to enable the flag — verified by round-trip."""
        from sqlalchemy import update

        from app.core.database import async_session_maker

        email = unique_email("beta_flip")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)

            # Flip beta_enabled via direct DB op (the only legitimate path per BETA-01).
            async with async_session_maker() as session:
                await session.execute(
                    update(User).where(User.id == user_id).values(beta_enabled=True)
                )
                await session.commit()

            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["beta_enabled"] is True

    @pytest.mark.asyncio
    async def test_user_profile_update_does_not_change_beta_enabled(self):
        """Threat T-66-02: UserProfileUpdate must not include beta_enabled.

        PUT /users/me/profile with a payload carrying beta_enabled=false leaves the
        DB-flipped True value unchanged because Pydantic v2 silently drops unknown
        fields via its default extra="ignore".
        """
        from sqlalchemy import update

        from app.core.database import async_session_maker

        email = unique_email("beta_mass_assign")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)
            headers = {"Authorization": f"Bearer {token}"}

            # Set the flag via direct DB op (the only legitimate path per BETA-01).
            async with async_session_maker() as session:
                await session.execute(
                    update(User).where(User.id == user_id).values(beta_enabled=True)
                )
                await session.commit()

            # Attempt to disable via PUT with a malicious payload.
            put_resp = await client.put(
                "/api/users/me/profile",
                json={"chess_com_username": "legit", "beta_enabled": False},
                headers=headers,
            )
            assert put_resp.status_code == 200
            # beta_enabled stays True because UserProfileUpdate ignores unknown fields.
            assert put_resp.json()["beta_enabled"] is True

            # GET confirms persistence — the flag was not silently flipped.
            get_resp = await client.get("/api/users/me/profile", headers=headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["beta_enabled"] is True


# ---------------------------------------------------------------------------
# MAIA-04 / 151-03: current_rating (D-07 free-play ELO-selector default)
# ---------------------------------------------------------------------------


class TestProfileCurrentRating:
    @pytest.mark.asyncio
    async def test_profile_returns_null_current_rating_with_no_games(self):
        """A user with zero games gets current_rating=None (not omitted)."""
        email = unique_email("rating_none")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token = await _register_and_login(client, email, password)
            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "current_rating" in body
        assert body["current_rating"] is None

    @pytest.mark.asyncio
    async def test_profile_returns_current_rating_from_most_recent_game(self):
        """current_rating reflects the user's color rating on their most recent game."""
        import datetime

        from app.core.database import async_session_maker
        from app.repositories.game_repository import bulk_insert_games

        email = unique_email("rating_present")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)

            async with async_session_maker() as session:
                await bulk_insert_games(
                    session,
                    [
                        {
                            "user_id": user_id,
                            "platform": "chess.com",
                            "platform_game_id": f"rating-{uuid.uuid4().hex}",
                            "platform_url": "https://chess.com/game/1",
                            "pgn": '[Event "Test"]\n\n1. e4 *',
                            "result": "1-0",
                            "user_color": "white",
                            "time_control_str": "600+0",
                            "time_control_bucket": "blitz",
                            "time_control_seconds": 600,
                            "rated": True,
                            "white_username": "u",
                            "black_username": "o",
                            "white_rating": 1720,
                            "black_rating": 1650,
                            "opening_name": None,
                            "opening_eco": None,
                            "played_at": datetime.datetime.now(datetime.timezone.utc),
                        }
                    ],
                )
                await session.commit()

            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["current_rating"] == 1720


# ---------------------------------------------------------------------------
# Phase 171-02 D-07: lichess_blitz_equivalent_rating (blitz-bucket anchor)
# ---------------------------------------------------------------------------


class TestProfileLichessBlitzEquivalentRating:
    @pytest.mark.asyncio
    async def test_profile_returns_null_lichess_blitz_when_no_anchors(self):
        """A freshly registered user (no anchors at all) gets field=None, present."""
        email = unique_email("blitz_anchor_none")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            token = await _register_and_login(client, email, password)
            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "lichess_blitz_equivalent_rating" in body
        assert body["lichess_blitz_equivalent_rating"] is None

    @pytest.mark.asyncio
    async def test_profile_returns_lichess_blitz_anchor_rating(self):
        """A user with a blitz-bucket anchor gets that anchor's rating."""
        from app.core.database import async_session_maker
        from app.repositories.user_rating_anchors_repository import upsert_anchor

        email = unique_email("blitz_anchor_present")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)

            async with async_session_maker() as session:
                await upsert_anchor(
                    session,
                    user_id=user_id,
                    time_control_bucket="blitz",
                    anchor_rating=1740,
                    n_chesscom_games=0,
                    n_lichess_games=25,
                    chesscom_median_native=None,
                    lichess_median_native=1740,
                )
                await session.commit()

            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "lichess_blitz_equivalent_rating" in body
        assert body["lichess_blitz_equivalent_rating"] == 1740

    @pytest.mark.asyncio
    async def test_profile_returns_null_lichess_blitz_when_only_non_blitz_anchors(self):
        """A user with only rapid/classical anchors (no blitz) gets None -- the
        blitz-bucket semantic is deliberate, not a bug (D-07)."""
        from app.core.database import async_session_maker
        from app.repositories.user_rating_anchors_repository import upsert_anchor

        email = unique_email("blitz_anchor_nonblitz")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)

            async with async_session_maker() as session:
                await upsert_anchor(
                    session,
                    user_id=user_id,
                    time_control_bucket="rapid",
                    anchor_rating=1600,
                    n_chesscom_games=0,
                    n_lichess_games=20,
                    chesscom_median_native=None,
                    lichess_median_native=1600,
                )
                await upsert_anchor(
                    session,
                    user_id=user_id,
                    time_control_bucket="classical",
                    anchor_rating=1550,
                    n_chesscom_games=0,
                    n_lichess_games=15,
                    chesscom_median_native=None,
                    lichess_median_native=1550,
                )
                await session.commit()

            resp = await client.get(
                "/api/users/me/profile",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "lichess_blitz_equivalent_rating" in body
        assert body["lichess_blitz_equivalent_rating"] is None

    @pytest.mark.asyncio
    async def test_put_profile_returns_lichess_blitz_anchor_rating(self):
        """PUT /me/profile returns the same field with the same value as GET."""
        from app.core.database import async_session_maker
        from app.repositories.user_rating_anchors_repository import upsert_anchor

        email = unique_email("blitz_anchor_put")
        password = "testpassword123"

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_id, token = await _register_login_and_get_id(client, email, password)

            async with async_session_maker() as session:
                await upsert_anchor(
                    session,
                    user_id=user_id,
                    time_control_bucket="blitz",
                    anchor_rating=1680,
                    n_chesscom_games=10,
                    n_lichess_games=0,
                    chesscom_median_native=1700,
                    lichess_median_native=None,
                )
                await session.commit()

            resp = await client.put(
                "/api/users/me/profile",
                json={"chess_com_username": "someuser"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "lichess_blitz_equivalent_rating" in body
        assert body["lichess_blitz_equivalent_rating"] == 1680
