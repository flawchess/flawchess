"""Tests for app/services/eval_queue_service.py (Phase 146 D-01: recency-ordered tier-4 claim).

Covers:
- test_claim_tier4_blob_recency_favors_fresh_game: Monkeypatches TIER4_RECENCY_WINDOW=1
  so only the most-recently-analyzed game is in the CTE window. Asserts the fresh game
  (1 min ago) wins all draws when old game (1 hour ago) is also eligible.

Eval-lottery isolation (MEMORY: project_eval_lottery_test_isolation): every
non-guest Game + GameFlaw insert is wrapped in a finally-cleanup so global
tier-4 lottery rows don't leak into sibling tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Unique user ID range for this module — avoids FK conflicts with other test modules.
_TEST_USER_ID_TIER4: int = 99400


@pytest_asyncio.fixture(scope="session")
async def tier4_session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker bound to the per-run test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=False)
async def tier4_test_user(
    tier4_session_maker: async_sessionmaker[AsyncSession],
) -> int:
    """Ensure tier4 test user _TEST_USER_ID_TIER4 exists in the test DB. Returns user_id."""
    from app.models.user import User

    async with tier4_session_maker() as session:
        result = await session.execute(select(User).where(User.id == _TEST_USER_ID_TIER4))
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID_TIER4,
                    email=f"tier4-test-{_TEST_USER_ID_TIER4}@example.com",
                    hashed_password="fakehash",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )
            await session.commit()
    return _TEST_USER_ID_TIER4


async def _insert_analyzed_game_with_flaw(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    full_evals_completed_at: datetime,
) -> int:
    """Insert a Game (full_evals_completed_at set) + one GameFlaw (allowed_pv_lines NULL).

    Returns the game_id. The game matches the tier-4 predicate:
      - full_evals_completed_at IS NOT NULL
      - user is_guest = false
      - game_flaw.allowed_pv_lines IS NULL (not set — omit the column to get true SQL NULL;
        see MEMORY asyncpg_jsonb_null_vs_sql_null — passing Python None writes jsonb null,
        not SQL NULL, and would NOT match `allowed_pv_lines IS NULL`).
    """
    from app.models.game import Game
    from app.models.game_flaw import GameFlaw

    async with session_maker() as session:
        now_ts = datetime.now(timezone.utc)
        g = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=f"tier4-{uuid.uuid4().hex}",
            pgn="1. e4 e5 *",
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
            evals_completed_at=now_ts,
            full_evals_completed_at=full_evals_completed_at,
        )
        session.add(g)
        await session.flush()
        game_id = int(g.id)  # type: ignore[arg-type]

        flaw = GameFlaw(
            user_id=user_id,
            game_id=game_id,
            ply=2,
            severity=2,
            phase=0,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            # allowed_pv_lines intentionally omitted → SQL NULL, not jsonb null
        )
        session.add(flaw)
        await session.commit()
    return game_id


async def _delete_games_tier4(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
) -> None:
    """Delete games by ID (cascades to game_positions and game_flaws)."""
    from app.models.game import Game

    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_claim_tier4_blob_recency_favors_fresh_game(
    monkeypatch: pytest.MonkeyPatch,
    tier4_session_maker: async_sessionmaker[AsyncSession],
    tier4_test_user: int,
) -> None:
    """Phase 146 D-01: _claim_tier4_blob recency CTE favors recently-analyzed games.

    Monkeypatches TIER4_RECENCY_WINDOW to 1 so only the single most-recently-analyzed
    game is in the CTE. With two eligible games — one fresh (1 min ago) and one old
    (1 hour ago) — the fresh game must win every draw when the window is 1.

    RED (fails before Phase 146 code change): TIER4_RECENCY_WINDOW constant does not
    exist in eval_queue_service → monkeypatch.setattr raises AttributeError → test fails.
    GREEN (passes after change): constant exists, CTE uses :recency_window bound param,
    window=1 selects only the fresh game → 100% fresh-game picks.

    Eval-lottery isolation: both games are inserted before and deleted in a finally
    block so rows don't leak into the global tier-4 lottery state.
    """
    import app.services.eval_queue_service as eval_queue_module
    from app.services.eval_queue_service import _claim_tier4_blob

    # RED assertion: TIER4_RECENCY_WINDOW must exist (fails before Phase 146 adds it).
    monkeypatch.setattr(eval_queue_module, "TIER4_RECENCY_WINDOW", 1)

    now = datetime.now(timezone.utc)
    recent_at = now - timedelta(minutes=1)
    old_at = now - timedelta(hours=1)

    user_id = tier4_test_user
    recent_game_id = await _insert_analyzed_game_with_flaw(tier4_session_maker, user_id, recent_at)
    old_game_id = await _insert_analyzed_game_with_flaw(tier4_session_maker, user_id, old_at)

    try:
        # With TIER4_RECENCY_WINDOW=1, only the most-recently-analyzed game is in the
        # CTE (ORDER BY full_evals_completed_at DESC LIMIT 1). The fresh game (1 min ago)
        # always beats the old game (1 hour ago). Every draw must pick the fresh game.
        n_draws = 20
        for i in range(n_draws):
            async with tier4_session_maker() as session:
                result = await _claim_tier4_blob(session)
            assert result is not None, (
                f"_claim_tier4_blob returned None on draw {i}; both games are eligible"
            )
            picked_game_id = result[0]
            assert picked_game_id == recent_game_id, (
                f"Draw {i}: expected fresh game {recent_game_id} (1 min ago) to be picked "
                f"when TIER4_RECENCY_WINDOW=1, but got {picked_game_id} (old game is {old_game_id}). "
                "Phase 146 D-01: recency CTE must limit the pool to the top-N most-recent games."
            )
    finally:
        await _delete_games_tier4(tier4_session_maker, [recent_game_id, old_game_id])
