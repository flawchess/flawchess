"""Integration tests for GET /api/imports/eval-coverage.

Covers:
- T-91-14: Unauthenticated access returns 401
- T-91-15: Cross-user data scoping (User A's pending count not visible to User B)
- Response shape: pending_count, total_count, pct_complete, analyzed_count, in_flight_count
- Zero-games edge case: pct_complete=100, analyzed_count=0, in_flight_count=0
- All-complete case: pending_count=0, pct_complete=100
- Partial case: correct pending count and rounded pct (D-04 backward-compat regression)
- D-118-10 analyzed_count: white_blunders IS NOT NULL — lichess-eval games included;
  entry-ply-only games (evals_completed_at SET, white_blunders NULL) excluded
- D-118-12 in_flight_count: eval_jobs pending|leased rows for the user

Uses httpx AsyncClient with ASGITransport. Game rows are seeded directly via
committed DB sessions (not the rollback-scoped db_session fixture) because HTTP
requests go through an independent session path.
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
from app.models.eval_jobs import EvalJob, TIER_EXPLICIT
from app.models.game import Game

EVAL_COVERAGE_ENDPOINT = "/api/imports/eval-coverage"

# Constants per CLAUDE.md no-magic-numbers rule
PARTIAL_PENDING_COUNT = 3
PARTIAL_TOTAL_COUNT = 10
PARTIAL_EXPECTED_PCT = 70  # round(100 * (10 - 3) / 10) = 70

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

# Game category counts used for the analyzed_count distinction test
_ANALYZED_ENGINE_COUNT = 2  # white_blunders IS NOT NULL, lichess_evals_at IS NULL
_ANALYZED_LICHESS_COUNT = 1  # white_blunders IS NOT NULL, lichess_evals_at IS NOT NULL
_ENTRY_PLY_ONLY_COUNT = 1  # evals_completed_at IS NOT NULL, white_blunders IS NULL
_UNANALYZED_COUNT = 1  # all NULL
_TOTAL_COUNT = (
    _ANALYZED_ENGINE_COUNT + _ANALYZED_LICHESS_COUNT + _ENTRY_PLY_ONLY_COUNT + _UNANALYZED_COUNT
)
_EXPECTED_ANALYZED_COUNT = _ANALYZED_ENGINE_COUNT + _ANALYZED_LICHESS_COUNT  # = 3
# entry-ply-only + unanalyzed → pending (evals_completed_at IS NULL)
_EXPECTED_PENDING_COUNT = (
    _ENTRY_PLY_ONLY_COUNT + _UNANALYZED_COUNT
)  # = 2 (NOT evals_completed_at IS NULL count)

# Clarification: count_pending_evals uses evals_completed_at IS NULL.
# entry-ply-only has evals_completed_at SET → counted as non-pending.
# So only _UNANALYZED_COUNT games are actually pending.
_CORRECT_PENDING_COUNT = _UNANALYZED_COUNT  # = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(user_id: int, evals_completed_at: datetime.datetime | None = None) -> Game:
    """Build a minimal Game ORM object for seeding tests (no flaw analysis)."""
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
    )


def _make_analyzed_engine_game(user_id: int) -> Game:
    """Engine-analyzed game: white_blunders IS NOT NULL, lichess_evals_at IS NULL.
    Counts as is_analyzed (D-118-10).
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
        evals_completed_at=_NOW,
        full_evals_completed_at=_NOW,
        white_blunders=0,
        black_blunders=0,
        lichess_evals_at=None,
    )


def _make_analyzed_lichess_game(user_id: int) -> Game:
    """Lichess game with imported %evals: white_blunders IS NOT NULL, lichess_evals_at IS NOT NULL.
    Counts as is_analyzed (D-118-10) — lichess evals included.
    """
    return Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/game/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        is_computer_game=False,
        evals_completed_at=_NOW,
        white_blunders=1,
        black_blunders=0,
        lichess_evals_at=_NOW,
    )


def _make_entry_ply_only_game(user_id: int) -> Game:
    """Entry-ply analyzed game: evals_completed_at IS NOT NULL but white_blunders IS NULL.
    NOT is_analyzed (D-118-10): entry-ply eval alone does not mean flaw analysis.
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
        evals_completed_at=_NOW,
        full_evals_completed_at=None,
        white_blunders=None,
        black_blunders=None,
    )


def _make_unanalyzed_game(user_id: int) -> Game:
    """Completely unanalyzed game: all NULL. Pending and not is_analyzed."""
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
        evals_completed_at=None,
        full_evals_completed_at=None,
        white_blunders=None,
        black_blunders=None,
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
) -> list[int]:
    """Insert game rows for the given user via a committed session. Returns game IDs."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        for game in games:
            game.user_id = user_id
            session.add(game)
        await session.commit()
        return [int(g.id) for g in games]  # type: ignore[arg-type]


async def _seed_eval_job(test_engine, user_id: int, game_id: int) -> None:
    """Insert a pending eval_jobs row for a game."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        job = EvalJob(tier=TIER_EXPLICIT, user_id=user_id, game_id=game_id, status="pending")
        session.add(job)
        await session.commit()


async def _delete_games_for_user(test_engine, user_id: int) -> None:
    """Delete all seeded games (cascade-deletes eval_jobs) for cleanup."""
    from sqlalchemy import delete

    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.user_id == user_id))
        await session.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_a_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User A and return (user_id, token). Cleanup games on teardown."""
    email = f"eval_cov_a_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


@pytest_asyncio.fixture
async def user_b_client(test_engine) -> AsyncGenerator[tuple[int, str], None]:
    """Register User B and return (user_id, token). Cleanup games on teardown."""
    email = f"eval_cov_b_{uuid.uuid4().hex[:8]}@example.com"
    user_id, token = await _register_and_login(email)
    yield user_id, token
    await _delete_games_for_user(test_engine, user_id)


# ---------------------------------------------------------------------------
# Tests — existing behavior (D-04 backward-compat regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_coverage_requires_auth() -> None:
    """T-91-14: GET /api/imports/eval-coverage without token returns 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_eval_coverage_zero_games(user_a_client: tuple[int, str]) -> None:
    """User with no games returns pct_complete=100, analyzed_count=0, in_flight_count=0."""
    _user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["pending_count"] == 0
    assert body["total_count"] == 0
    assert body["pct_complete"] == 100
    assert body["analyzed_count"] == 0
    assert body["in_flight_count"] == 0


@pytest.mark.asyncio
async def test_eval_coverage_all_complete(user_a_client: tuple[int, str], test_engine) -> None:
    """User with 5 games all having evals_completed_at set returns pct_complete=100."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    games_count = 5
    games = [_make_game(user_id, evals_completed_at=_NOW) for _ in range(games_count)]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["pending_count"] == 0
    assert body["total_count"] == games_count
    assert body["pct_complete"] == 100


@pytest.mark.asyncio
async def test_eval_coverage_partial(user_a_client: tuple[int, str], test_engine) -> None:
    """D-04 backward-compat: pending_count/pct_complete unchanged by D-118-12 extension."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    complete_games = [
        _make_game(user_id, evals_completed_at=_NOW)
        for _ in range(PARTIAL_TOTAL_COUNT - PARTIAL_PENDING_COUNT)
    ]
    pending_games = [
        _make_game(user_id, evals_completed_at=None) for _ in range(PARTIAL_PENDING_COUNT)
    ]
    await _seed_games_for_user(test_engine, user_id, complete_games + pending_games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    # D-04 backward-compat regression: existing keys unchanged
    assert body["pending_count"] == PARTIAL_PENDING_COUNT
    assert body["total_count"] == PARTIAL_TOTAL_COUNT
    assert body["pct_complete"] == PARTIAL_EXPECTED_PCT
    # D-118-12 extension present
    assert "analyzed_count" in body
    assert "in_flight_count" in body


@pytest.mark.asyncio
async def test_eval_coverage_scoped_to_user(
    user_a_client: tuple[int, str],
    user_b_client: tuple[int, str],
    test_engine,
) -> None:
    """T-91-15: User B sees their own data only — User A's pending count is not leaked."""
    user_a_id, _token_a = user_a_client
    _user_b_id, token_b = user_b_client
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Seed 5 pending games for User A
    user_a_games = [_make_game(user_a_id, evals_completed_at=None) for _ in range(5)]
    await _seed_games_for_user(test_engine, user_a_id, user_a_games)

    # User B has no games — should NOT see User A's pending count
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers_b)

    assert response.status_code == 200
    body = response.json()
    assert body["pending_count"] == 0
    assert body["total_count"] == 0
    assert body["pct_complete"] == 100
    assert body["analyzed_count"] == 0
    assert body["in_flight_count"] == 0


# ---------------------------------------------------------------------------
# Tests — D-118-12 analyzed_count semantics (is_analyzed = white_blunders IS NOT NULL)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyzed_count_uses_is_analyzed_not_entry_ply(
    user_a_client: tuple[int, str], test_engine
) -> None:
    """D-118-10 correctness: analyzed_count = white_blunders IS NOT NULL.

    A mix of 4 game categories:
    - Engine-analyzed (white_blunders SET, lichess_evals_at NULL) → IS analyzed
    - Lichess-eval analyzed (white_blunders SET, lichess_evals_at SET) → IS analyzed
    - Entry-ply-only (evals_completed_at SET, white_blunders NULL) → NOT analyzed
    - Unanalyzed (all NULL) → NOT analyzed

    analyzed_count must equal the sum of the first two categories, NOT the
    entry-ply-only count (which is what a naive evals_completed_at IS NOT NULL query
    would return — the D-118-10 bug). This test proves the distinction.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    games: list[Game] = (
        [_make_analyzed_engine_game(user_id) for _ in range(_ANALYZED_ENGINE_COUNT)]
        + [_make_analyzed_lichess_game(user_id) for _ in range(_ANALYZED_LICHESS_COUNT)]
        + [_make_entry_ply_only_game(user_id) for _ in range(_ENTRY_PLY_ONLY_COUNT)]
        + [_make_unanalyzed_game(user_id) for _ in range(_UNANALYZED_COUNT)]
    )
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()

    assert body["total_count"] == _TOTAL_COUNT
    assert body["analyzed_count"] == _EXPECTED_ANALYZED_COUNT

    # Prove the distinction: analyzed_count != entry-ply-only count.
    # Entry-ply-only + analyzed-engine + analyzed-lichess all have evals_completed_at SET.
    # A naive evals_completed_at IS NOT NULL query would return _TOTAL_COUNT - 1 = 4,
    # not 3. The correct white_blunders gate returns 3.
    entry_ply_naive_count = _ANALYZED_ENGINE_COUNT + _ANALYZED_LICHESS_COUNT + _ENTRY_PLY_ONLY_COUNT
    assert body["analyzed_count"] != entry_ply_naive_count, (
        "analyzed_count equals the naive entry-ply count — D-118-10 bug: "
        "should use white_blunders IS NOT NULL, not evals_completed_at IS NOT NULL"
    )


# ---------------------------------------------------------------------------
# Tests — D-118-12 in_flight_count semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_flight_count(user_a_client: tuple[int, str], test_engine) -> None:
    """in_flight_count equals the number of pending|leased eval_jobs for the user."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # Seed 2 unanalyzed games and make 1 in-flight
    games = [_make_unanalyzed_game(user_id) for _ in range(2)]
    game_ids = await _seed_games_for_user(test_engine, user_id, games)
    # Seed one pending eval_job for game 0
    await _seed_eval_job(test_engine, user_id, game_ids[0])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    # Exactly 1 pending eval_jobs row seeded (the last_activity trigger may add
    # more via create_task — assert at least 1 to avoid flakiness)
    assert body["in_flight_count"] >= 1


@pytest.mark.asyncio
async def test_in_flight_count_zero_when_no_jobs(
    user_a_client: tuple[int, str], test_engine
) -> None:
    """in_flight_count is 0 when no eval_jobs are pending/leased for the user."""
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    # Seed analyzed games only (not pending → no auto-enqueue trigger)
    games = [_make_analyzed_engine_game(user_id) for _ in range(3)]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["in_flight_count"] == 0
    assert body["analyzed_count"] == 3
