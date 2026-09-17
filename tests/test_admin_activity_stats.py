"""Integration tests for GET /api/admin/activity/stats (Quick 260824-qaz, Task 1).

Covers D-1 (SPA route, hard gate lives on this endpoint alone), D-2 (401 /
403 / 403-impersonation / 200 auth ladder), D-4 (dedicated read-only engine),
and D-5 (300s cache shared across requests, ?refresh=1 forces a rebuild).

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
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillSolve, DrillSource
from app.models.user import User
from app.routers import admin_activity
from app.services import activity_queries as queries
from app.services.activity_stats import StatsCache, build_readonly_engine
from app.services.guest_service import create_guest_user

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


def fake_payload(range_key: queries.RangeKey = "all") -> queries.Payload:
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
        imports=[],
        persona=[],
        bot_players=0,
        elo=[],
        funnel=[],
        tti=[],
        stick=[],
        conversion={},
        conversion_compare=[],
        purged_excluded={},
    )


@asynccontextmanager
async def cache_override(cache: StatsCache) -> AsyncGenerator[None, None]:
    """Point GET /admin/activity/stats at `cache` for the duration of the block.

    Mirrors conftest.py's override_get_async_session pattern: the dependency
    seam (admin_activity.get_activity_cache) is exactly what Task 1's action
    item 3 added so tests never touch settings.DATABASE_URL / the developer's
    dev DB, and each test controls its own cache instance and TTL.
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


@pytest.mark.asyncio
async def test_stats_rejects_impersonation_token(test_engine):
    """An impersonation token minted for a non-superuser target -> 403 (D-04 re-enforced)."""
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
    """Two successive GETs inside the TTL build the payload once; ?refresh=1 rebuilds (D-5)."""
    build_calls = 0
    payload = fake_payload()

    async def fake_build_payload(_engine, _range_key, _now_utc):
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
# Range parameter (Quick 260831-p7x, Task 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_range_param_echoed_in_body(test_engine):
    """?range=d30 returns 200 and echoes range == "d30" in the body (D1, D4)."""
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
    """Omitting `range` entirely defaults to the all-time key (D1, D4)."""
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
    d30 GET still reads the (separate) d30 cache entry (D4)."""
    build_calls: dict[str, int] = {}

    async def fake_build_payload(_engine, range_key, _now_utc):
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
    """?range=d30&refresh=1 rebuilds only the d30 entry; the d7 entry survives (D4)."""
    build_calls: dict[str, int] = {}

    async def fake_build_payload(_engine, range_key, _now_utc):
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
async def test_readonly_engine_refuses_writes(test_engine):
    """build_readonly_engine's connect_args enforce a genuinely read-only session (D-4).

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
# resolve_window (pure function, no DB) — Quick 260831-p7x, Task 1
# ---------------------------------------------------------------------------


def test_resolve_window_all_time_covers_full_dataset():
    """`all` spans the whole dataset: no lead-in, no clamp, index 0 (D1)."""
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
def test_resolve_window_d30_d90_end_today_inclusive(range_key, span):
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
# fetch_train_funnel (SEED-166, D-19) — direct query test against test_engine.
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
) -> None:
    """Seed one drill_sessions row plus one drill_solves row.

    `solved=True` stamps `solved_at` on the lone solve row (the session was
    solved); `solved=False` leaves it NULL, which is exactly the "no_solve"
    condition `fetch_train_funnel` tests for on a user's FIRST session.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        async with session.begin():
            drill_session = DrillSession(
                user_id=user_id,
                session_date=session_date,
                status=status,
                puzzle_count=1,
                expires_on=session_date + datetime.timedelta(days=7),
            )
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


@pytest.mark.asyncio
async def test_fetch_train_funnel_seeded_cohort(test_engine):
    """Pins every branch of the FINDING J cohort query on a seeded fixture.

    Window/data-start dates are fixed constants (not wall-clock), since
    fetch_train_funnel only ever compares `session_date` to a bound cutoff
    parameter -- the query has no dependency on "today".

      - user_zero: one session inside the window, unsolved -> zero_solve_users.
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

    # Baseline BEFORE seeding: this test file's shared test_engine can carry
    # rows from other tests (in this file or, under -n auto, other files
    # scheduled onto the same xdist worker). Asserting on the DELTA this
    # fixture introduces, rather than an absolute count, is what keeps the
    # assertions correct regardless of what else landed in this date range.
    async with test_engine.connect() as conn:
        baseline = await queries.fetch_train_funnel(conn, window_start, data_start)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        user_zero, _ = await register_and_login(client, unique_email("funnel-zero"))
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
        result = await queries.fetch_train_funnel(conn, window_start, data_start)

    delta = {key: result[key] - baseline[key] for key in result}

    # Windowed cohort: user_zero, user_one_completed, user_returner (3 openers).
    # user_predates_window is excluded -- its FIRST session predates the window.
    assert delta["openers"] == 3
    assert delta["zero_solve_users"] == 1  # user_zero only
    assert delta["finishers"] == 2  # user_one_completed + user_returner
    assert delta["returners"] == 1  # user_returner only

    # All-time cohort additionally includes user_predates_window (4 openers),
    # who also has 2 completed sessions -> contributes to both finishers and
    # returners there.
    assert delta["all_time_openers"] == 4
    assert delta["all_time_zero_solve_users"] == 1
    assert delta["all_time_finishers"] == 3
    assert delta["all_time_returners"] == 2

    # All-time is a superset of the windowed cohort for every metric.
    assert delta["all_time_openers"] >= delta["openers"]
    assert delta["all_time_zero_solve_users"] >= delta["zero_solve_users"]
    assert delta["all_time_finishers"] >= delta["finishers"]
    assert delta["all_time_returners"] >= delta["returners"]


@pytest.mark.asyncio
async def test_fetch_train_funnel_excludes_opener_whose_first_session_predates_window(
    test_engine,
):
    """A user whose first session predates the window never counts as an
    opener for that window, even though the same user has a later session
    that falls squarely inside it (RESEARCH Finding J's defining case)."""
    window_start = datetime.date(2026, 7, 1)
    data_start = window_start - datetime.timedelta(days=90)

    async with test_engine.connect() as conn:
        baseline = await queries.fetch_train_funnel(conn, window_start, data_start)

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
    )
    await _seed_funnel_session(
        test_engine,
        user_id,
        window_start + datetime.timedelta(days=1),
        status="expired",
        solved=False,
    )

    async with test_engine.connect() as conn:
        result = await queries.fetch_train_funnel(conn, window_start, data_start)

    delta = {key: result[key] - baseline[key] for key in result}

    assert delta["openers"] == 0
    assert delta["all_time_openers"] == 1


# ---------------------------------------------------------------------------
# QTE-01..04: purged-user exclusion across the game-derived cohort queries.
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
    """A purged user is dropped from fetch_funnel/fetch_time_to_import/
    fetch_stickiness/fetch_conversion_compare instead of reading as "never
    imported"; fetch_purged_excluded counts it under the right cohort key;
    fetch_funnel has exactly 4 stages and no "Chess account linked" label.

    Seeds a PURGED GUEST (the real-world shape: guest cleanup / DELETE
    /games) rather than a purged registered user, so the same seed also
    exercises the _GUEST_COHORT-scoped fetch_conversion_compare, whose
    cohort predicate excludes anyone who is neither a guest nor promoted.
    """
    window_start = datetime.date(2019, 1, 1)

    async with test_engine.connect() as conn:
        baseline_funnel = await queries.fetch_funnel(conn, window_start)
        baseline_tti = await queries.fetch_time_to_import(conn, window_start)
        baseline_stick = await queries.fetch_stickiness(conn, window_start)
        baseline_compare = await queries.fetch_conversion_compare(conn, window_start)
        baseline_purged = await queries.fetch_purged_excluded(conn, window_start)

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
        funnel = await queries.fetch_funnel(conn, window_start)
        tti = await queries.fetch_time_to_import(conn, window_start)
        stick = await queries.fetch_stickiness(conn, window_start)
        compare = await queries.fetch_conversion_compare(conn, window_start)
        purged = await queries.fetch_purged_excluded(conn, window_start)

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

    # fetch_time_to_import: "Under 5 min" (index 0) registered=importer_id,
    # guest=promoted_id; "Never" (index 4) guest=guest_never_imported.
    r0_delta = [tti[0][i] - baseline_tti[0][i] for i in (1, 2)]
    g4_delta = tti[4][2] - baseline_tti[4][2]
    assert r0_delta == [1, 1]
    assert g4_delta == 1

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
