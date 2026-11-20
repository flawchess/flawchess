"""Integration tests for GET /api/admin/activity/stats.

Covers the auth ladder (401 / 403 / 403-impersonation / 200) with the hard gate
on this endpoint alone (the SPA route is not gated), the dedicated read-only
engine, and the 300s cache shared across requests (?refresh=1 forces a rebuild).

Helper patterns are duplicated lightweight versions of test_admin_users_search.py
/ test_impersonation.py's helpers — project convention (see those files'
module docstrings): each test file's fixtures stay self-contained rather than
sharing a helpers module that has to serve every caller's slightly different
needs.
"""

import datetime
import typing
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy import update as sa_update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.user import User
from app.routers import admin_activity
from app.services import activity_queries as queries
from app.services.activity_stats import StatsCache, build_readonly_engine
from app.services.guest_service import create_guest_user
from tests.blunder_check_seed import delete_blunder_check_sessions

_DEFAULT_PASSWORD = "pw12345678"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unique_email(prefix: str = "activity") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


async def register(client: httpx.AsyncClient, email: str, password: str = _DEFAULT_PASSWORD) -> int:
    resp = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), f"register failed: {resp.status_code} {resp.text}"
    return int(resp.json()["id"])


async def login(client: httpx.AsyncClient, email: str, password: str = _DEFAULT_PASSWORD) -> str:
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


async def make_superuser(client: httpx.AsyncClient, test_engine) -> tuple[int, str]:
    """Register + promote + re-login a superuser. Returns (id, token)."""
    email = unique_email("admin")
    user_id = await register(client, email)
    await set_superuser(test_engine, user_id, True)
    token = await login(client, email)
    return user_id, token


async def touch_user_activity(client: httpx.AsyncClient, token: str) -> None:
    """Trigger one authenticated request so LastActivityMiddleware writes a
    user_activity row for `token`'s owner.

    activity_queries.fetch_window runs `SELECT min(activity_date)` /
    `max(activity_date)` through `_scalar_date`, which asserts the result is a
    `datetime.date` — on a fresh test DB with zero user_activity rows that
    assert fails (min() of an empty set is NULL), so the 200-path tests below
    need at least one row before build_payload can run for real.
    """
    resp = await client.get("/api/users/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"


def fake_payload(range_key: queries.SelectedRange = "all") -> queries.Payload:
    """A minimal, schema-complete Payload for tests that monkeypatch build_payload
    and only care about call counts / the echoed range key, not real query data."""
    return queries.Payload(
        generated_at="2026-01-01T00:00:00+00:00",
        promoted_since="2026-08-23",
        range=range_key,
        data_start="2026-01-01",
        days=["2026-01-01"],
        window_start_index=0,
        last_complete_index=0,
        activity=[],
        signups=[],
        bot=[],
        train=[],
        train_funnel={},
        solves=[],
        puzzle_difficulty=[],
        blunder_check_sessions=[],
        blunder_check_windows=[],
        blunder_check_difficulty=[],
        imports=[],
        persona=[],
        bot_players=0,
        elo=[],
        funnel=[],
        stick=[],
        conversion={},
        conversion_compare=[],
        purged_excluded={},
    )


@asynccontextmanager
async def cache_override(cache: StatsCache) -> AsyncGenerator[None, None]:
    """Point GET /admin/activity/stats at `cache` for the duration of the block.

    Mirrors conftest.py's override_get_async_session pattern: the dependency
    seam (admin_activity.get_activity_cache) lets tests avoid settings.DATABASE_URL /
    the developer's dev DB, and each test controls its own cache instance and TTL.
    """

    async def _dep() -> StatsCache:
        return cache

    app.dependency_overrides[admin_activity.get_activity_cache] = _dep
    try:
        yield
    finally:
        app.dependency_overrides.pop(admin_activity.get_activity_cache, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_requires_authentication(test_engine):  # noqa: ARG001
    """Anonymous GET /api/admin/activity/stats -> 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/admin/activity/stats")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stats_requires_superuser(test_engine):
    """Authenticated non-superuser caller -> 403."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, regular_token = await register_and_login(client, unique_email("regular"))

        resp = await client.get(
            "/api/admin/activity/stats",
            headers={"Authorization": f"Bearer {regular_token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_superuser_gets_full_payload(test_engine):
    """Superuser -> 200, body has every key of queries.Payload."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    assert resp.headers.get("cache-control") == "no-store"
    body = resp.json()
    expected_keys = set(queries.Payload.__annotations__)
    assert expected_keys <= set(body.keys()), f"missing keys: {expected_keys - set(body.keys())}"
    # The guest-Train card and its payload field were removed.
    assert "guest_train" not in body


@pytest.mark.asyncio
async def test_stats_rejects_impersonation_token(test_engine):
    """An impersonation token minted for a non-superuser target -> 403."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        target_id, _ = await register_and_login(client, unique_email("target"))

        impersonate_resp = await client.post(
            f"/api/admin/impersonate/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert impersonate_resp.status_code == 200, (
            f"{impersonate_resp.status_code} {impersonate_resp.text}"
        )
        impersonation_token = impersonate_resp.json()["access_token"]

        resp = await client.get(
            "/api/admin/activity/stats",
            headers={"Authorization": f"Bearer {impersonation_token}"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_cached_for_ttl_then_refresh_forces_rebuild(test_engine, monkeypatch):
    """Two successive GETs inside the TTL build the payload once; ?refresh=1 rebuilds."""
    build_calls = 0
    payload = fake_payload()

    async def fake_build_payload(_engine, _request, _now_utc):
        nonlocal build_calls
        build_calls += 1
        return payload

    # StatsCache.get() calls the module-level `build_payload` name inside
    # app/services/activity_stats.py, so patching that module attribute (not the imported
    # binding here) is what actually intercepts the call.
    monkeypatch.setattr("app.services.activity_stats.build_payload", fake_build_payload)

    cache = StatsCache(test_engine, ttl_seconds=300)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        async with cache_override(cache):
            resp1 = await client.get(
                "/api/admin/activity/stats", headers={"Authorization": f"Bearer {admin_token}"}
            )
            resp2 = await client.get(
                "/api/admin/activity/stats", headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert resp1.status_code == 200, f"{resp1.status_code} {resp1.text}"
            assert resp2.status_code == 200, f"{resp2.status_code} {resp2.text}"
            assert build_calls == 1, "two successive GETs inside the TTL must build only once"

            resp3 = await client.get(
                "/api/admin/activity/stats",
                params={"refresh": "1"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp3.status_code == 200, f"{resp3.status_code} {resp3.text}"
            assert build_calls == 2, "?refresh=1 must bypass the cache and rebuild"


# ---------------------------------------------------------------------------
# Range parameter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_range_param_echoed_in_body(test_engine):
    """?range=d30 returns 200 and echoes range == "d30" in the body."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                params={"range": "d30"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    assert resp.json()["range"] == "d30"


@pytest.mark.asyncio
async def test_stats_rejects_unknown_range_with_422_not_5xx(test_engine):
    """An unrecognised range value is a 422 validation failure, never a captured 5xx."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        resp = await client.get(
            "/api/admin/activity/stats",
            params={"range": "nonsense"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stats_omitting_range_behaves_as_all(test_engine):
    """Omitting `range` entirely defaults to the all-time key."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    assert resp.json()["range"] == "all"


@pytest.mark.asyncio
async def test_stats_cache_keys_range_independently(test_engine, monkeypatch):
    """Two GETs for d30 inside the TTL build once; a d7 GET builds again; a third
    d30 GET still reads the (separate) d30 cache entry."""
    build_calls: dict[str, int] = {}

    async def fake_build_payload(_engine, request, _now_utc):
        range_key = request.range_key
        build_calls[range_key] = build_calls.get(range_key, 0) + 1
        return fake_payload(range_key)

    monkeypatch.setattr("app.services.activity_stats.build_payload", fake_build_payload)

    cache = StatsCache(test_engine, ttl_seconds=300)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        headers = {"Authorization": f"Bearer {admin_token}"}

        async with cache_override(cache):
            r1 = await client.get(
                "/api/admin/activity/stats", params={"range": "d30"}, headers=headers
            )
            r2 = await client.get(
                "/api/admin/activity/stats", params={"range": "d30"}, headers=headers
            )
            assert r1.status_code == 200 and r2.status_code == 200
            assert build_calls == {"d30": 1}, "two GETs for d30 inside the TTL must build once"

            r3 = await client.get(
                "/api/admin/activity/stats", params={"range": "d7"}, headers=headers
            )
            assert r3.status_code == 200
            assert build_calls == {"d30": 1, "d7": 1}, "a different range key must build again"

            r4 = await client.get(
                "/api/admin/activity/stats", params={"range": "d30"}, headers=headers
            )
            assert r4.status_code == 200
            assert build_calls == {"d30": 1, "d7": 1}, "d30 must still read its own cache entry"


@pytest.mark.asyncio
async def test_stats_refresh_invalidates_only_its_own_range(test_engine, monkeypatch):
    """?range=d30&refresh=1 rebuilds only the d30 entry; the d7 entry survives."""
    build_calls: dict[str, int] = {}

    async def fake_build_payload(_engine, request, _now_utc):
        range_key = request.range_key
        build_calls[range_key] = build_calls.get(range_key, 0) + 1
        return fake_payload(range_key)

    monkeypatch.setattr("app.services.activity_stats.build_payload", fake_build_payload)

    cache = StatsCache(test_engine, ttl_seconds=300)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        headers = {"Authorization": f"Bearer {admin_token}"}

        async with cache_override(cache):
            await client.get("/api/admin/activity/stats", params={"range": "d30"}, headers=headers)
            await client.get("/api/admin/activity/stats", params={"range": "d7"}, headers=headers)
            assert build_calls == {"d30": 1, "d7": 1}

            refreshed = await client.get(
                "/api/admin/activity/stats",
                params={"range": "d30", "refresh": "1"},
                headers=headers,
            )
            assert refreshed.status_code == 200
            assert build_calls == {"d30": 2, "d7": 1}, "refresh must rebuild only d30"

            plain_d30 = await client.get(
                "/api/admin/activity/stats", params={"range": "d30"}, headers=headers
            )
            assert plain_d30.status_code == 200
            assert build_calls == {"d30": 2, "d7": 1}, (
                "d30 must read the refreshed entry, not rebuild"
            )

            plain_d7 = await client.get(
                "/api/admin/activity/stats", params={"range": "d7"}, headers=headers
            )
            assert plain_d7.status_code == 200
            assert build_calls == {
                "d30": 2,
                "d7": 1,
            }, "d7's cache must survive a refresh scoped to d30"


@pytest.mark.asyncio
async def test_stats_custom_window_truncates_at_end_date(test_engine):
    """start/end returns range == "custom", days ending on `end`, and truncates
    signups so a user created "today" falls outside a window ending yesterday."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        today = datetime.datetime.now(datetime.timezone.utc).date()
        start = today - datetime.timedelta(days=3)
        end = today - datetime.timedelta(days=1)

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                params={"start": start.isoformat(), "end": end.isoformat()},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    body = resp.json()
    assert body["range"] == "custom"
    assert body["days"][-1] == end.isoformat()
    assert not any(row[0] == today.isoformat() for row in body["signups"]), (
        "a signup dated after the selected end date leaked through"
    )


@pytest.mark.asyncio
async def test_stats_custom_single_past_day(test_engine):
    """start == end == yesterday returns 200 with days[-1] == yesterday (Task 2)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        yesterday = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                params={"start": yesterday.isoformat(), "end": yesterday.isoformat()},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    assert resp.json()["days"][-1] == yesterday.isoformat()


@pytest.mark.asyncio
async def test_stats_custom_today_only_includes_todays_signup(test_engine):
    """start == end == today returns 200, days[-1] == today, and today's own
    signup (the superuser this test registers) shows up -- proving today is
    analysed rather than dropped as an incomplete day."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        await touch_user_activity(client, admin_token)

        today = datetime.datetime.now(datetime.timezone.utc).date()

        cache = StatsCache(test_engine, ttl_seconds=300)
        async with cache_override(cache):
            resp = await client.get(
                "/api/admin/activity/stats",
                params={"start": today.isoformat(), "end": today.isoformat()},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
    body = resp.json()
    assert body["days"][-1] == today.isoformat()
    assert any(row[0] == today.isoformat() for row in body["signups"]), (
        "today's own signup must be included, not dropped as an incomplete day"
    )


@pytest.mark.asyncio
async def test_stats_custom_window_validation_rejections(test_engine):
    """start > end, end > today, one-of-two, and a malformed date are each a
    422, never a 5xx and never silently coerced."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        headers = {"Authorization": f"Bearer {admin_token}"}

        today = datetime.datetime.now(datetime.timezone.utc).date()
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=1)

        start_after_end = await client.get(
            "/api/admin/activity/stats",
            params={"start": today.isoformat(), "end": yesterday.isoformat()},
            headers=headers,
        )
        assert start_after_end.status_code == 422

        end_after_today = await client.get(
            "/api/admin/activity/stats",
            params={"start": yesterday.isoformat(), "end": tomorrow.isoformat()},
            headers=headers,
        )
        assert end_after_today.status_code == 422

        start_without_end = await client.get(
            "/api/admin/activity/stats",
            params={"start": yesterday.isoformat()},
            headers=headers,
        )
        assert start_without_end.status_code == 422

        end_without_start = await client.get(
            "/api/admin/activity/stats",
            params={"end": yesterday.isoformat()},
            headers=headers,
        )
        assert end_without_start.status_code == 422

        malformed = await client.get(
            "/api/admin/activity/stats",
            params={"start": "not-a-date", "end": yesterday.isoformat()},
            headers=headers,
        )
        assert malformed.status_code == 422
        assert malformed.json()  # still a JSON body, not a raw 500 page


@pytest.mark.asyncio
async def test_stats_custom_range_literal_still_rejected(test_engine):
    """?range=custom is still rejected -- RangeKey is unchanged; "custom" is
    an output-only value of SelectedRange."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)

        resp = await client.get(
            "/api/admin/activity/stats",
            params={"range": "custom"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stats_custom_window_cached_independently_of_presets(test_engine, monkeypatch):
    """Two requests for the SAME custom window build once; a request for a
    DIFFERENT custom window builds again; a preset request builds again --
    three builds total."""
    build_calls = 0

    async def fake_build_payload(_engine, request, _now_utc):
        nonlocal build_calls
        build_calls += 1
        return fake_payload(request.range_key)

    monkeypatch.setattr("app.services.activity_stats.build_payload", fake_build_payload)

    cache = StatsCache(test_engine, ttl_seconds=300)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        _, admin_token = await make_superuser(client, test_engine)
        headers = {"Authorization": f"Bearer {admin_token}"}

        today = datetime.datetime.now(datetime.timezone.utc).date()
        window_a = {
            "start": (today - datetime.timedelta(days=10)).isoformat(),
            "end": (today - datetime.timedelta(days=5)).isoformat(),
        }
        window_b = {
            "start": (today - datetime.timedelta(days=20)).isoformat(),
            "end": (today - datetime.timedelta(days=15)).isoformat(),
        }

        async with cache_override(cache):
            r1 = await client.get("/api/admin/activity/stats", params=window_a, headers=headers)
            r2 = await client.get("/api/admin/activity/stats", params=window_a, headers=headers)
            assert r1.status_code == 200 and r2.status_code == 200
            assert build_calls == 1, "two requests for the same custom window must build once"

            r3 = await client.get("/api/admin/activity/stats", params=window_b, headers=headers)
            assert r3.status_code == 200
            assert build_calls == 2, "a different custom window must build again"

            r4 = await client.get(
                "/api/admin/activity/stats", params={"range": "d30"}, headers=headers
            )
            assert r4.status_code == 200
            assert build_calls == 3, "a preset request must build independently of custom windows"


@pytest.mark.asyncio
async def test_readonly_engine_refuses_writes(test_engine):
    """build_readonly_engine's connect_args enforce a genuinely read-only session.

    End-to-end variant (plan-sanctioned alternative to introspecting
    connect_args directly): open a connection through the SAME factory the
    endpoint uses, against the test database, and prove Postgres itself
    refuses a write — default_transaction_read_only is a server setting, so
    even a CREATE TEMP TABLE (which still writes to system catalogs) fails.
    """
    url = test_engine.url.render_as_string(hide_password=False)
    engine = build_readonly_engine(url, "flawchess-test-readonly")
    try:
        async with engine.connect() as conn:
            with pytest.raises(DBAPIError):
                await conn.execute(
                    text("CREATE TEMP TABLE t_admin_activity_readonly_probe (id int)")
                )
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# resolve_window (pure function, no DB)
# ---------------------------------------------------------------------------


def test_resolve_window_all_time_covers_full_dataset():
    """`all` spans the whole dataset: no lead-in, no clamp, index 0."""
    data_start = datetime.date(2025, 1, 1)
    data_end = data_start + datetime.timedelta(days=399)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )

    window = queries.resolve_window("all", now_utc, data_start, data_end)

    assert window.window_start == data_start
    assert window.lead_in_start == data_start
    assert window.window_start_index == 0
    assert len(window.days) == 400
    assert window.days[-1] == data_end.isoformat()


def test_resolve_window_d7_ends_today_with_lead_in():
    """`d7` over an ample dataset ends on `today` and carries the full lead-in."""
    data_start = datetime.date(2025, 1, 1)
    data_end = data_start + datetime.timedelta(days=399)
    today = data_end
    now_utc = datetime.datetime.combine(today, datetime.time(12, 0), tzinfo=datetime.timezone.utc)

    window = queries.resolve_window("d7", now_utc, data_start, data_end)

    assert window.window_start == today - datetime.timedelta(days=6)
    assert window.lead_in_start == window.window_start - datetime.timedelta(
        days=queries.ROLLING_LEAD_IN_DAYS
    )
    assert window.window_start_index == queries.ROLLING_LEAD_IN_DAYS
    assert window.days[window.window_start_index] == window.window_start.isoformat()


@pytest.mark.parametrize("range_key,span", [("d30", 30), ("d90", 90)])
def test_resolve_window_30_and_90_day_ranges_end_today_inclusive(range_key, span):
    """A `d30`/`d90` window spans exactly `span` calendar days, today inclusive."""
    data_start = datetime.date(2025, 1, 1)
    data_end = data_start + datetime.timedelta(days=399)
    today = data_end
    now_utc = datetime.datetime.combine(today, datetime.time(12, 0), tzinfo=datetime.timezone.utc)

    window = queries.resolve_window(range_key, now_utc, data_start, data_end)

    assert window.window_start == today - datetime.timedelta(days=span - 1)
    assert window.lead_in_start == window.window_start - datetime.timedelta(
        days=queries.ROLLING_LEAD_IN_DAYS
    )
    assert window.window_start_index == queries.ROLLING_LEAD_IN_DAYS


def test_resolve_window_clamps_up_to_data_start_on_short_dataset():
    """A d90 window never starts before the data does (short-dataset clamp)."""
    data_start = datetime.date(2026, 8, 1)
    data_end = data_start + datetime.timedelta(days=9)  # a 10-day-old dataset
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )

    window = queries.resolve_window("d90", now_utc, data_start, data_end)

    assert window.window_start == data_start
    assert window.lead_in_start == data_start
    assert window.window_start_index == 0


def test_resolve_window_clamps_down_to_data_end_on_stale_dataset():
    """A d7 window on data that stopped 60 days ago degrades to the last data
    day rather than pointing an index past the end of `days` (stale-dataset clamp)."""
    data_start = datetime.date(2026, 1, 1)
    data_end = data_start + datetime.timedelta(days=99)
    now_utc = datetime.datetime.combine(
        data_end + datetime.timedelta(days=60), datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )

    window = queries.resolve_window("d7", now_utc, data_start, data_end)

    assert window.window_start == data_end
    assert 0 <= window.window_start_index <= len(window.days) - 1


@pytest.mark.parametrize("range_key", typing.get_args(queries.RangeKey))
def test_resolve_window_last_complete_index_keeps_current_meaning(range_key):
    """last_complete_index == len(days) - 2 when data_end is today-or-later and
    len(days) > 1, else len(days) - 1 — unchanged by the windowing feature."""
    data_start = datetime.date(2026, 1, 1)
    data_end = data_start + datetime.timedelta(days=199)
    now_today = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )

    window_today = queries.resolve_window(range_key, now_today, data_start, data_end)
    assert window_today.last_complete_index == len(window_today.days) - 2

    # Once data_end is safely in the past (not "today"), the tail is complete.
    now_stale = now_today + datetime.timedelta(days=5)
    window_stale = queries.resolve_window(range_key, now_stale, data_start, data_end)
    assert window_stale.last_complete_index == len(window_stale.days) - 1


def test_resolve_window_range_mapping_covers_every_literal_value():
    """Every RangeKey value has an entry in RANGE_WINDOW_DAYS."""
    for range_key in typing.get_args(queries.RangeKey):
        assert range_key in queries.RANGE_WINDOW_DAYS


# ---------------------------------------------------------------------------
# resolve_window custom start/end
# ---------------------------------------------------------------------------


def test_resolve_window_custom_start_end_reports_custom():
    """An explicit start/end pair starts on `start`, ends on `end`, and
    reports back as range_key == "custom"."""
    data_start = datetime.date(2025, 1, 1)
    data_end = data_start + datetime.timedelta(days=399)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )
    start = data_start + datetime.timedelta(days=50)
    end = data_start + datetime.timedelta(days=80)

    window = queries.resolve_window(
        "all", now_utc, data_start, data_end, custom_start=start, custom_end=end
    )

    assert window.range_key == "custom"
    assert window.window_start == start
    assert window.window_end == end
    assert window.days[-1] == end.isoformat()
    assert window.days[window.window_start_index] == start.isoformat()


def test_resolve_window_custom_single_day_mid_dataset_is_complete():
    """start == end on a past day gives exactly one visible day, and that
    day is complete."""
    data_start = datetime.date(2025, 1, 1)
    data_end = data_start + datetime.timedelta(days=399)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )
    day = data_start + datetime.timedelta(days=100)

    window = queries.resolve_window(
        "all", now_utc, data_start, data_end, custom_start=day, custom_end=day
    )

    assert len(window.days) - window.window_start_index == 1
    assert window.last_complete_index >= window.window_start_index


def test_resolve_window_custom_today_only_is_selectable():
    """start == end == today, with data_end at yesterday (the realistic case:
    user_activity has no row for today yet). Today must still be selectable."""
    data_end = datetime.date(2026, 3, 15)
    data_start = data_end - datetime.timedelta(days=199)
    today = data_end + datetime.timedelta(days=1)
    now_utc = datetime.datetime.combine(today, datetime.time(9, 0), tzinfo=datetime.timezone.utc)

    window = queries.resolve_window(
        "all", now_utc, data_start, data_end, custom_start=today, custom_end=today
    )

    assert window.days[-1] == today.isoformat()
    assert 0 <= window.window_start_index <= len(window.days) - 1
    assert window.last_complete_index >= 0


def test_resolve_window_custom_start_before_data_start_clamps_up():
    """A custom start earlier than the dataset clamps up to data_start."""
    data_start = datetime.date(2026, 6, 1)
    data_end = data_start + datetime.timedelta(days=29)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )
    start = data_start - datetime.timedelta(days=100)
    end = data_start + datetime.timedelta(days=5)

    window = queries.resolve_window(
        "all", now_utc, data_start, data_end, custom_start=start, custom_end=end
    )

    assert window.window_start == data_start
    assert window.window_start_index == 0


def test_resolve_window_custom_entirely_before_data_start_stays_safe():
    """A custom window that ends before data_start (the lead_in_start guard):
    `days` is non-empty and window_start_index stays in range,
    rather than raising or rendering an empty page."""
    data_start = datetime.date(2026, 6, 1)
    data_end = data_start + datetime.timedelta(days=29)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )
    start = data_start - datetime.timedelta(days=60)
    end = data_start - datetime.timedelta(days=50)

    window = queries.resolve_window(
        "all", now_utc, data_start, data_end, custom_start=start, custom_end=end
    )

    assert len(window.days) > 0
    assert 0 <= window.window_start_index <= len(window.days) - 1


@pytest.mark.parametrize("range_key", typing.get_args(queries.RangeKey))
def test_resolve_window_preset_window_end_is_data_end(range_key):
    """With custom_start/custom_end omitted, window_end == data_end for every
    preset (regression guard: presets must behave exactly as before)."""
    data_start = datetime.date(2026, 1, 1)
    data_end = data_start + datetime.timedelta(days=199)
    now_utc = datetime.datetime.combine(
        data_end, datetime.time(12, 0), tzinfo=datetime.timezone.utc
    )

    window = queries.resolve_window(range_key, now_utc, data_start, data_end)

    assert window.window_end == data_end
    assert window.range_key == range_key


# ---------------------------------------------------------------------------
# fetch_train_funnel — direct query test against test_engine.
# Self-contained seeding, per this file's own convention (see module
# docstring): a drill_sessions row plus one drill_solves row per session,
# duplicated here rather than importing tests/routers/test_train.py's
# `_seed_session`, which pre-materializes a whole puzzle-per-position batch
# this test does not need.
# ---------------------------------------------------------------------------


async def _seed_funnel_session(
    test_engine,
    user_id: int,
    session_date: datetime.date,
    *,
    status: str,
    solved: bool,
    entered: bool = False,
    started_at: datetime.datetime | None = None,
    expires_on: datetime.date | None = None,
) -> None:
    """Seed one drill_sessions row plus one drill_solves row.

    `solved=True` stamps `solved_at` on the lone solve row (the session was
    solved); `solved=False` leaves it NULL, which is exactly the "no_solve"
    condition `fetch_train_funnel` tests for on a user's FIRST session.
    `entered=True` stamps `entered_at` (Start pressed) at the row's own
    `started_at`; unentered and unsolved is a landing-page visit.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            drill_session = DrillSession(
                user_id=user_id,
                session_date=session_date,
                status=status,
                puzzle_count=1,
                expires_on=expires_on or session_date + datetime.timedelta(days=7),
            )
            started = started_at or datetime.datetime.now(datetime.timezone.utc)
            drill_session.started_at = started
            if entered:
                drill_session.entered_at = started
            session.add(drill_session)
            await session.flush()
            session.add(
                DrillSolve(
                    session_id=drill_session.id,
                    position=0,
                    user_id=user_id,
                    game_id=None,
                    ply=0,
                    source=int(DrillSource.RED_HERRING),
                    solved_at=(
                        datetime.datetime.combine(
                            session_date, datetime.time(12, 0), tzinfo=datetime.timezone.utc
                        )
                        if solved
                        else None
                    ),
                )
            )


# `fetch_train_funnel` gates starters on the GLOBAL min(entered_at), which other
# tests sharing this DB can move. Pinning an entered session far in the past
# (outside every window below) fixes that gate for both the baseline and the
# post-seed read, so the delta assertions stay deterministic.
_ENTERED_SENTINEL_AT = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)


async def _pin_entered_since(test_engine, client: httpx.AsyncClient) -> None:
    user_id, _ = await register_and_login(client, unique_email("funnel-sentinel"))
    await _seed_funnel_session(
        test_engine,
        user_id,
        _ENTERED_SENTINEL_AT.date(),
        status="expired",
        solved=False,
        entered=True,
        started_at=_ENTERED_SENTINEL_AT,
    )


def _funnel_delta(result: dict, baseline: dict) -> dict[str, int]:
    return {k: result[k] - baseline[k] for k in result if isinstance(result[k], int)}


@pytest.mark.asyncio
async def test_fetch_train_funnel_seeded_cohort(test_engine):
    """Pins every branch of the FINDING J cohort query on a seeded fixture.

    Window/data-start dates are fixed constants (not wall-clock), since
    fetch_train_funnel only ever compares `session_date` to a bound cutoff
    parameter -- the query has no dependency on "today".

      - user_zero: one entered session inside the window, unsolved ->
        zero_solve_users.
      - user_visitor: one session inside the window, never entered or solved
        (opened /train, never pressed Start) -> not a starter at all.
      - user_one_completed: one completed session inside the window ->
        finishers only (not returners).
      - user_returner: two completed sessions inside the window -> both
        finishers and returners.
      - user_predates_window: FIRST session predates the window (but is still
        inside the all-time data range), with a SECOND session inside the
        window -> excluded from the windowed cohort entirely, but present in
        the all-time cohort (and contributes to all_time finishers/returners
        via that same two-completed-session shape as user_returner).
    """
    window_start = datetime.date(2026, 6, 1)
    data_start = window_start - datetime.timedelta(days=60)
    # Wide enough to keep every seeded session (up to window_start + 10 days)
    # inside the window; the point of this fixture is the cohort's first-session
    # ENTRY predicate, not the new end-date truncation.
    window_end = window_start + datetime.timedelta(days=365)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _pin_entered_since(test_engine, client)

    # Baseline BEFORE seeding: this test file's shared test_engine can carry
    # rows from other tests (in this file or, under -n auto, other files
    # scheduled onto the same xdist worker). Asserting on the DELTA this
    # fixture introduces, rather than an absolute count, is what keeps the
    # assertions correct regardless of what else landed in this date range.
    async with test_engine.connect() as conn:
        baseline = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_zero, _ = await register_and_login(client, unique_email("funnel-zero"))
        user_visitor, _ = await register_and_login(client, unique_email("funnel-visit"))
        user_one_completed, _ = await register_and_login(client, unique_email("funnel-one"))
        user_returner, _ = await register_and_login(client, unique_email("funnel-ret"))
        user_predates_window, _ = await register_and_login(client, unique_email("funnel-pre"))

    # user_zero: single unsolved session inside the window.
    await _seed_funnel_session(
        test_engine,
        user_zero,
        window_start + datetime.timedelta(days=5),
        status="expired",
        solved=False,
        entered=True,
    )

    # user_visitor: opened /train (session composed on mount), never started.
    await _seed_funnel_session(
        test_engine,
        user_visitor,
        window_start + datetime.timedelta(days=6),
        status="expired",
        solved=False,
    )

    # user_one_completed: single completed, solved session inside the window.
    await _seed_funnel_session(
        test_engine,
        user_one_completed,
        window_start + datetime.timedelta(days=3),
        status="completed",
        solved=True,
    )

    # user_returner: two completed, solved sessions inside the window.
    await _seed_funnel_session(
        test_engine,
        user_returner,
        window_start + datetime.timedelta(days=2),
        status="completed",
        solved=True,
    )
    await _seed_funnel_session(
        test_engine,
        user_returner,
        window_start + datetime.timedelta(days=10),
        status="completed",
        solved=True,
    )

    # user_predates_window: FIRST session predates window_start (but is still
    # inside data_start..window_start), second session lands inside the
    # window. Both completed+solved, so this user also feeds all_time
    # finishers/returners -- proving the all_time_* >= windowed_* property
    # below is not a coincidence of a single-session fixture.
    await _seed_funnel_session(
        test_engine,
        user_predates_window,
        window_start - datetime.timedelta(days=30),
        status="completed",
        solved=True,
    )
    await _seed_funnel_session(
        test_engine,
        user_predates_window,
        window_start + datetime.timedelta(days=5),
        status="completed",
        solved=True,
    )

    async with test_engine.connect() as conn:
        result = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    delta = _funnel_delta(result, baseline)
    assert result["entered_since"] is not None

    # Windowed starters: user_zero, user_one_completed, user_returner (3). The
    # solved-but-unstamped sessions count via the solve fallback; user_visitor
    # never started. user_predates_window's FIRST session predates the window.
    assert delta["starters"] == 3
    assert delta["zero_solve_users"] == 1  # user_zero only, not user_visitor
    assert delta["finishers"] == 2  # user_one_completed + user_returner
    assert delta["returners"] == 1  # user_returner only

    # All-time cohort additionally includes user_predates_window (4 starters),
    # who also has 2 completed sessions -> contributes to both finishers and
    # returners there.
    assert delta["all_time_starters"] == 4
    assert delta["all_time_zero_solve_users"] == 1
    assert delta["all_time_finishers"] == 3
    assert delta["all_time_returners"] == 2

    # All-time is a superset of the windowed cohort for every metric.
    assert delta["all_time_starters"] >= delta["starters"]
    assert delta["all_time_zero_solve_users"] >= delta["zero_solve_users"]
    assert delta["all_time_finishers"] >= delta["finishers"]
    assert delta["all_time_returners"] >= delta["returners"]


@pytest.mark.asyncio
async def test_fetch_train_funnel_excludes_opener_whose_first_session_predates_window(
    test_engine,
):
    """A user whose first session predates the window never counts as an
    opener for that window, even though the same user has a later session
    that falls squarely inside it."""
    window_start = datetime.date(2026, 7, 1)
    data_start = window_start - datetime.timedelta(days=90)
    window_end = window_start + datetime.timedelta(days=365)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _pin_entered_since(test_engine, client)

    async with test_engine.connect() as conn:
        baseline = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, _ = await register_and_login(client, unique_email("funnel-excl"))

    await _seed_funnel_session(
        test_engine,
        user_id,
        window_start - datetime.timedelta(days=1),
        status="expired",
        solved=False,
        entered=True,
    )
    await _seed_funnel_session(
        test_engine,
        user_id,
        window_start + datetime.timedelta(days=1),
        status="expired",
        solved=False,
        entered=True,
    )

    async with test_engine.connect() as conn:
        result = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    delta = _funnel_delta(result, baseline)

    assert delta["starters"] == 0
    assert delta["all_time_starters"] == 1


@pytest.mark.asyncio
async def test_fetch_train_funnel_skips_sessions_before_first_enter_stamp(test_engine):
    """entered_at was not backfilled: a first session composed before the
    earliest stamp is not a starter even when it has solves, so pre-tracking
    data cannot read as a near-0% zero-solve share."""
    window_start = datetime.date(1999, 1, 1)
    data_start = window_start
    window_end = datetime.date(1999, 12, 31)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _pin_entered_since(test_engine, client)

    async with test_engine.connect() as conn:
        baseline = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_id, _ = await register_and_login(client, unique_email("funnel-pretrack"))

    await _seed_funnel_session(
        test_engine,
        user_id,
        datetime.date(1999, 6, 1),
        status="completed",
        solved=True,
        started_at=datetime.datetime(1999, 6, 1, tzinfo=datetime.timezone.utc),
    )

    async with test_engine.connect() as conn:
        result = await queries.fetch_train_funnel(conn, window_start, data_start, window_end)

    delta = _funnel_delta(result, baseline)
    assert delta["starters"] == 0
    assert delta["finishers"] == 1  # the return cohort is not gated on the stamp


# ---------------------------------------------------------------------------
# Purged-user exclusion across the game-derived cohort queries.
# Direct-query tests against test_engine, baseline-delta pattern (see
# test_fetch_train_funnel_seeded_cohort's module comment above): the shared
# engine carries rows from other tests, so every assertion is on the DELTA
# this fixture introduces.
# ---------------------------------------------------------------------------


async def _stamp_user(test_engine, user_id: int, **values: object) -> None:
    """Direct UPDATE of retained-fact / cohort columns a test needs to seed.

    These columns are stamped by production write sites (POST /imports,
    DELETE /games, guest_cleanup_service, guest_service) that this test does
    not want to drive end-to-end -- it only needs the resulting row shape.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(sa_update(User).where(User.id == user_id).values(**values))
        await session.commit()


@pytest.mark.asyncio
async def test_purged_user_excluded_from_game_derived_cohorts(test_engine):
    """A purged user is dropped from fetch_funnel/fetch_stickiness/
    fetch_conversion_compare instead of reading as "never
    imported"; fetch_purged_excluded counts it under the right cohort key;
    fetch_funnel has exactly 4 stages and no "Chess account linked" label.

    Seeds a PURGED GUEST (the real-world shape: guest cleanup / DELETE
    /games) rather than a purged registered user, so the same seed also
    exercises the _GUEST_COHORT-scoped fetch_conversion_compare, whose
    cohort predicate excludes anyone who is neither a guest nor promoted.
    """
    window_start = datetime.date(2019, 1, 1)
    # Far enough in the future to keep every user seeded "now" (real wall
    # clock) inside the window -- this test's point is the purged-user
    # exclusion, not the new end-date truncation.
    window_end = datetime.date(2099, 1, 1)

    async with test_engine.connect() as conn:
        baseline_funnel = await queries.fetch_funnel(conn, window_start, window_end)
        baseline_stick = await queries.fetch_stickiness(conn, window_start, window_end)
        baseline_compare = await queries.fetch_conversion_compare(conn, window_start, window_end)
        baseline_purged = await queries.fetch_purged_excluded(conn, window_start, window_end)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        importer_id, _ = await register_and_login(client, unique_email("purge-importer"))
        promoted_id, _ = await register_and_login(client, unique_email("purge-promoted"))

    now = datetime.datetime.now(datetime.timezone.utc)

    await _stamp_user(
        test_engine,
        importer_id,
        chess_com_username="importer_cc",
        first_import_started_at=now,
        lifetime_games_imported=5,
    )
    await _stamp_user(
        test_engine,
        promoted_id,
        promoted_at=now,
        first_import_started_at=now,
        lifetime_games_imported=3,
    )

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        guest_never_imported, _token = await create_guest_user(session)
        purged_guest, _token2 = await create_guest_user(session)

    await _stamp_user(
        test_engine,
        purged_guest.id,
        chess_com_username="purged_cc",
        first_import_started_at=now,
        lifetime_games_imported=5,
        games_purged_at=now,
    )

    async with test_engine.connect() as conn:
        funnel = await queries.fetch_funnel(conn, window_start, window_end)
        stick = await queries.fetch_stickiness(conn, window_start, window_end)
        compare = await queries.fetch_conversion_compare(conn, window_start, window_end)
        purged = await queries.fetch_purged_excluded(conn, window_start, window_end)

    # fetch_funnel: exactly 4 stages, phantom "Chess account linked" stage gone.
    assert len(funnel) == 4
    assert all(row[0] != "Chess account linked" for row in funnel)

    created_delta = [funnel[0][i] - baseline_funnel[0][i] for i in (1, 2)]
    started_delta = [funnel[1][i] - baseline_funnel[1][i] for i in (1, 2)]
    imported_delta = [funnel[2][i] - baseline_funnel[2][i] for i in (1, 2)]
    # registered: importer_id only (purged_guest excluded regardless; promoted_id
    # moved to the GUEST column via _GUEST_COHORT). guest: promoted_id +
    # guest_never_imported for "created"; only promoted_id for started/imported.
    assert created_delta == [1, 2]
    assert started_delta == [1, 1]
    assert imported_delta == [1, 1]

    # fetch_stickiness keeps RAW is_guest (not _GUEST_COHORT): promoted_id
    # (is_guest=False) lands in the "Registered" row, not "Guest".
    registered_row = next(r for r in stick if r[0] == "Registered")
    guest_row = next(r for r in stick if r[0] == "Guest")
    baseline_registered_row = next(r for r in baseline_stick if r[0] == "Registered")
    baseline_guest_row = next(r for r in baseline_stick if r[0] == "Guest")
    assert registered_row[1] - baseline_registered_row[1] == 2  # importer + promoted
    # purged_guest excluded: without exclusion this would be 1 (itself), not 0.
    assert guest_row[1] - baseline_guest_row[1] == 0
    assert guest_row[3] - baseline_guest_row[3] == 1  # guest_never_imported only

    # fetch_conversion_compare ("Imported games" row, index 0): cohort is
    # _GUEST_COHORT-scoped. purged_guest excluded: without exclusion g_import
    # (index 3) would be 1 (itself has lifetime_games_imported=5), not 0.
    imported_row = compare[0]
    baseline_imported_row = baseline_compare[0]
    assert imported_row[1] - baseline_imported_row[1] == 1  # converted hits: promoted_id
    assert imported_row[2] - baseline_imported_row[2] == 1  # converted total: promoted_id
    assert imported_row[3] - baseline_imported_row[3] == 0  # guest hits: purged excluded
    assert imported_row[4] - baseline_imported_row[4] == 1  # guest total: guest_never_imported

    # fetch_purged_excluded: purged_guest counted under the GUEST key.
    assert purged["registered"] - baseline_purged["registered"] == 0
    assert purged["guest"] - baseline_purged["guest"] == 1


# ---------------------------------------------------------------------------
# Train session outcomes (Completed / Open / Abandoned) and Blunder Check
# metrics. Direct-query tests against test_engine, baseline-delta pattern, on a
# far-future fixed day so no other test's rows land on it. `today` is passed
# explicitly, never wall-clock.
# ---------------------------------------------------------------------------

_OUTCOME_DAY = datetime.date(2031, 3, 10)
_OUTCOME_TODAY = datetime.date(2031, 3, 12)
_OUTCOME_WINDOW_END = datetime.date(2031, 3, 20)
_PAST_EXPIRY = datetime.date(2031, 3, 11)
_FUTURE_EXPIRY = datetime.date(2031, 3, 14)

_SESSION_COLS = ("sessions", "users", "completed", "abandoned", "open", "served")


def _session_row_for_day(rows: list[list[typing.Any]], day: datetime.date) -> dict[str, int]:
    """Map the row for `day` (ISO string key) to named counts, zero when absent."""
    for row in rows:
        if row[0] == day.isoformat():
            return dict(zip(_SESSION_COLS, (int(v) for v in row[1:]), strict=True))
    return dict.fromkeys(_SESSION_COLS, 0)


def _session_delta(after: dict[str, int], before: dict[str, int]) -> dict[str, int]:
    return {k: after[k] - before[k] for k in after}


async def _fresh_users(test_engine, count: int, prefix: str) -> list[int]:
    """One user per seeded session row: both Train modes allow one OPEN row per user."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return [
            (await register_and_login(client, unique_email(f"{prefix}{i}")))[0]
            for i in range(count)
        ]


@pytest.mark.asyncio
async def test_fetch_train_derives_outcomes_and_skips_unstarted(test_engine):
    """Outcome derivation and the never-started exclusion for puzzle sessions.

    Reference date 2031-03-12; every row is dated 2031-03-10. Started rows:
      A open, expires 03-11, entered      -> Abandoned (window passed)
      A2 open, expires == today, entered  -> Abandoned (the `<=` boundary)
      B open, expires 03-14, entered      -> Open
      E completed, never entered/solved   -> Completed (pre-entered_at row)
      F expired, not entered, solved row  -> Abandoned (solve fallback)
    Never started, excluded entirely:
      C open past expiry, D expired, G open in window.
    """
    async with test_engine.connect() as conn:
        baseline = _session_row_for_day(
            await queries.fetch_train(
                conn, _OUTCOME_DAY, _OUTCOME_WINDOW_END, today=_OUTCOME_TODAY
            ),
            _OUTCOME_DAY,
        )

    users = await _fresh_users(test_engine, 8, "trainout")
    a, a2, b, e, f, c, d, g = users
    day = _OUTCOME_DAY
    seeds: list[tuple[int, dict[str, typing.Any]]] = [
        (a, dict(status="open", solved=False, entered=True, expires_on=_PAST_EXPIRY)),
        (a2, dict(status="open", solved=False, entered=True, expires_on=_OUTCOME_TODAY)),
        (b, dict(status="open", solved=False, entered=True, expires_on=_FUTURE_EXPIRY)),
        (e, dict(status="completed", solved=False, expires_on=_FUTURE_EXPIRY)),
        (f, dict(status="expired", solved=True, expires_on=_PAST_EXPIRY)),
        (c, dict(status="open", solved=False, expires_on=_PAST_EXPIRY)),
        (d, dict(status="expired", solved=False, expires_on=_PAST_EXPIRY)),
        (g, dict(status="open", solved=False, expires_on=_FUTURE_EXPIRY)),
    ]
    for user_id, kwargs in seeds:
        await _seed_funnel_session(test_engine, user_id, day, **kwargs)

    async with test_engine.connect() as conn:
        after = _session_row_for_day(
            await queries.fetch_train(
                conn, _OUTCOME_DAY, _OUTCOME_WINDOW_END, today=_OUTCOME_TODAY
            ),
            _OUTCOME_DAY,
        )

    assert _session_delta(after, baseline) == {
        "sessions": 5,
        "users": 5,
        "completed": 1,
        "abandoned": 3,
        "open": 1,
        "served": 5,
    }


async def _seed_bc_session(
    test_engine,
    user_id: int,
    *,
    status: str,
    session_date: datetime.date,
    expires_on: datetime.date,
    window_count: int = 2,
    windows: typing.Sequence[tuple[int | None, int, int, datetime.datetime | None, bool]] = (),
) -> int:
    """Seed one blunder_check_sessions row plus optional windows; returns the session id.

    Each window spec is (outcome or None, points_scored, points_possible,
    ended_at or None, herring). Rows satisfy the table CHECKs: a herring window
    has no blunder position/ply and window_case HERRING; any other window has
    blunder_position 2, blunder_ply first_ply + 1 and window_case ALLOWED.
    """
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            header = BlunderCheckSession(
                user_id=user_id,
                status=status,
                window_count=window_count,
                session_date=session_date,
                expires_on=expires_on,
            )
            session.add(header)
            await session.flush()
            first_ply = 10
            for position, (outcome, scored, possible, ended_at, herring) in enumerate(windows):
                session.add(
                    BlunderCheckWindow(
                        session_id=header.id,
                        position=position,
                        user_id=user_id,
                        game_id=None,
                        is_own=True,
                        window_length=3,
                        blunder_position=None if herring else 2,
                        first_ply=first_ply,
                        blunder_ply=None if herring else first_ply + 1,
                        window_case=int(WindowCase.HERRING if herring else WindowCase.ALLOWED),
                        start_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        move_ucis="e2e4 e7e5 g1f3",
                        lead_in_plies=0,
                        points_possible=possible,
                        points_scored=scored,
                        outcome=outcome,
                        started_at=ended_at,
                        ended_at=ended_at,
                    )
                )
            return header.id


@pytest.mark.asyncio
async def test_fetch_blunder_check_sessions_derives_outcomes(test_engine):
    """Same derivation as puzzles, but every Blunder Check session counts as started.

    Reference date 2031-03-12, all rows dated 2031-03-10, window_count 2 each:
    completed -> Completed; expired -> Abandoned; open past expiry -> Abandoned;
    open expiring today -> Abandoned (boundary); open in window -> Open.
    """
    async with test_engine.connect() as conn:
        baseline = _session_row_for_day(
            await queries.fetch_blunder_check_sessions(
                conn, _OUTCOME_DAY, _OUTCOME_WINDOW_END, today=_OUTCOME_TODAY
            ),
            _OUTCOME_DAY,
        )

    users = await _fresh_users(test_engine, 5, "bcout")
    specs = [
        ("completed", _FUTURE_EXPIRY),
        ("expired", _PAST_EXPIRY),
        ("open", _PAST_EXPIRY),
        ("open", _OUTCOME_TODAY),
        ("open", _FUTURE_EXPIRY),
    ]
    session_ids: list[int] = []
    try:
        for user_id, (status, expires_on) in zip(users, specs, strict=True):
            session_ids.append(
                await _seed_bc_session(
                    test_engine,
                    user_id,
                    status=status,
                    session_date=_OUTCOME_DAY,
                    expires_on=expires_on,
                )
            )
        async with test_engine.connect() as conn:
            after = _session_row_for_day(
                await queries.fetch_blunder_check_sessions(
                    conn, _OUTCOME_DAY, _OUTCOME_WINDOW_END, today=_OUTCOME_TODAY
                ),
                _OUTCOME_DAY,
            )
    finally:
        await delete_blunder_check_sessions(test_engine, session_ids)

    assert _session_delta(after, baseline) == {
        "sessions": 5,
        "users": 5,
        "completed": 1,
        "abandoned": 3,
        "open": 1,
        "served": 10,
    }


_BC_WINDOW_COLS = (
    "windows",
    "users",
    "scored",
    "possible",
    "cleared",
    "caught",
    "missed",
    "false_alarm",
)


def _bc_window_row(rows: list[list[typing.Any]], day: datetime.date) -> dict[str, int]:
    for row in rows:
        if row[0] == day.isoformat():
            return dict(zip(_BC_WINDOW_COLS, (int(v) for v in row[1:]), strict=True))
    return dict.fromkeys(_BC_WINDOW_COLS, 0)


@pytest.mark.asyncio
async def test_fetch_blunder_check_windows_score_and_outcome_mix(test_engine):
    """Judged windows (outcome NOT NULL) bucket by ended_at day with points and mix.

    lead_in_start 2031-03-01, window_end 2031-03-20. On 03-10 four judged
    windows (one per outcome). Excluded: a started-but-unended window (outcome
    NULL) and one ended before lead_in_start. A window ended on window_end's day
    lands in that day's row.
    """
    lead_in = datetime.date(2031, 3, 1)
    noon = datetime.time(12, 0)
    utc = datetime.timezone.utc
    ended_day = datetime.datetime.combine(_OUTCOME_DAY, noon, tzinfo=utc)
    ended_last = datetime.datetime.combine(_OUTCOME_WINDOW_END, noon, tzinfo=utc)
    ended_before = datetime.datetime.combine(datetime.date(2031, 2, 28), noon, tzinfo=utc)
    last_day = _OUTCOME_WINDOW_END
    before_day = datetime.date(2031, 2, 28)

    async with test_engine.connect() as conn:
        baseline_rows = await queries.fetch_blunder_check_windows(conn, lead_in, last_day)
    baseline = {d: _bc_window_row(baseline_rows, d) for d in (_OUTCOME_DAY, last_day, before_day)}

    (user_id,) = await _fresh_users(test_engine, 1, "bcwin")
    cleared, caught, missed, false_alarm = (
        int(WindowOutcome.CLEARED),
        int(WindowOutcome.CAUGHT),
        int(WindowOutcome.MISSED),
        int(WindowOutcome.FALSE_ALARM),
    )
    session_ids: list[int] = []
    try:
        session_ids.append(
            await _seed_bc_session(
                test_engine,
                user_id,
                status="completed",
                session_date=_OUTCOME_DAY,
                expires_on=_FUTURE_EXPIRY,
                window_count=8,
                windows=[
                    (cleared, 3, 3, ended_day, True),
                    (caught, 4, 6, ended_day, False),
                    (missed, 0, 6, ended_day, False),
                    (false_alarm, 0, 3, ended_day, True),
                    (None, 0, 3, None, True),
                    (caught, 4, 6, ended_before, False),
                    (cleared, 3, 3, ended_last, True),
                ],
            )
        )
        async with test_engine.connect() as conn:
            rows = await queries.fetch_blunder_check_windows(conn, lead_in, last_day)
    finally:
        await delete_blunder_check_sessions(test_engine, session_ids)

    def delta(day: datetime.date) -> dict[str, int]:
        after = _bc_window_row(rows, day)
        return {k: after[k] - baseline[day][k] for k in after}

    assert delta(_OUTCOME_DAY) == {
        "windows": 4,
        "users": 1,
        "scored": 7,
        "possible": 18,
        "cleared": 1,
        "caught": 1,
        "missed": 1,
        "false_alarm": 1,
    }
    assert delta(last_day)["windows"] == 1
    # Ended before lead_in_start: never fetched, so no row and no delta.
    assert all(row[0] != before_day.isoformat() for row in rows)
    assert delta(before_day)["windows"] == 0


def _puzzle_difficulty(rows: list[list[typing.Any]]) -> dict[int, list[int]]:
    """fetch_puzzle_difficulty rows keyed by source, zero-filled."""
    found = {int(r[0]): [int(v) for v in r[1:]] for r in rows}
    return {int(src): found.get(int(src), [0, 0, 0, 0]) for src in DrillSource}


@pytest.mark.asyncio
async def test_fetch_puzzle_difficulty_splits_by_source(test_engine):
    """Solved puzzles group by source with the move-quality mix.

    Values are [solves, good, inaccuracy, correct_guess]. Seeded on 2031-03-10:
    SR good + SR inaccuracy + SR wrong + a legacy SR row (move_quality NULL,
    correct_move True -> good); herring good; sharp filler wrong. Excluded: an
    unsolved row and one solved before the window start (this query takes the
    window start, not the lead-in).
    """
    start = datetime.date(2031, 3, 5)
    noon = datetime.time(12, 0)
    utc = datetime.timezone.utc
    solved_day = datetime.datetime.combine(_OUTCOME_DAY, noon, tzinfo=utc)
    solved_before = datetime.datetime.combine(datetime.date(2031, 3, 4), noon, tzinfo=utc)
    sr, herring, sharp = (
        int(DrillSource.SR_ITEM),
        int(DrillSource.RED_HERRING),
        int(DrillSource.SHARP_FILLER),
    )
    good, inaccuracy, wrong = (
        int(DrillMoveQuality.GOOD),
        int(DrillMoveQuality.INACCURACY),
        int(DrillMoveQuality.WRONG),
    )
    # (source, move_quality, correct_move, correct_guess, solved_at)
    solves = [
        (sr, good, True, True, solved_day),
        (sr, inaccuracy, True, False, solved_day),
        (sr, wrong, False, True, solved_day),
        (sr, None, True, False, solved_day),  # legacy row: counts as good
        (herring, good, True, True, solved_day),
        (sharp, wrong, False, True, solved_day),
        (sr, None, None, None, None),  # unsolved: excluded
        (herring, good, True, True, solved_before),  # before the window: excluded
    ]

    async with test_engine.connect() as conn:
        baseline = _puzzle_difficulty(
            await queries.fetch_puzzle_difficulty(conn, start, _OUTCOME_WINDOW_END)
        )

    (user_id,) = await _fresh_users(test_engine, 1, "pzdiff")
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session, session.begin():
        drill_session = DrillSession(
            user_id=user_id,
            session_date=_OUTCOME_DAY,
            status="completed",
            puzzle_count=len(solves),
            expires_on=_FUTURE_EXPIRY,
        )
        session.add(drill_session)
        await session.flush()
        session.add_all(
            DrillSolve(
                session_id=drill_session.id,
                position=position,
                user_id=user_id,
                game_id=None,
                ply=position,
                source=source,
                move_quality=quality,
                correct_move=correct_move,
                correct_guess=correct_guess,
                solved_at=solved_at,
            )
            for position, (source, quality, correct_move, correct_guess, solved_at) in enumerate(
                solves
            )
        )

    async with test_engine.connect() as conn:
        after = _puzzle_difficulty(
            await queries.fetch_puzzle_difficulty(conn, start, _OUTCOME_WINDOW_END)
        )

    delta = {k: [a - b for a, b in zip(after[k], baseline[k], strict=True)] for k in after}
    assert delta == {sr: [4, 2, 1, 2], herring: [1, 1, 0, 1], sharp: [1, 0, 0, 1]}


def _bc_difficulty(rows: list[list[typing.Any]]) -> dict[tuple[int, int], list[int]]:
    """fetch_blunder_check_difficulty rows keyed by (herring, own), zero-filled."""
    found = {(int(r[0]), int(r[1])): [int(v) for v in r[2:]] for r in rows}
    return {(h, o): found.get((h, o), [0, 0, 0, 0, 0]) for h in (1, 0) for o in (1, 0)}


@pytest.mark.asyncio
async def test_fetch_blunder_check_difficulty_splits_by_type_and_ownership(test_engine):
    """Judged windows group by (red herring vs blunder window) x (own vs foreign game).

    Values are [windows, cleared, caught, missed, false_alarm]. Seeded on
    2031-03-10: herring/own cleared; herring/foreign cleared + false alarm;
    blunder/own caught + missed; blunder/foreign false alarm. Excluded: an
    unjudged window (outcome NULL) and one ended before the window start (this
    query takes the window start, not the lead-in).
    """
    start = datetime.date(2031, 3, 5)
    noon = datetime.time(12, 0)
    utc = datetime.timezone.utc
    ended_day = datetime.datetime.combine(_OUTCOME_DAY, noon, tzinfo=utc)
    ended_before = datetime.datetime.combine(datetime.date(2031, 3, 4), noon, tzinfo=utc)

    async with test_engine.connect() as conn:
        baseline = _bc_difficulty(
            await queries.fetch_blunder_check_difficulty(conn, start, _OUTCOME_WINDOW_END)
        )

    (user_id,) = await _fresh_users(test_engine, 1, "bcdiff")
    cleared, caught, missed, false_alarm = (
        int(WindowOutcome.CLEARED),
        int(WindowOutcome.CAUGHT),
        int(WindowOutcome.MISSED),
        int(WindowOutcome.FALSE_ALARM),
    )
    # Positions 1, 2 and 5 are flipped to foreign games below (the seed helper
    # writes is_own=True for every window).
    foreign_positions = [1, 2, 5]
    session_ids: list[int] = []
    try:
        session_id = await _seed_bc_session(
            test_engine,
            user_id,
            status="completed",
            session_date=_OUTCOME_DAY,
            expires_on=_FUTURE_EXPIRY,
            window_count=8,
            windows=[
                (cleared, 3, 3, ended_day, True),  # 0 herring / own
                (cleared, 3, 3, ended_day, True),  # 1 herring / foreign
                (false_alarm, 0, 3, ended_day, True),  # 2 herring / foreign
                (caught, 4, 6, ended_day, False),  # 3 blunder / own
                (missed, 0, 6, ended_day, False),  # 4 blunder / own
                (false_alarm, 0, 6, ended_day, False),  # 5 blunder / foreign
                (None, 0, 3, None, True),  # 6 unjudged: excluded
                (caught, 4, 6, ended_before, False),  # 7 before the window: excluded
            ],
        )
        session_ids.append(session_id)
        async with test_engine.begin() as conn:
            await conn.execute(
                sa_update(BlunderCheckWindow)
                .where(
                    BlunderCheckWindow.session_id == session_id,
                    BlunderCheckWindow.position.in_(foreign_positions),
                )
                .values(is_own=False)
            )
        async with test_engine.connect() as conn:
            after = _bc_difficulty(
                await queries.fetch_blunder_check_difficulty(conn, start, _OUTCOME_WINDOW_END)
            )
    finally:
        await delete_blunder_check_sessions(test_engine, session_ids)

    delta = {k: [a - b for a, b in zip(after[k], baseline[k], strict=True)] for k in after}
    assert delta == {
        (1, 1): [1, 1, 0, 0, 0],
        (1, 0): [2, 1, 0, 0, 1],
        (0, 1): [2, 0, 1, 1, 0],
        (0, 0): [1, 0, 0, 0, 1],
    }
