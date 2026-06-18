"""Backfill dry-run + batched-insert test for Phase 108 Plan 06.

Tests that run_backfill (from scripts/backfill_flaws.py):
  (a) dry_run=True writes zero game_flaws rows
  (b) A real run materializes the expected rows for an analyzed game
  (c) Re-running is idempotent (same row set, no PK duplicates)

Phase 125 Plan 01 adds TestBackfillTacticColumns (Nyquist Wave 0):
  (d) After run_backfill, the blunder row has tactic_motif IS NOT NULL when a
      PV is present at flaw_ply+1 and the detector fires (PV-fires path).
  (e) The no-PV control (existing committed_analyzed_game fixture) produces
      tactic_motif IS NULL for all rows (no-PV NULL bucket = honest).

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
from app.services.tactic_detector import TACTIC_CONFIDENCE_HIGH, TacticMotifInt

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
# Phase 125 tactic-column test constants
# ---------------------------------------------------------------------------

# Separate user ID for the tactic test so its committed data never interferes
# with the Phase 108 fixture.
_TACTIC_TEST_USER_ID = 125010

# FEN-header PGN for the tactic fixture:
#   - White king on e3, black rook on e2.
#   - ply 0 (white, even): Kf4 — white king moves to f4.
#   - ply 1 (black, odd): Re4?? — black rook moves to e4 (hanging piece BLUNDER).
# FEN at ply 0 (fen_map[0]): 8/6p1/5k2/2p5/8/P1P1K3/1P2r3/8
# FEN at ply 1 (fen_map[1], fen_before_flaw): 8/6p1/5k2/2p5/5K2/P1P5/1P2r3/8
# FEN at ply 2 (fen_after_flaw): 8/6p1/5k2/2p5/4rK2/P1P5/1P6/8
# White king captures on e4 = refutation confirming hanging-piece (D-09 prod fixture).
_TACTIC_PGN = '[FEN "8/6p1/5k2/2p5/8/P1P1K3/1P2r3/8 w - - 0 1"]\n\n1. Kf4 Re4 *'

# Blunder ply for the tactic game (black's Re4?? is at ply 1).
_TACTIC_BLUNDER_PLY = 1

# eval_cp values for the tactic game:
#   positions[0]: black winning (−500) → es_before_for_black ≈ 0.86
#   positions[1]: white winning (+200) → es_after_for_black  ≈ 0.32
#   drop ≈ 0.54 ≥ BLUNDER_DROP (0.15) — classifies as blunder ✓
#   positions[2]: None (final position, no eval).
_TACTIC_CP_BEFORE_BLUNDER = -500  # eval at positions[0], black winning
_TACTIC_CP_AFTER_BLUNDER = 200  # eval at positions[1], white winning after Re4??

# Refutation PV at flaw_ply+1 = positions[2].pv:
# Kxe4 captures the hanging rook.  This PV is a D-09 prod-confirmed fixture
# from tests/services/test_tactic_detector.py (_HANGING_PIECE_FIXTURES entry 3):
#   FEN after Re4??: 8/6p1/5k2/2p5/4rK2/P1P5/1P6/8 w - - 0 2
#   PV: f4e4 f6e6 c3c4 ... → hanging-piece fires (motif=2, confidence=100).
_TACTIC_REFUTATION_PV = "f4e4 f6e6 c3c4 e6f6 b2b3 f6e6 e4f4 e6f6 a3a4 f6e6 f4g5 e6e5"


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


# ---------------------------------------------------------------------------
# Phase 125 Plan 01: TestBackfillTacticColumns (Nyquist Wave 0 gap closure)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def committed_tactic_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[tuple[Game, int], None]:
    """Seed a committed game with a hanging-piece blunder PV for tactic detection.

    The fixture creates:
    - A 3-position game (plies 0-2) whose PGN starts from a custom FEN.
    - positions[0].move_san = 'Kf4' (white's move, ply 0).
    - positions[1].move_san = 'Re4' (black's blunder, ply 1 = _TACTIC_BLUNDER_PLY).
    - positions[2].pv = _TACTIC_REFUTATION_PV (the refutation at flaw_ply+1).
    - eval_cp triggers a blunder at ply 1 from black's perspective.

    run_backfill with this game must produce a GameFlaw row at ply 1 with
    tactic_motif IS NOT NULL (hanging-piece detector fires on the PV).

    Yields (game, blunder_ply). Teardown: deletes committed data.
    """
    user_id = _TACTIC_TEST_USER_ID
    async with session_factory() as session:
        existing = (
            (await session.execute(select(User).where(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=user_id,
                    email=f"test-backfill-tactic-{user_id}@example.com",
                    hashed_password="x",
                )
            )
            await session.flush()

        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/tactic-test",
            pgn=_TACTIC_PGN,
            result="0-1",
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

        # 3 positions: plies 0-2.
        # Ply 2 is the final position (no move_san, no eval, but carries the PV
        # that the tactic detector reads as positions[blunder_ply + 1].pv).
        cp_values: list[int | None] = [
            _TACTIC_CP_BEFORE_BLUNDER,  # ply 0: before white's Kf4, black winning
            _TACTIC_CP_AFTER_BLUNDER,  # ply 1: after black's Re4??, white winning
            None,  # ply 2: final position, no eval
        ]
        move_sans: list[str | None] = [
            "Kf4",  # ply 0: white's move
            "Re4",  # ply 1: black's blunder (flaw move)
            None,  # ply 2: final position (no move played from here)
        ]
        pvs: list[str | None] = [
            None,  # ply 0: no PV
            None,  # ply 1: no PV (PV is at flaw_ply+1 = ply 2)
            _TACTIC_REFUTATION_PV,  # ply 2: PV at flaw_ply+1, consumed by detector
        ]

        for ply in range(3):
            pos = GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                eval_cp=cp_values[ply],
                eval_mate=None,
                clock_seconds=None,
                phase=1,  # middlegame
                full_hash=ply + 1000,  # offset from Phase 108 fixture to avoid collisions
                white_hash=ply + 1000,
                black_hash=ply + 1000,
                material_count=200,
                material_signature="K_KR",
                material_imbalance=-5,
                has_opposite_color_bishops=False,
                piece_count=4,
                backrank_sparse=True,
                mixedness=10,
                endgame_class=1,  # rook endgame
                move_san=move_sans[ply],
                pv=pvs[ply],
            )
            session.add(pos)

        await session.commit()

    yield game, _TACTIC_BLUNDER_PLY

    # Teardown: delete committed data to avoid test pollution.
    async with session_factory() as session:
        await session.execute(delete(Game).where(Game.id == game_id))
        await session.commit()


class TestBackfillTacticColumns:
    """Phase 125 Nyquist Wave 0: verify tactic columns are written by run_backfill.

    Two paths:
    - PV-fires path (Test B): a game seeded with positions[blunder_ply+1].pv AND
      move_san at blunder_ply produces a GameFlaw row with tactic_motif IS NOT NULL.
    - No-PV NULL path (Test A): the existing committed_analyzed_game fixture
      (move_san=None, no pv) produces tactic_motif IS NULL for all rows.
    """

    @pytest.mark.asyncio
    async def test_tactic_motif_is_null_when_no_pv(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_analyzed_game: tuple[Game, int, int],
    ) -> None:
        """No-PV NULL bucket: no pv seeded → every GameFlaw row has tactic_motif IS NULL.

        The existing committed_analyzed_game fixture has move_san=None and pv=None on
        all positions. The _detect_tactic_for_flaw guard (pv is None → short-circuit)
        must leave tactic_motif, tactic_piece, and tactic_confidence all NULL.
        This confirms the no-PV NULL bucket is honest, not an error.
        """
        from scripts.backfill_flaws import run_backfill

        game, _blunder_ply, _mistake_ply = committed_analyzed_game

        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=False,
            limit=None,
            session_maker=session_factory,
        )

        async with session_factory() as session:
            result = await session.execute(
                select(GameFlaw).where(
                    GameFlaw.game_id == game.id,
                    GameFlaw.user_id == game.user_id,
                )
            )
            stored = result.scalars().all()

        assert len(stored) >= 1, "Expected at least one flaw row"
        for row in stored:
            assert row.tactic_motif is None, (
                f"Expected tactic_motif IS NULL (no pv), got {row.tactic_motif} at ply {row.ply}"
            )
            assert row.tactic_piece is None, (
                f"Expected tactic_piece IS NULL (no pv), got {row.tactic_piece} at ply {row.ply}"
            )
            assert row.tactic_confidence is None, (
                f"Expected tactic_confidence IS NULL (no pv), got {row.tactic_confidence} at ply {row.ply}"
            )

    @pytest.mark.asyncio
    async def test_tactic_motif_is_not_null_when_pv_fires(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        committed_tactic_game: tuple[Game, int],
    ) -> None:
        """PV-fires path: pv + move_san seeded → blunder row has tactic_motif IS NOT NULL.

        The committed_tactic_game fixture seeds a hanging-piece blunder at ply 1:
        black plays Re4?? (rook to e4, hanging to white's king on f4).
        positions[2].pv = the D-09 prod-confirmed refutation PV (f4e4 ...).
        After run_backfill, the GameFlaw at ply 1 must carry a non-NULL tactic_motif
        and tactic_confidence, confirming the detect path was exercised.

        The control: flaw rows at other plies (if any) keep tactic_motif NULL if
        their pv is absent, which preserves the honest NULL semantics.
        """
        from scripts.backfill_flaws import run_backfill

        game, blunder_ply = committed_tactic_game

        await run_backfill(
            db="dev",
            user_id=game.user_id,
            dry_run=False,
            limit=None,
            session_maker=session_factory,
        )

        async with session_factory() as session:
            result = await session.execute(
                select(GameFlaw).where(
                    GameFlaw.game_id == game.id,
                    GameFlaw.user_id == game.user_id,
                )
            )
            stored = result.scalars().all()

        assert len(stored) >= 1, "Expected at least one flaw row (blunder at ply 1)"

        # Find the blunder row at the tactic blunder ply.
        blunder_rows = [r for r in stored if r.ply == blunder_ply]
        assert len(blunder_rows) == 1, (
            f"Expected exactly one flaw row at ply {blunder_ply}, "
            f"got {len(blunder_rows)}. All rows: {[(r.ply, r.severity) for r in stored]}"
        )
        blunder_row = blunder_rows[0]

        # Strong assertion (WR-01): pin the exact motif + confidence the known
        # hanging-piece fixture must produce, so a detector regression that fires
        # the WRONG motif fails loudly instead of passing on a bare not-None check.
        assert blunder_row.tactic_motif == TacticMotifInt.HANGING_PIECE, (
            f"Expected tactic_motif == HANGING_PIECE ({TacticMotifInt.HANGING_PIECE}) "
            f"at ply {blunder_ply} (PV-fires path), got {blunder_row.tactic_motif}. "
            f"Verify positions[{blunder_ply + 1}].pv and move_san at ply {blunder_ply}."
        )
        assert blunder_row.tactic_confidence == TACTIC_CONFIDENCE_HIGH, (
            f"Expected tactic_confidence == {TACTIC_CONFIDENCE_HIGH} at ply "
            f"{blunder_ply}, got {blunder_row.tactic_confidence}."
        )
