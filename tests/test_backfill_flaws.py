"""Backfill dry-run + batched-insert test for Phase 108 Plan 06.

Tests that run_backfill (from scripts/backfill_flaws.py):
  (a) dry_run=True writes zero game_flaws rows
  (b) A real run materializes the expected rows for an analyzed game
  (c) Re-running is idempotent (same row set, no PK duplicates)

Uses session-maker injection against the per-run test DB so run_backfill
never touches a real --db target. The game must have committed data (not
just a rollback-scoped db_session) since run_backfill opens its own sessions
internally via the injected session_maker.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.flaws_service import classify_game_flaws

# A real PGN that classify_game_flaws can replay for FEN computation.
# 10 half-moves = plies 0-9; ply 9 is the final position (no eval).
_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"

# These cp values produce known mover-POV ES drops for white:
#   eval_cp_to_expected_score(200, "white")  ≈ 0.685
#   eval_cp_to_expected_score(-500, "white") ≈ 0.160  → drop ≈ 0.525 (blunder)
#   eval_cp_to_expected_score(100, "white")  ≈ 0.591
#   eval_cp_to_expected_score(-50, "white")  ≈ 0.488  → drop ≈ 0.103 (mistake)
_CP_BLUNDER_BEFORE = 200
_CP_BLUNDER_AFTER = -500
_CP_MISTAKE_BEFORE = 100
_CP_MISTAKE_AFTER = -50

# Shared test user ID — unique enough to avoid FK conflicts with other test files
_TEST_USER_ID = 108060


# ---------------------------------------------------------------------------
# Fixtures: committed data (run_backfill opens its own sessions internally)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory(test_engine) -> async_sessionmaker[AsyncSession]:  # type: ignore[type-arg]
    """Return an async_sessionmaker bound to the per-run test DB."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def committed_analyzed_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[tuple[Game, int, int], None]:
    """Seed a committed user, game, and analyzed positions into the test DB.

    Committed (not rollback-scoped) so run_backfill's internal sessions can
    see the data. Yields (game, blunder_ply, mistake_ply).
    Teardown: deletes the game and user (cascade removes positions + flaws).
    """
    user_id = _TEST_USER_ID
    async with session_factory() as session:
        # Ensure user exists
        existing = (
            (await session.execute(select(User).where(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(id=user_id, email=f"test-backfill-{user_id}@example.com", hashed_password="x")
            )
            await session.flush()

        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/bf-test",
            pgn=_PGN,
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            base_time_seconds=600,
            increment_seconds=0.0,
            rated=True,
            is_computer_game=False,
        )
        session.add(game)
        await session.flush()
        game_id = game.id

        # Seed 10 positions (plies 0-9); ply 9 has no eval (coverage = 9/10 = 0.90).
        # Blunder at white's ply 2, mistake at white's ply 4.
        cp_values = [20] * 10
        cp_values[1] = _CP_BLUNDER_BEFORE  # baseline before ply 2
        cp_values[2] = _CP_BLUNDER_AFTER  # blunder at ply 2
        cp_values[3] = _CP_MISTAKE_BEFORE  # baseline before ply 4
        cp_values[4] = _CP_MISTAKE_AFTER  # mistake at ply 4

        for ply in range(10):
            eval_cp = cp_values[ply] if ply < 9 else None  # final ply: no eval
            pos = GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                eval_cp=eval_cp,
                eval_mate=None,
                clock_seconds=None,
                phase=1,  # middlegame
                full_hash=ply,
                white_hash=ply,
                black_hash=ply,
                material_count=1000,
                material_signature="KP_KP",
                material_imbalance=0,
                has_opposite_color_bishops=False,
                piece_count=20,
                backrank_sparse=False,
                mixedness=100,
                endgame_class=None,
                move_san=None,
            )
            session.add(pos)

        await session.commit()

    yield game, 2, 4

    # Teardown: delete committed data to avoid test pollution
    async with session_factory() as session:
        await session.execute(delete(Game).where(Game.id == game_id))
        await session.commit()


# ---------------------------------------------------------------------------
# Verify the test game produces flaws (sanity guard)
# ---------------------------------------------------------------------------


class TestBackfillFlawsFixture:
    """Sanity check that the committed_analyzed_game fixture yields analyzable data."""

    @pytest.mark.asyncio
    async def test_fixture_game_is_analyzable(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_analyzed_game: tuple[Game, int, int],
    ) -> None:
        """The seeded game should produce at least 1 flaw from classify_game_flaws."""
        game, blunder_ply, mistake_ply = committed_analyzed_game
        async with session_factory() as session:
            from app.repositories.flaws_repository import fetch_game_positions_ordered

            positions = await fetch_game_positions_ordered(
                session, game_id=game.id, user_id=game.user_id
            )
            result = classify_game_flaws(game, positions)
        assert isinstance(result, list), "Expected analyzed game (list[FlawRecord])"
        assert len(result) >= 1, "Expected at least one flaw"


# ---------------------------------------------------------------------------
# TestBackfillDryRun
# ---------------------------------------------------------------------------


class TestBackfillDryRun:
    """run_backfill with dry_run=True writes zero game_flaws rows."""

    @pytest.mark.asyncio
    async def test_dry_run_writes_no_rows(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_analyzed_game: tuple[Game, int, int],
    ) -> None:
        """Dry-run must not insert any game_flaws rows into the DB."""
        from scripts.backfill_flaws import run_backfill

        game, _blunder_ply, _mistake_ply = committed_analyzed_game

        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=True,
            limit=None,
            session_maker=session_factory,
        )

        async with session_factory() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(GameFlaw)
                    .where(
                        GameFlaw.game_id == game.id,
                        GameFlaw.user_id == game.user_id,
                    )
                )
            ).scalar_one()

        assert count == 0, f"Expected 0 rows after dry-run, got {count}"

    @pytest.mark.asyncio
    async def test_dry_run_on_empty_user_does_nothing(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Dry-run on a user with no games returns without error."""
        from scripts.backfill_flaws import run_backfill

        # User ID that does not exist in DB — run_backfill must handle gracefully
        await run_backfill(
            db="dev",
            user_id=999_888_777,
            dry_run=True,
            limit=None,
            session_maker=session_factory,
        )
        # No exception = pass


# ---------------------------------------------------------------------------
# TestBackfillRealRun
# ---------------------------------------------------------------------------


class TestBackfillRealRun:
    """run_backfill (real) populates game_flaws and re-running is idempotent."""

    @pytest.mark.asyncio
    async def test_real_run_materializes_expected_rows(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_analyzed_game: tuple[Game, int, int],
    ) -> None:
        """A real run materializes the M+B rows expected by classify_game_flaws."""
        from scripts.backfill_flaws import run_backfill
        from app.repositories.flaws_repository import fetch_game_positions_ordered

        game, _blunder_ply, _mistake_ply = committed_analyzed_game

        # Get ground truth from classifier
        async with session_factory() as session:
            positions = await fetch_game_positions_ordered(
                session, game_id=game.id, user_id=game.user_id
            )
        expected = classify_game_flaws(game, positions)
        assert isinstance(expected, list), "Expected analyzed game"
        assert len(expected) >= 1, "Test game must have at least 1 flaw"

        # Run the backfill
        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=False,
            limit=None,
            session_maker=session_factory,
        )

        # Verify the materialized rows
        async with session_factory() as session:
            result = await session.execute(
                select(GameFlaw).where(
                    GameFlaw.game_id == game.id,
                    GameFlaw.user_id == game.user_id,
                )
            )
            stored = result.scalars().all()

        assert len(stored) == len(expected), (
            f"Expected {len(expected)} rows (M+B only), got {len(stored)}"
        )

        # (ply, severity_int) set matches exactly
        expected_pairs = {(r["ply"], 1 if r["severity"] == "mistake" else 2) for r in expected}
        stored_pairs = {(row.ply, row.severity) for row in stored}
        assert expected_pairs == stored_pairs, (
            f"Materialized rows differ from classifier: "
            f"expected={expected_pairs}, got={stored_pairs}"
        )

    @pytest.mark.asyncio
    async def test_rerun_is_idempotent(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_analyzed_game: tuple[Game, int, int],
    ) -> None:
        """Re-running run_backfill produces the same row set, no PK duplicates."""
        from scripts.backfill_flaws import run_backfill

        game, _blunder_ply, _mistake_ply = committed_analyzed_game

        # First run
        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=False,
            limit=None,
            session_maker=session_factory,
        )

        async with session_factory() as session:
            count_after_first = (
                await session.execute(
                    select(func.count())
                    .select_from(GameFlaw)
                    .where(
                        GameFlaw.game_id == game.id,
                        GameFlaw.user_id == game.user_id,
                    )
                )
            ).scalar_one()

        # Second run
        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=False,
            limit=None,
            session_maker=session_factory,
        )

        async with session_factory() as session:
            count_after_second = (
                await session.execute(
                    select(func.count())
                    .select_from(GameFlaw)
                    .where(
                        GameFlaw.game_id == game.id,
                        GameFlaw.user_id == game.user_id,
                    )
                )
            ).scalar_one()

        assert count_after_first > 0, "Expected rows after first run"
        assert count_after_first == count_after_second, (
            f"Re-run not idempotent: first={count_after_first}, second={count_after_second}"
        )
