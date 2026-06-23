"""Integration tests for GET /api/imports/eval-coverage.

Covers:
- T-91-14: Unauthenticated access returns 401
- T-91-15: Cross-user data scoping (User A's pending count not visible to User B)
- Response shape: pending_count, total_count, pct_complete, analyzed_count
- Zero-games edge case: pct_complete=100, analyzed_count=0
- All-complete case: pending_count=0, pct_complete=100
- Partial case: correct pending count and rounded pct (D-04 backward-compat regression)
- analyzed_count: full_evals_completed_at IS NOT NULL (FlawChess's own full analysis,
  the same gate the Library cards use). Lichess games imported with bundled analysis
  (white_blunders SET at import, full_evals_completed_at NULL) are NOT counted until
  the drain runs — the badge agrees with the per-game cards. total_count is every
  imported game.

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
from app.models.game import Game

EVAL_COVERAGE_ENDPOINT = "/api/imports/eval-coverage"

# Constants per CLAUDE.md no-magic-numbers rule
PARTIAL_PENDING_COUNT = 3
PARTIAL_TOTAL_COUNT = 10
PARTIAL_EXPECTED_PCT = 70  # round(100 * (10 - 3) / 10) = 70

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

# Game category counts used for the analyzed_count distinction test
_ANALYZED_ENGINE_COUNT = 2  # full_evals_completed_at SET → analyzed
_ANALYZED_LICHESS_COUNT = 1  # white_blunders SET at import, full_evals NULL → NOT analyzed
_ENTRY_PLY_ONLY_COUNT = 1  # evals_completed_at SET, full_evals NULL → NOT analyzed
_UNANALYZED_COUNT = 1  # all NULL → NOT analyzed
_TOTAL_COUNT = (
    _ANALYZED_ENGINE_COUNT + _ANALYZED_LICHESS_COUNT + _ENTRY_PLY_ONLY_COUNT + _UNANALYZED_COUNT
)
# analyzed_count = full_evals_completed_at IS NOT NULL → only the engine games.
# The lichess-bundled-analysis game is excluded (the bug this fixes).
_EXPECTED_ANALYZED_COUNT = _ANALYZED_ENGINE_COUNT  # = 2


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
    """Lichess game with bundled analysis: white_blunders SET at import, full_evals NULL.

    This is the bug case: lichess imports the analysis block (white_blunders) at
    import time, but FlawChess's own full-eval drain has NOT run
    (full_evals_completed_at IS NULL). The Library card still shows "Analyze", so
    the badge must NOT count it as analyzed.
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


def _make_unanalyzable_game(user_id: int) -> Game:
    """Degenerate game post-drain: full_evals_completed_at SET but white_blunders NULL.

    Models a zero-move / ultra-short game post-drain: the full-eval drain finished
    (full_evals_completed_at SET) and entry-ply evals are marked done
    (evals_completed_at SET), but classify_game_flaws returned GameNotAnalyzed so
    white_blunders stayed NULL. full_evals_completed_at IS NOT NULL → it counts as
    analyzed (its card shows no "Analyze" button), so "X of X" stays reachable.
    """
    return Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://chess.com/game/test",
        pgn="1-0",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        is_computer_game=False,
        evals_completed_at=_NOW,
        full_evals_completed_at=_NOW,
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
    """User with no games returns pct_complete=100, analyzed_count=0."""
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
    assert "in_flight_count" not in body


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
    # D-118-12 extension present; in_flight_count removed in Phase 119-03
    assert "analyzed_count" in body
    assert "in_flight_count" not in body


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
    assert "in_flight_count" not in body


# ---------------------------------------------------------------------------
# Tests — analyzed_count semantics (full_evals_completed_at IS NOT NULL)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyzed_count_uses_full_evals_not_white_blunders(
    user_a_client: tuple[int, str], test_engine
) -> None:
    """analyzed_count = full_evals_completed_at IS NOT NULL (matches Library cards).

    A mix of 4 game categories:
    - Engine-analyzed (full_evals_completed_at SET) → IS analyzed
    - Lichess bundled analysis (white_blunders SET at import, full_evals NULL) → NOT
      analyzed (the bug: this used to count as analyzed and inflate the badge)
    - Entry-ply-only (evals_completed_at SET, full_evals NULL) → NOT analyzed
    - Unanalyzed (all NULL) → NOT analyzed

    total_count is every imported game; analyzed_count is only the engine category.
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

    # total_count is every imported game (not an "analyzable" subset).
    assert body["total_count"] == _TOTAL_COUNT
    # Only the engine category has full_evals_completed_at SET.
    assert body["analyzed_count"] == _EXPECTED_ANALYZED_COUNT

    # Regression guard for the reported bug: the lichess-bundled-analysis game has
    # white_blunders SET, so a white_blunders-gated count would include it and read
    # "analyzed". full_evals_completed_at IS NOT NULL correctly excludes it.
    white_blunders_naive_count = _ANALYZED_ENGINE_COUNT + _ANALYZED_LICHESS_COUNT
    assert body["analyzed_count"] != white_blunders_naive_count, (
        "analyzed_count counts the lichess bundled-analysis game — the bug: "
        "should gate on full_evals_completed_at IS NOT NULL, not white_blunders"
    )


# ---------------------------------------------------------------------------
# Tests — total_count is every game; degenerate games count as analyzed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_total_count_is_all_games(user_a_client: tuple[int, str], test_engine) -> None:
    """total_count counts every imported game; degenerate games count as analyzed.

    Seed: 2 analyzed + 3 degenerate (full_evals SET, white_blunders NULL) +
    1 in-flight (all NULL). The degenerate games have full_evals_completed_at SET,
    so they count as analyzed (their cards show no "Analyze" button); the in-flight
    game is the only pending entry-ply eval.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    analyzed_count = 2
    degenerate_count = 3
    in_flight_count = 1
    games: list[Game] = (
        [_make_analyzed_engine_game(user_id) for _ in range(analyzed_count)]
        + [_make_unanalyzable_game(user_id) for _ in range(degenerate_count)]
        + [_make_unanalyzed_game(user_id) for _ in range(in_flight_count)]
    )
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    # Every game counts in the denominator.
    assert body["total_count"] == analyzed_count + degenerate_count + in_flight_count
    # Both the 2 analyzed and the 3 degenerate have full_evals_completed_at SET.
    assert body["analyzed_count"] == analyzed_count + degenerate_count
    # The in-flight game is the only pending entry-ply eval.
    assert body["pending_count"] == in_flight_count


@pytest.mark.asyncio
async def test_x_of_x_reachable_when_drain_done(
    user_a_client: tuple[int, str], test_engine
) -> None:
    """Once the drain finishes, analyzed_count == total_count (badge reaches X of X).

    With only analyzed + degenerate games (no in-flight work), every game has
    full_evals_completed_at SET, so analyzed_count == total_count, the badge reads
    "X of X", and pct_complete is 100.
    """
    user_id, token = user_a_client
    headers = {"Authorization": f"Bearer {token}"}

    analyzed_count = 4
    degenerate_count = 9  # matches the prod user-28 case
    total = analyzed_count + degenerate_count
    games: list[Game] = [_make_analyzed_engine_game(user_id) for _ in range(analyzed_count)] + [
        _make_unanalyzable_game(user_id) for _ in range(degenerate_count)
    ]
    await _seed_games_for_user(test_engine, user_id, games)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(EVAL_COVERAGE_ENDPOINT, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == total
    assert body["analyzed_count"] == total
    assert body["pending_count"] == 0
    assert body["pct_complete"] == 100
