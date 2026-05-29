"""Integration tests for GET /api/imports/readiness.

Phase 96 Plan 01 Task 2 — SC-1 truth-table tests for both tiers.

Covers:
- test_readiness_requires_auth: unauthenticated request returns 401
- test_readiness_scoped_to_user: User A's state does not affect User B
- test_tier1_false_when_active_import: active in-memory job → tier1=False
- test_tier2_false_when_evals_done_but_no_percentile_rows: drained games,
  no percentile rows, total > 0 → tier1=True, tier2=False
- test_tier2_true_when_evals_and_percentiles_ready: drained games + a
  UserBenchmarkPercentile row → tier2=True
- test_tier2_true_when_no_games: user with zero games, no active job →
  tier1=True, tier2=True (nothing to drain — below-floor escape)

Uses httpx AsyncClient with ASGITransport. Game rows and percentile rows are
seeded directly via committed DB sessions (not the rollback-scoped db_session
fixture) because HTTP requests go through an independent session path.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game
from app.models.user_benchmark_percentile import UserBenchmarkPercentile
from app.services import import_service, percentile_compute_registry
from app.services.canonical_slice_sql import MEDIAN_ANCHOR_MIN_GAMES

READINESS_ENDPOINT = "/api/imports/readiness"

# Constants per CLAUDE.md no-magic-numbers rule
_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
# A played_at inside the anchor SQL's 36-month recency window (NOW() - 36mo),
# so seeded games are eligible to produce a per-TC anchor. _NOW (2024) is far
# outside the window, so it cannot be used for above-floor seeding.
_RECENT_PLAYED_AT = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
# Equal-footing rating used on both sides so |white - black| <= 100 holds
# (the anchor SQL's universal equal-footing filter).
_ANCHOR_RATING = 1500
_DEFAULT_CDF_SNAPSHOT = datetime.date(2026, 3, 31)
_DEFAULT_METRIC = "score_gap"
_DEFAULT_TC = "blitz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(
    user_id: int,
    evals_completed_at: datetime.datetime | None = None,
    *,
    anchor_eligible: bool = False,
) -> Game:
    """Build a minimal Game ORM object for seeding tests.

    ``anchor_eligible=True`` populates the fields the per-TC anchor SQL needs to
    count a game toward the 30-game floor (both ratings set + equal-footing, a
    played_at inside the 36-month recency window). Left False, the game is
    counted by ``count_games_for_user`` but never produces an anchor (NULL
    ratings / NULL played_at), i.e. it is a below-floor game.
    """
    return Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://chess.com/game/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        is_computer_game=False,
        evals_completed_at=evals_completed_at,
        white_rating=_ANCHOR_RATING if anchor_eligible else None,
        black_rating=_ANCHOR_RATING if anchor_eligible else None,
        played_at=_RECENT_PLAYED_AT if anchor_eligible else None,
    )


def _make_percentile_row(user_id: int) -> UserBenchmarkPercentile:
    """Build a minimal UserBenchmarkPercentile ORM object for seeding tests."""
    return UserBenchmarkPercentile(
        user_id=user_id,
        metric=_DEFAULT_METRIC,  # type: ignore[arg-type]
        time_control_bucket=_DEFAULT_TC,  # type: ignore[arg-type]
        value=0.05,
        n_games=42,
        percentile=55.0,
        cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
    )


async def _register_and_login(email: str, password: str = "testpassword123") -> tuple[int, str]:
    """Register a user via HTTP and return (user_id, auth_token)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg_resp = await client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        assert reg_resp.status_code in (200, 201), f"register failed: {reg_resp.text}"
        user_id = int(reg_resp.json()["id"])

        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200, f"login failed: {login_resp.text}"
        token = str(login_resp.json()["access_token"])

    return user_id, token


async def _seed_games_for_user(
    test_engine,
    user_id: int,
    games: list[Game],
) -> None:
    """Insert game rows for the given user via a committed session.

    Uses a dedicated session (not db_session) so the data is visible to HTTP
    requests through the app's own session path.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        for game in games:
            game.user_id = user_id
            session.add(game)
        await session.commit()


async def _seed_percentile_row_for_user(
    test_engine,
    user_id: int,
) -> None:
    """Insert a UserBenchmarkPercentile row for the given user via a committed session."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        row = _make_percentile_row(user_id)
        session.add(row)
        await session.commit()


async def _delete_games_for_user(test_engine, user_id: int) -> None:
    """Delete all seeded games for cleanup after test."""
    from sqlalchemy import delete

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.user_id == user_id))
        await session.execute(
            delete(UserBenchmarkPercentile).where(UserBenchmarkPercentile.user_id == user_id)
        )
        await session.commit()


def _remove_job(job_id: str) -> None:
    """Remove an in-memory import job by job_id (test cleanup helper).

    Directly removes from the internal registry so the test doesn't leave
    orphaned PENDING jobs that affect other tests.
    """
    import_service._jobs.pop(job_id, None)  # noqa: SLF001


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_a_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User A and return (user_id, token). Cleanup games on teardown."""
    email = f"readiness_a_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


@pytest_asyncio.fixture
async def user_b_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User B and return (user_id, token). Cleanup games on teardown."""
    email = f"readiness_b_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readiness_requires_auth() -> None:
    """T-96-03: GET /api/imports/readiness without token returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(READINESS_ENDPOINT)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tier2_true_when_no_games(user_a_client: tuple[int, str]) -> None:
    """User with zero games, no active job → tier1=True, tier2=True.

    The below-floor escape: when total == 0 there are no evals to drain
    and no percentile rows to wait for, so Stage B is vacuously done.
    """
    _user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(READINESS_ENDPOINT, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier1"] is True
    assert data["tier2"] is True
    assert data["pending_count"] == 0
    assert data["total_count"] == 0


@pytest.mark.asyncio
async def test_tier1_false_when_active_import(
    user_a_client: tuple[int, str],
) -> None:
    """Active in-memory import job → tier1=False, tier2=False.

    Registers a job directly via import_service (in-memory registry)
    and verifies the endpoint reflects the active-import state.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # Register an active in-memory job (does not run the actual import)
    job_id = import_service.create_job(user_id, "chess.com", "testuser")
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(READINESS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier1"] is False, "tier1 must be False while import job is active"
        assert data["tier2"] is False, "tier2 must be False when tier1 is False"
    finally:
        # Clean up the in-memory job
        _remove_job(job_id)


@pytest.mark.asyncio
async def test_tier2_false_when_above_floor_evals_done_but_no_percentile_rows(
    user_a_client: tuple[int, str],
    test_engine,
) -> None:
    """Above-floor user, evals done, no percentile rows → tier2=False.

    With enough anchor-eligible games to clear the 30-game per-TC floor and
    pending_count == 0 but no Stage-B percentile rows yet, tier2 must be
    False — the user is genuinely waiting for Stage B to write rows (the
    below-floor escape must NOT fire because an anchor exists).
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # Seed exactly the floor count of anchor-eligible, fully-evaluated games.
    n_games = MEDIAN_ANCHOR_MIN_GAMES
    games = [
        _make_game(user_id, evals_completed_at=_NOW, anchor_eligible=True) for _ in range(n_games)
    ]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(READINESS_ENDPOINT, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier1"] is True
    assert data["tier2"] is False, "above-floor user with no percentile rows must stay locked"
    assert data["pending_count"] == 0
    assert data["total_count"] == n_games


@pytest.mark.asyncio
async def test_tier2_true_when_below_anchor_floor(
    user_a_client: tuple[int, str],
    test_engine,
) -> None:
    """Below-floor user, evals done, no percentile rows → tier2=True.

    Regression for the prod-145 lockout (quick-260529): a user with games but
    too few to clear the 30-game per-TC anchor floor produces no anchors and
    therefore no percentile rows, by design. Without the below-floor escape
    ``has_any_rows`` stays False forever and the endgames page is stuck on the
    "Analyzing endgames" screen even though Stockfish is done. The escape must
    unlock them once evals are drained.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # 13 evaluated games (prod user 145's exact count) — below the 30-game floor.
    n_games = 13
    assert n_games < MEDIAN_ANCHOR_MIN_GAMES
    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(n_games)]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(READINESS_ENDPOINT, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier1"] is True
    assert data["tier2"] is True, "below-floor user must unlock once evals are drained"
    assert data["pending_count"] == 0
    assert data["total_count"] == n_games


@pytest.mark.asyncio
async def test_tier2_true_when_evals_and_percentiles_ready(
    user_a_client: tuple[int, str],
    test_engine,
) -> None:
    """Drained games + percentile row → tier2=True.

    Stage B has completed (at least one UserBenchmarkPercentile row exists),
    so the endpoint signals tier2=True.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # Seed evaluated games + a percentile row (Stage B complete signal)
    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_id, games)
    await _seed_percentile_row_for_user(test_engine, user_id)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(READINESS_ENDPOINT, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tier1"] is True
    assert data["tier2"] is True, "tier2 must be True when evals done AND percentile rows exist"
    assert data["pending_count"] == 0
    assert data["total_count"] == 5


@pytest.mark.asyncio
async def test_tier2_false_while_stage_b_computing(
    user_a_client: tuple[int, str],
    test_engine,
) -> None:
    """Drained games + percentile row, but user mid-Stage-B → tier2=False.

    Quick 260529-015: identical DB state to the tier2=True case (pending==0,
    has_any_rows True), but the in-memory Stage-B registry mark forces
    tier2=False so the page does not unlock with missing/stale badges before
    compute_stage_b finishes writing the eval-dependent rows.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_id, games)
    await _seed_percentile_row_for_user(test_engine, user_id)

    percentile_compute_registry.mark(user_id)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(READINESS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier1"] is True
        assert data["tier2"] is False, "tier2 must be False while Stage B is computing"
        assert data["pending_count"] == 0
        assert data["total_count"] == 5
    finally:
        percentile_compute_registry.clear(user_id)


@pytest.mark.asyncio
async def test_tier2_true_after_stage_b_clears(
    user_a_client: tuple[int, str],
    test_engine,
) -> None:
    """Same seed as above; mark then clear → tier2=True (gate releases).

    Proves the registry gate is released once compute_stage_b clears the mark,
    with identical DB state to the locked case.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_id, games)
    await _seed_percentile_row_for_user(test_engine, user_id)

    percentile_compute_registry.mark(user_id)
    percentile_compute_registry.clear(user_id)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(READINESS_ENDPOINT, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tier1"] is True
        assert data["tier2"] is True, "tier2 must be True after the Stage-B mark is cleared"
        assert data["pending_count"] == 0
        assert data["total_count"] == 5
    finally:
        percentile_compute_registry.clear(user_id)


@pytest.mark.asyncio
async def test_readiness_scoped_to_user(
    user_a_client: tuple[int, str],
    user_b_client: tuple[int, str],
    test_engine,
) -> None:
    """T-96-01: User B sees only their own readiness state.

    User A has an active import job and no percentile rows.
    User B has no active import and a percentile row.
    User B must see tier1=True, tier2=True regardless of User A's state.
    """
    user_a_id, token_a = user_a_client
    user_b_id, token_b = user_b_client
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A: register an active job — would make tier1=False for User A
    job_id = import_service.create_job(user_a_id, "chess.com", "usera")

    # User B: seed games + percentile row → tier2=True for User B
    games_b = [_make_game(user_b_id, evals_completed_at=_NOW) for _ in range(2)]
    await _seed_games_for_user(test_engine, user_b_id, games_b)
    await _seed_percentile_row_for_user(test_engine, user_b_id)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(READINESS_ENDPOINT, headers=headers_b)

        assert response.status_code == 200
        data = response.json()
        # User B is not affected by User A's active import
        assert data["tier1"] is True, "User B's tier1 must not be affected by User A's active job"
        assert data["tier2"] is True, "User B sees their own percentile rows only"
        assert data["total_count"] == 2
    finally:
        _remove_job(job_id)
