"""Tests for app/services/eval_queue_service.py (260701-lw4: tier-4 ES lottery).

Covers:
- test_claim_tier4_blob_anti_starvation_and_recency_preference: inserts one very-old
  and one fresh analyzed game (same non-guest user, so Stage 1's user pick is
  deterministic) and monkeypatches TIER4_GAME_WEIGHT_FLOOR to a moderate value so the
  old game's Stage 2 weight collapses to (approximately) the floor while the fresh
  game's weight is dominated by its recency term. Over N draws, asserts both that the
  old game is picked at least once (anti-starvation — the core fix replacing the old
  top-50 window, which gave old games zero probability) and that the fresh game wins a
  strict majority (recency weighting still dominant).

Eval-lottery isolation (MEMORY: project_eval_lottery_test_isolation): every
non-guest Game + GameFlaw insert is wrapped in a finally-cleanup so global
tier-4 lottery rows don't leak into sibling tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Unique user ID range for this module — avoids FK conflicts with other test modules.
_TEST_USER_ID_TIER4: int = 99400

# Number of lottery draws in the anti-starvation + recency-preference test.
# With P(old) ≈ 0.1875 (see TEST_GAME_WEIGHT_FLOOR_MODERATE below), P(old never
# picked in N=40 draws) = (1 - 0.1875)^40 ≈ 4.4e-4 — well below the 1e-3 target,
# so "old picked >= 1" is statistically near-certain without being tautological.
N_DRAWS: int = 40

# Moderate TIER4_GAME_WEIGHT_FLOOR used only for this test (monkeypatched). With
# the old game aged far past TIER4_GAME_RECENCY_HALF_LIFE_DAYS (its exp() decay
# term ~0), its Stage-2 weight collapses to ~this floor while the fresh game's
# weight is ~1.0 (recency term) + this floor. That yields
# P(old) = floor / (floor + (1 + floor)) ≈ 0.3 / 1.6 ≈ 0.1875 — inside the
# plan's target 0.15-0.25 band (fresh keeps a clear >0.5 majority).
TEST_GAME_WEIGHT_FLOOR_MODERATE: float = 0.3

# Old game age: far beyond TIER4_GAME_RECENCY_HALF_LIFE_DAYS (30 days) so its
# recency term is negligible (~1e-4), leaving its Stage-2 weight ≈ the floor.
OLD_GAME_AGE_DAYS: int = 400


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
        user = result.unique().scalar_one_or_none()
        if user is None:
            session.add(
                User(
                    id=_TEST_USER_ID_TIER4,
                    email=f"tier4-test-{_TEST_USER_ID_TIER4}@example.com",
                    hashed_password="fakehash",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                    # Recent last_activity so Stage 1 (user pick) is not starved by its
                    # own floor — this is the only non-guest user this test relies on
                    # being eligible, so its Stage 1 weight just needs to be > 0.
                    last_activity=datetime.now(timezone.utc),
                )
            )
            await session.commit()
        else:
            # Refresh last_activity in case a prior test run left a stale value —
            # shared session-scoped row, not a new non-guest game, so no
            # per-test cleanup is required (mirrors the module docstring note).
            await session.execute(
                update(User)
                .where(User.id == _TEST_USER_ID_TIER4)
                .values(last_activity=datetime.now(timezone.utc))
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
async def test_claim_tier4_blob_anti_starvation_and_recency_preference(
    monkeypatch: pytest.MonkeyPatch,
    tier4_session_maker: async_sessionmaker[AsyncSession],
    tier4_test_user: int,
) -> None:
    """260701-lw4: _claim_tier4_blob's Stage-2 ES lottery favors fresh games without
    starving old ones.

    Both games belong to the same tier-4 test user, so Stage 1 (user pick) is
    deterministic — only one eligible user exists in this test's scope — and the
    fresh-vs-old contrast lives entirely in Stage 2 (game pick).

    TIER4_GAME_WEIGHT_FLOOR is monkeypatched to a moderate value
    (TEST_GAME_WEIGHT_FLOOR_MODERATE) and the old game is aged well past
    TIER4_GAME_RECENCY_HALF_LIFE_DAYS so its recency term is negligible and its
    weight collapses to ~the floor. This lands P(old) ≈ 0.1875 (see the module
    constant docstring above) — high enough that "old picked >= 1" over N_DRAWS
    draws is statistically near-certain (not a coin-flip-adjacent flaky assertion),
    while the fresh game still wins a clear majority.
    """
    import app.services.eval_queue_service as eval_queue_module
    from app.services.eval_queue_service import _claim_tier4_blob

    monkeypatch.setattr(
        eval_queue_module, "TIER4_GAME_WEIGHT_FLOOR", TEST_GAME_WEIGHT_FLOOR_MODERATE
    )

    now = datetime.now(timezone.utc)
    fresh_at = now
    old_at = now - timedelta(days=OLD_GAME_AGE_DAYS)

    user_id = tier4_test_user
    fresh_game_id = await _insert_analyzed_game_with_flaw(tier4_session_maker, user_id, fresh_at)
    old_game_id = await _insert_analyzed_game_with_flaw(tier4_session_maker, user_id, old_at)

    try:
        fresh_picks = 0
        old_picks = 0
        for i in range(N_DRAWS):
            async with tier4_session_maker() as session:
                result = await _claim_tier4_blob(session)
            assert result is not None, (
                f"_claim_tier4_blob returned None on draw {i}; both games are eligible"
            )
            picked_game_id = result[0]
            assert picked_game_id in (fresh_game_id, old_game_id), (
                f"Draw {i}: picked game {picked_game_id} is neither our fresh game "
                f"({fresh_game_id}) nor our old game ({old_game_id}) — Stage 1 (user "
                "pick) likely selected a different eligible non-guest user; check for "
                "leaked tier-4 lottery rows from a sibling test."
            )
            if picked_game_id == fresh_game_id:
                fresh_picks += 1
            else:
                old_picks += 1

        # Anti-starvation: the floor term must give the old game nonzero draw mass
        # (the core fix — the old top-50 window gave game #51+ probability zero).
        assert old_picks >= 1, (
            f"Old game {old_game_id} was never picked in {N_DRAWS} draws (fresh won "
            f"{fresh_picks}/{N_DRAWS}). TIER4_GAME_WEIGHT_FLOOR anti-starvation floor "
            "should give every pending-blob game nonzero draw probability."
        )
        # Recency preference: the fresh game must still win a strict majority.
        assert fresh_picks > N_DRAWS / 2, (
            f"Fresh game {fresh_game_id} won only {fresh_picks}/{N_DRAWS} draws (old won "
            f"{old_picks}). Recency weighting should keep freshly-analyzed games "
            "dominant despite the anti-starvation floor."
        )
    finally:
        await _delete_games_tier4(tier4_session_maker, [fresh_game_id, old_game_id])
