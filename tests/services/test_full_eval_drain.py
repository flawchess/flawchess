"""Integration tests for run_full_eval_drain (Phase 116 EVAL-01/03/05/QUEUE-07,
Phase 117 EVAL-04/EVAL-06/D-117-07/QUEUE-03).

Tests cover:
- EVAL-01: all non-terminal plies collected; terminal position excluded
- EVAL-01: PGN parse failure returns empty list
- EVAL-03: dedup returns hit for known parity hash (full_evals_completed_at gated)
- EVAL-03: dedup ignores depth-15 source (no full_evals_completed_at marker)
- EVAL-04: best_move populated on every evaluated non-dedup'd ply after drain tick
- EVAL-04: dedup_best_move transplanted via dedup for opening-region plies (D-117-01)
- EVAL-04: flaw_pv written ONLY at ply N+1 for FlawRecord at ply N (D-117-02)
- EVAL-05: full_evals_completed_at set after drain tick
- EVAL-05: marker set even when engine returns (None, None) holes
- EVAL-06: classify_hook — game_flaws rows exist after full eval completes
- EVAL-06: oracle_counts — white/black oracle columns filled and match game_flaws
- D-117-07: wr02_repointed — lichess_evals_at gates dedup source, not white_blunders
- QUEUE-03: gather_outside_session — asyncio.gather NOT inside an AsyncSession scope (AST scan)
- QUEUE-07: yield gate is True when an active ImportJob exists
- QUEUE-07: yield gate is True when a game has evals_completed_at IS NULL

Session patching mirrors test_eval_drain.py: monkeypatch
app.services.eval_drain.async_session_maker to route drain sessions to the
test DB. Engine calls are monkeypatched for all drain-logic tests; no real
Stockfish required.
"""

from __future__ import annotations

import ast
import inspect
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import chess
import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ─── Module-level test constants ──────────────────────────────────────────────

_TEST_USER_ID: int = 99200  # unique to this module to avoid FK conflicts
_TEST_USER_ID_117: int = 99201  # separate range for Phase 117 tests to avoid FK conflicts
# A short PGN ending in checkmate (Scholar's mate in 4 moves = 8 half-moves).
# The final position IS checkmate; the iterator should never visit it.
_CHECKMATE_PGN: str = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6?? 4. Qxf7# 1-0"
# A simple non-terminal PGN used for general tests.
_SIMPLE_PGN: str = "1. e4 e5 2. Nf3 Nc6 3. Bc4 *"
# A minimal PGN with only 2 moves (4 half-moves).
_TWO_MOVE_PGN: str = "1. e4 e5 *"
# A 6-half-move PGN (3 moves each, 6 non-terminal positions).
# Used for oracle/classify/flaw-PV tests where coverage >= 90% is required and
# we need enough plies for the blunder-eval-sequence (plies 0..5).
_SIX_PLY_PGN: str = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *"


# ─── Session-scoped fixtures ──────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def full_drain_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker bound to the test engine.

    Used to:
    1. Insert committed test data visible across sessions.
    2. Patch app.services.eval_drain.async_session_maker.
    """
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=False)
async def full_drain_test_user(
    full_drain_session_maker: async_sessionmaker[AsyncSession],
) -> int:
    """Ensure test user _TEST_USER_ID exists in the test DB (committed). Returns user_id."""
    from app.models.user import User

    async with full_drain_session_maker() as session:
        result = await session.execute(select(User).where(User.id == _TEST_USER_ID))
        # .unique() required: User → OAuthAccount lazy="joined" collection load.
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"full-drain-test-{_TEST_USER_ID}@example.com",
                    hashed_password="fakehash",
                )
            )
            await session.commit()
    return _TEST_USER_ID


@pytest_asyncio.fixture(scope="session", autouse=False)
async def full_drain_test_user_117(
    full_drain_session_maker: async_sessionmaker[AsyncSession],
) -> int:
    """Ensure test user _TEST_USER_ID_117 exists in the test DB. Returns user_id."""
    from app.models.user import User

    async with full_drain_session_maker() as session:
        result = await session.execute(select(User).where(User.id == _TEST_USER_ID_117))
        # User → OAuthAccount is lazy="joined" (a collection eager-load), so the
        # entity result must be de-duplicated with .unique() before scalar access.
        # Without it, SQLAlchemy raises once cross-file mapper configuration emits
        # the joined collection load (errors only when run alongside other suites).
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID_117,
                    email=f"full-drain-test-{_TEST_USER_ID_117}@example.com",
                    hashed_password="fakehash",
                )
            )
            await session.commit()
    return _TEST_USER_ID_117


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def _insert_game(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    pgn: str = _SIMPLE_PGN,
    *,
    evals_completed_at: datetime | None = None,
    full_evals_completed_at: datetime | None = None,
    white_blunders: int | None = None,
    lichess_evals_at: datetime | None = None,
) -> int:
    """Insert a Game row and commit. Returns the game_id."""
    from app.models.game import Game

    async with session_maker() as session:
        g = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=f"full-drain-{uuid.uuid4().hex}",
            pgn=pgn,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
            evals_completed_at=evals_completed_at,
            full_evals_completed_at=full_evals_completed_at,
            white_blunders=white_blunders,
            lichess_evals_at=lichess_evals_at,
        )
        session.add(g)
        await session.flush()
        game_id = g.id
        await session.commit()
    return game_id


async def _insert_game_positions(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    game_id: int,
    rows: list[dict[str, Any]],
) -> None:
    """Insert GamePosition rows for a game and commit.

    Each dict in rows: {"ply": int, "full_hash": int, "eval_cp": int|None,
    "eval_mate": int|None, "best_move": str|None (optional), "pv": str|None (optional),
    "move_san": str|None (optional)}.
    """
    from app.models.game_position import GamePosition

    async with session_maker() as session:
        for r in rows:
            session.add(
                GamePosition(
                    user_id=user_id,
                    game_id=game_id,
                    ply=r["ply"],
                    full_hash=r["full_hash"],
                    white_hash=0,
                    black_hash=0,
                    move_san=r.get("move_san"),
                    phase=0,
                    endgame_class=None,
                    eval_cp=r.get("eval_cp"),
                    eval_mate=r.get("eval_mate"),
                    best_move=r.get("best_move"),
                    pv=r.get("pv"),
                )
            )
        await session.commit()


async def _delete_games(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
) -> None:
    """Delete games by ID (committed cleanup)."""
    from app.models.game import Game

    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


async def _delete_import_jobs(
    session_maker: async_sessionmaker[AsyncSession],
    job_ids: list[str],
) -> None:
    """Delete ImportJob rows by ID (committed cleanup)."""
    from app.models.import_job import ImportJob

    if not job_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(ImportJob).where(ImportJob.id.in_(job_ids)))
        await session.commit()


# ─── EVAL-01: all-ply collector ───────────────────────────────────────────────


class TestCollectAllPliesExcludesTerminal:
    """EVAL-01: _collect_full_ply_targets yields one target per non-terminal ply."""

    def test_collect_all_plies_excludes_terminal(self) -> None:
        """A checkmate PGN: targets == number of half-moves played (terminal excluded).

        Scholar's mate: 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6?? 4.Qxf7# = 7 half-moves
        (plies 0..6). The mainline iterator yields the board BEFORE each move is
        pushed, so it yields 7 nodes (plies 0..6). The post-4.Qxf7# board is
        checkmate — never yielded, never added to targets.
        """
        from app.services.eval_drain import _collect_full_ply_targets

        pgn = _CHECKMATE_PGN
        # Provide game_positions_rows for plies 0..6 (7 half-moves).
        expected_ply_count = 7  # plies 0..6; ply 7 is the terminal checkmate position
        gp_rows = [(ply, ply + 1000, None, None) for ply in range(expected_ply_count)]

        targets = _collect_full_ply_targets(game_id=1, pgn_text=pgn, game_positions_rows=gp_rows)

        # Must have exactly 7 targets (plies 0..6); the terminal board is never visited.
        assert len(targets) == expected_ply_count, (
            f"Expected {expected_ply_count} non-terminal targets, got {len(targets)}. "
            "Terminal (checkmate) position must be excluded — EVAL-01."
        )
        plies_collected = [t.ply for t in targets]
        assert plies_collected == list(range(expected_ply_count)), (
            f"Expected plies [0..{expected_ply_count - 1}], got {plies_collected}"
        )
        # Each board snapshot must be a valid chess.Board (not game-over).
        for t in targets:
            assert isinstance(t.board, chess.Board), f"Target at ply {t.ply} has no board"
            assert not t.board.is_game_over(), (
                f"Board at ply {t.ply} is game-over — terminal position was incorrectly included"
            )

    def test_collect_handles_bad_pgn(self) -> None:
        """Malformed PGN returns empty list (no exception)."""
        from app.services.eval_drain import _collect_full_ply_targets

        gp_rows = [(0, 12345, None, None)]
        targets = _collect_full_ply_targets(
            game_id=1, pgn_text="THIS IS NOT VALID PGN !!!", game_positions_rows=gp_rows
        )
        assert targets == [], "Malformed PGN must return [] without raising"

    def test_collect_handles_none_pgn_result(self) -> None:
        """Empty PGN (chess.pgn.read_game returns None) returns empty list."""
        from app.services.eval_drain import _collect_full_ply_targets

        gp_rows = [(0, 12345, None, None)]
        targets = _collect_full_ply_targets(game_id=1, pgn_text="", game_positions_rows=gp_rows)
        assert targets == [], "Empty PGN (None game) must return []"

    def test_collect_missing_gp_rows_skipped(self) -> None:
        """Plies not in game_positions_rows are silently skipped."""
        from app.services.eval_drain import _collect_full_ply_targets

        # Only provide a row for ply 2 — plies 0, 1, 3 skipped.
        gp_rows = [(2, 99999, None, None)]
        targets = _collect_full_ply_targets(
            game_id=1, pgn_text=_SIMPLE_PGN, game_positions_rows=gp_rows
        )
        assert len(targets) == 1
        assert targets[0].ply == 2


# ─── EVAL-03: dedup lookup ────────────────────────────────────────────────────


class TestDedupHitsParity:
    """EVAL-03: dedup returns parity eval only when source game has full_evals_completed_at set."""

    async def test_dedup_hits_parity_source(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """SEED-044 post-move self-join: a position's OWN eval is recovered from the
        PRIOR row's post-move eval, and its best_move from the position's own row.

        Donor game (full_evals_completed_at set):
          ply 4: eval_cp=42  -> post-move eval of ply 4 = eval of the position REACHED = ply 5's position
          ply 5: full_hash=Q, best_move="g1f3" -> best move FROM Q (decision-keyed)
        So _fetch_dedup_evals([Q]) recovers (eval OF Q=42, None, best_move FROM Q="g1f3").
        """
        from app.services.eval_drain import _DEDUP_MAX_PLY, _fetch_dedup_evals

        # Insert a parity-source game (full_evals_completed_at set).
        now = datetime.now(timezone.utc)
        source_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            full_evals_completed_at=now,
            evals_completed_at=now,
        )
        # A unique hash to avoid collisions with other test data.
        target_hash = 0xDEAD_BEEF_0001
        predecessor_hash = 0xDEAD_BEEF_00FF
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            source_game_id,
            [
                # cur (ply 4): post-move eval = eval of the position reached (Q at ply 5).
                {"ply": 4, "full_hash": predecessor_hash, "eval_cp": 42, "eval_mate": None},
                # nxt (ply 5): the requested position Q; carries best_move FROM Q.
                {
                    "ply": 5,
                    "full_hash": target_hash,
                    "eval_cp": 99,
                    "eval_mate": None,
                    "best_move": "g1f3",
                },
            ],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash in result, (
                f"Parity source (full_evals_completed_at set, ply {5} <= {_DEDUP_MAX_PLY}) "
                "must be recovered by the post-move self-join (EVAL-03 / SEED-044)."
            )
            # (eval OF Q from prior row, eval_mate, best_move FROM Q from Q's own row).
            assert result[target_hash] == (42, None, "g1f3")
        finally:
            await _delete_games(full_drain_session_maker, [source_game_id])

    async def test_dedup_excludes_depth15_source(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A game_position row at ply<=20 whose game has only evals_completed_at (no full marker)
        must NOT be returned by _fetch_dedup_evals (Pitfall 4, D-116-02)."""
        from app.services.eval_drain import _fetch_dedup_evals

        # Insert a depth-15 source game (evals_completed_at set, full_evals_completed_at NULL).
        now = datetime.now(timezone.utc)
        depth15_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )
        target_hash = 0xDEAD_BEEF_0002
        # Insert the predecessor too, so the self-join WOULD match if not for the
        # full_evals_completed_at gate (SEED-044 — the gate is what must exclude it).
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            depth15_game_id,
            [
                {"ply": 4, "full_hash": 0xDEAD_BEEF_02FF, "eval_cp": 100, "eval_mate": None},
                {"ply": 5, "full_hash": target_hash, "eval_cp": 80, "eval_mate": None},
            ],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash not in result, (
                "Depth-15 source (full_evals_completed_at IS NULL) must NOT be returned "
                "by _fetch_dedup_evals — Pitfall 4 / D-116-02."
            )
        finally:
            await _delete_games(full_drain_session_maker, [depth15_game_id])

    async def test_dedup_excludes_analyzed_source(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """A lichess-analyzed game (lichess_evals_at IS NOT NULL) must NOT be a dedup
        source (WR-02 repointed to D-117-07): its preserved rows are lichess post-move
        evals, which are not position-keyed by full_hash — only engine-written rows
        (lichess_evals_at IS NULL) are safe to transplant.

        D-117-07: the WR-02 gate was repointed from white_blunders IS NULL onto
        lichess_evals_at IS NULL. After oracle counts are filled for engine games,
        white_blunders IS NOT NULL for engine games too — using white_blunders would
        wrongly exclude engine-written sources.
        """
        from app.services.eval_drain import _fetch_dedup_evals

        now = datetime.now(timezone.utc)
        analyzed_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=now,
            full_evals_completed_at=now,
            lichess_evals_at=now,  # D-117-07: this is what marks a lichess-analyzed source
        )
        target_hash = 0xDEAD_BEEF_0003
        # Insert the predecessor too, so the self-join WOULD match if not for the
        # lichess_evals_at gate (SEED-044 — the gate is what must exclude it).
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            analyzed_game_id,
            [
                {"ply": 4, "full_hash": 0xDEAD_BEEF_03FF, "eval_cp": 77, "eval_mate": None},
                {"ply": 5, "full_hash": target_hash, "eval_cp": 70, "eval_mate": None},
            ],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash not in result, (
                "lichess-analyzed source (lichess_evals_at IS NOT NULL) must NOT be "
                "returned by _fetch_dedup_evals — lichess post-move evals are not "
                "position-keyed by full_hash (WR-02, D-117-07 repoint)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [analyzed_game_id])

    async def test_dedup_empty_input_returns_empty(
        self,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Empty hash list returns empty dict without querying the DB."""
        from app.services.eval_drain import _fetch_dedup_evals

        async with full_drain_session_maker() as session:
            result = await _fetch_dedup_evals(session, [])

        assert result == {}


# ─── EVAL-05: marker write ────────────────────────────────────────────────────


def _patch_drain_for_tick_tests(
    monkeypatch: pytest.MonkeyPatch,
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    user_id: int,
    *,
    is_analyzed: bool = False,
    tier: int = 3,
    job_id: int | None = None,
) -> Any:
    """Shared monkeypatching for direct _full_drain_tick tests (WR-07).

    Routes drain sessions to the test DB, suppresses Sentry, forces the
    yield gate to False, and mocks claim_eval_job to return a deterministic
    ClaimedJob for the given game_id/user_id.

    Phase 117: _full_drain_tick now calls claim_eval_job (which uses
    eval_queue_service.async_session_maker internally). We mock claim_eval_job
    directly in the drain module namespace so it doesn't open any sessions.

    Returns the drain module.
    """
    import app.services.eval_drain as drain_module
    from app.services.eval_queue_service import ClaimedJob

    monkeypatch.setattr(drain_module, "async_session_maker", session_maker)
    monkeypatch.setattr(drain_module.sentry_sdk, "capture_exception", lambda *a, **kw: None)
    monkeypatch.setattr(drain_module.sentry_sdk, "capture_message", lambda *a, **kw: None)
    monkeypatch.setattr(drain_module.sentry_sdk, "set_tag", lambda *a, **kw: None)
    monkeypatch.setattr(drain_module.sentry_sdk, "set_context", lambda *a, **kw: None)
    monkeypatch.setattr(
        drain_module,
        "_any_active_import_or_entry_ply_pending",
        AsyncMock(return_value=False),
    )
    # Mock claim_eval_job to return a ClaimedJob for the seeded game without
    # opening a DB session (avoids dependency on eval_queue_service sessions).
    claimed = ClaimedJob(
        game_id=game_id,
        user_id=user_id,
        tier=tier,
        is_analyzed=is_analyzed,
        job_id=job_id,
    )
    monkeypatch.setattr(drain_module, "claim_eval_job", AsyncMock(return_value=claimed))
    return drain_module


class TestMarkerWrite:
    """EVAL-05: full_evals_completed_at is set after a drain tick.

    WR-07: tests call _full_drain_tick() directly — deterministic, no wall-clock
    sleeps or loop cancellation. Phase 117: claim_eval_job is mocked directly in
    the drain module so the tick can run without touching eval_queue_service sessions.
    """

    async def test_marker_set_after_drain(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After one drain tick on a seeded game, full_evals_completed_at IS NOT NULL."""
        from app.models.game import Game

        # Insert a non-guest game with evals_completed_at set (not in entry-ply queue)
        # and full_evals_completed_at NULL (pending for the full drain).
        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            pgn=_SIMPLE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user
        )

        # Engine returns a valid eval (4-tuple: eval_cp, eval_mate, best_move, pv_string).
        mock_evaluate = AsyncMock(return_value=(50, None, "e2e4", "e2e4 e7e5"))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        # Insert a game_position row so the drain has at least one target.
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            game_id,
            [{"ply": 0, "full_hash": 0xABCD_EF01, "eval_cp": None, "eval_mate": None}],
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game (WR-07 contract)"

            async with full_drain_session_maker() as verify_session:
                result = await verify_session.execute(
                    select(Game.full_evals_completed_at).where(Game.id == game_id)
                )
                row = result.scalar_one_or_none()

            assert row is not None, (
                f"Game {game_id} still has full_evals_completed_at IS NULL after drain tick "
                "— EVAL-05 marker not written."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])

    async def test_marker_set_with_holes(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When evaluate_nodes_with_pv fails for SOME plies, the marker is still set,
        the successful eval is written, and the failed ply remains NULL (D-116-07).

        SEED-044 post-move: a row stores the eval of the NEXT position. For
        _TWO_MOVE_PGN ("1. e4 e5 *", plies 0,1, terminal ply 2) the engine is called
        for ply 0, ply 1, and the terminal. Row 0 stores pos_eval[1] (engine ply-1
        result); row 1 stores pos_eval[2] (the TERMINAL result). So failing the
        terminal call makes row 1 the NULL hole while row 0 is written.

        WR-05: this must be a PARTIAL failure — an all-fail game now trips the
        circuit breaker and stays pending (see test_all_fail_keeps_game_pending).
        """
        from app.models.game import Game
        from app.models.game_position import GamePosition

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            pgn=_TWO_MOVE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user
        )

        # Engine calls (in order): ply 0, ply 1, terminal. Post-move:
        #   row 0 = pos_eval[1] = ply-1 result (50)  -> written
        #   row 1 = pos_eval[2] = terminal result (None)  -> NULL hole
        # ply-0 result's eval is unused for storage (no row before move 0).
        mock_evaluate = AsyncMock(
            side_effect=[
                (99, None, "e2e4", "e2e4 e7e5"),  # ply 0 (eval unused; supplies row 0 best_move)
                (50, None, "e7e5", "e7e5"),  # ply 1 -> row 0 eval
                (None, None, None, None),  # terminal -> row 1 hole
            ]
        )
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            game_id,
            [
                {"ply": 0, "full_hash": 0xCAFE_BABE, "eval_cp": None, "eval_mate": None},
                {"ply": 1, "full_hash": 0xCAFE_BABF, "eval_cp": None, "eval_mate": None},
            ],
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Partial failure must still process the game"

            async with full_drain_session_maker() as verify_session:
                game_row = await verify_session.execute(
                    select(Game.full_evals_completed_at).where(Game.id == game_id)
                )
                marker = game_row.scalar_one_or_none()

                pos_rows = await verify_session.execute(
                    select(GamePosition.ply, GamePosition.eval_cp, GamePosition.eval_mate)
                    .where(GamePosition.game_id == game_id)
                    .order_by(GamePosition.ply)
                )
                evals_by_ply = {r[0]: (r[1], r[2]) for r in pos_rows.all()}

            assert marker is not None, (
                "full_evals_completed_at must be set when only SOME plies failed "
                "— D-116-07: mark complete with holes."
            )
            assert evals_by_ply.get(0) == (50, None), (
                "Row 0 stores the post-move eval (ply-1 engine result = 50) alongside "
                "the terminal-driven hole at row 1."
            )
            assert evals_by_ply.get(1) == (None, None), (
                "game_position.eval_cp/eval_mate must remain NULL when the after-position "
                "(terminal) engine eval returned (None, None) — NULL holes stay NULL (D-116-07)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])

    async def test_all_fail_keeps_game_pending(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """WR-05 circuit breaker: when EVERY engine call fails, the game must NOT be
        marked complete — an all-fail tick is an engine-pool problem, and marking
        would permanently burn the backlog with all-NULL holes."""
        from app.models.game import Game

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            pgn=_SIMPLE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user
        )

        # Engine always returns all-None 4-tuple — simulated dead pool.
        mock_evaluate = AsyncMock(return_value=(None, None, None, None))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            game_id,
            [{"ply": 0, "full_hash": 0xCAFE_BAC0, "eval_cp": None, "eval_mate": None}],
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is False, (
                "Tick must report no progress when the circuit breaker trips (WR-05)."
            )

            async with full_drain_session_maker() as verify_session:
                game_row = await verify_session.execute(
                    select(Game.full_evals_completed_at).where(Game.id == game_id)
                )
                marker = game_row.scalar_one_or_none()

            assert marker is None, (
                "full_evals_completed_at must stay NULL when ALL engine evals failed "
                "— the game must remain pending for retry (WR-05 circuit breaker)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])


# ─── QUEUE-07: gather-outside-session invariant (AST scan) ────────────────────


class TestGatherOutsideSession:
    """QUEUE-07: asyncio.gather must NEVER be inside an AsyncSession scope in the full-drain tick.

    AST scan mirrors the existing test_gather_outside_session in test_eval_drain.py
    (T-91-08 pattern). Acts as a CI regression guard for the CLAUDE.md hard rule.
    WR-07: the gather moved from run_full_eval_drain into _full_drain_tick — the
    scan targets the tick (where the gather actually lives).
    """

    def test_gather_outside_session(self) -> None:
        """AST scan: asyncio.gather call in _full_drain_tick is not inside an async-with block."""
        from app.services.eval_drain import _full_drain_tick

        source = inspect.getsource(_full_drain_tick)
        tree = ast.parse(source)

        class GatherOutsideSessionChecker(ast.NodeVisitor):
            def __init__(self) -> None:
                self.violations: list[int] = []
                self._async_with_stack: int = 0

            def visit_AsyncWith(self, node: ast.AsyncWith) -> None:  # noqa: N802
                self._async_with_stack += 1
                self.generic_visit(node)
                self._async_with_stack -= 1

            def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
                func = node.func
                is_gather = False
                if isinstance(func, ast.Attribute) and func.attr == "gather":
                    is_gather = True
                if isinstance(func, ast.Name) and func.id == "gather":
                    is_gather = True
                if is_gather and self._async_with_stack > 0:
                    self.violations.append(getattr(node, "lineno", -1))
                self.generic_visit(node)

        checker = GatherOutsideSessionChecker()
        checker.visit(tree)

        assert checker.violations == [], (
            f"asyncio.gather() found inside an async-with scope at line(s) "
            f"{checker.violations} in _full_drain_tick — violates CLAUDE.md "
            f"hard rule (QUEUE-07 / T-116-06 architectural invariant)."
        )


# ─── QUEUE-07: yield gate ─────────────────────────────────────────────────────


class TestYieldGate:
    """QUEUE-07: _any_active_import_or_entry_ply_pending gates the full drain."""

    async def test_yield_gate_active_import(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Yield gate is True when an ImportJob with status 'pending' exists."""
        from app.models.import_job import ImportJob
        from app.services.eval_drain import _any_active_import_or_entry_ply_pending

        job_id = f"test-full-drain-yield-{uuid.uuid4().hex[:8]}"
        async with full_drain_session_maker() as session:
            session.add(
                ImportJob(
                    id=job_id,
                    user_id=full_drain_test_user,
                    platform="chess.com",
                    username="test_yield_user",
                    status="pending",
                    games_fetched=0,
                    games_imported=0,
                )
            )
            await session.commit()
        try:
            async with full_drain_session_maker() as check_session:
                result = await _any_active_import_or_entry_ply_pending(check_session)
            assert result is True, (
                "Yield gate must return True when a pending ImportJob exists (D-116-11)."
            )
        finally:
            await _delete_import_jobs(full_drain_session_maker, [job_id])

    async def test_yield_gate_entry_ply_pending(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Yield gate is True when a Game with evals_completed_at IS NULL exists."""
        from app.services.eval_drain import _any_active_import_or_entry_ply_pending

        # Insert a game with evals_completed_at = NULL (entry-ply drain has backlog).
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=None,
        )
        try:
            async with full_drain_session_maker() as check_session:
                result = await _any_active_import_or_entry_ply_pending(check_session)
            assert result is True, (
                "Yield gate must return True when a Game with evals_completed_at IS NULL "
                "exists (entry-ply drain backlog, D-116-11)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])


# ─── D-117-07: WR-02 repoint (lichess_evals_at gates dedup) ───────────────────


class TestWr02Repointed:
    """D-117-07: _fetch_dedup_evals gates on lichess_evals_at IS NULL, not white_blunders.

    After oracle counts are filled for engine games, white_blunders IS NOT NULL for
    engine games too — using white_blunders would wrongly exclude engine sources.
    The WR-02 gate was repointed onto lichess_evals_at (the reliable discriminator).
    """

    async def test_wr02_engine_source_included(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Engine-written game (lichess_evals_at IS NULL, white_blunders IS NOT NULL)
        must be usable as a dedup source after oracle counts are filled."""
        from app.services.eval_drain import _fetch_dedup_evals

        now = datetime.now(timezone.utc)
        engine_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=now,
            full_evals_completed_at=now,
            white_blunders=2,  # oracle counts filled — but lichess_evals_at is NULL
            # lichess_evals_at=None is the default — engine-written source
        )
        target_hash = 0xDEAD_BEEF_0010
        # Predecessor (ply 2) holds the post-move eval of the requested position
        # (ply 3) — the SEED-044 self-join recovers it.
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            engine_game_id,
            [
                {"ply": 2, "full_hash": 0xDEAD_BEEF_10FF, "eval_cp": 99, "eval_mate": None},
                {"ply": 3, "full_hash": target_hash, "eval_cp": 88, "eval_mate": None},
            ],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash in result, (
                "Engine-written source (lichess_evals_at IS NULL) must be usable as dedup "
                "even when white_blunders IS NOT NULL (D-117-07 — WR-02 repointed)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [engine_game_id])

    async def test_wr02_lichess_source_excluded(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
    ) -> None:
        """Lichess-analyzed game (lichess_evals_at IS NOT NULL, white_blunders IS NULL)
        must NOT be usable as a dedup source."""
        from app.services.eval_drain import _fetch_dedup_evals

        now = datetime.now(timezone.utc)
        lichess_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=now,
            full_evals_completed_at=now,
            lichess_evals_at=now,  # lichess-analyzed — not safe for transplant
            # white_blunders=None (no oracle counts yet)
        )
        target_hash = 0xDEAD_BEEF_0011
        # Predecessor present so the self-join WOULD match if not for the
        # lichess_evals_at gate (SEED-044 — the gate is what must exclude it).
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            lichess_game_id,
            [
                {"ply": 2, "full_hash": 0xDEAD_BEEF_11FF, "eval_cp": 55, "eval_mate": None},
                {"ply": 3, "full_hash": target_hash, "eval_cp": 44, "eval_mate": None},
            ],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash not in result, (
                "Lichess-analyzed source (lichess_evals_at IS NOT NULL) must NOT be "
                "usable as a dedup source even when white_blunders IS NULL (D-117-07)."
            )
        finally:
            await _delete_games(full_drain_session_maker, [lichess_game_id])


# ─── EVAL-04: best_move populated after drain tick ────────────────────────────


class TestBestMove:
    """EVAL-04: best_move is written for every evaluated non-dedup'd ply."""

    async def test_best_move_written_after_tick(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """best_move is populated in game_positions.best_move for every ply the
        engine evaluated (non-dedup'd) after a drain tick (EVAL-04 / D-117-01).

        _THREE_MOVE_PGN = "1. e4 e5 2. Nf3 Nc6 *" has 4 half-moves → 4 non-terminal
        positions (plies 0..3). Each ply gets a distinct best_move from the mock.
        """
        from app.models.game_position import GamePosition

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIX_PLY_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user_117
        )

        # Per-ply best_move for 4 positions (plies 0..3); use unique hashes. best_move
        # stays decision-ply-keyed under post-move (SEED-044), so each row keeps its own
        # engine best_move. A trailing terminal call is added (engine games evaluate the
        # post-game position as the last row's after-eval donor); its best_move is unused.
        best_moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
        mock_evaluate = AsyncMock(
            side_effect=[
                *[(cp, None, bm, bm) for cp, bm in zip([20, 15, 25, 10], best_moves)],
                (5, None, "h2h3", "h2h3"),  # terminal eval-donor call (best_move ignored)
            ]
        )
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        gp_rows = [
            {"ply": i, "full_hash": 0xBEEF_0020 + i, "eval_cp": None, "eval_mate": None}
            for i in range(4)
        ]
        await _insert_game_positions(
            full_drain_session_maker, full_drain_test_user_117, game_id, gp_rows
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            async with full_drain_session_maker() as verify:
                rows = await verify.execute(
                    select(GamePosition.ply, GamePosition.best_move)
                    .where(GamePosition.game_id == game_id)
                    .order_by(GamePosition.ply)
                )
                bm_by_ply = {r[0]: r[1] for r in rows.all()}

            assert bm_by_ply.get(0) == "e2e4", f"ply 0 best_move mismatch: {bm_by_ply.get(0)}"
            assert bm_by_ply.get(1) == "e7e5", f"ply 1 best_move mismatch: {bm_by_ply.get(1)}"
            assert bm_by_ply.get(2) == "g1f3", f"ply 2 best_move mismatch: {bm_by_ply.get(2)}"
            assert bm_by_ply.get(3) == "b8c6", f"ply 3 best_move mismatch: {bm_by_ply.get(3)}"
        finally:
            await _delete_games(full_drain_session_maker, [game_id])

    async def test_dedup_best_move_transplanted(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """best_move is transplanted from a dedup source for opening-region plies
        (ply <= DEDUP_MAX_PLY) without an engine call (EVAL-04 / D-117-01).

        Setup: a parity-source game has a position at ply 2 with full_hash X and
        best_move "g1f3". The target game has a position at the same hash (ply 2,
        dedup-eligible) and a position at a different hash (ply 4, engine-evaluated).

        PGN: _SIMPLE_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bc4 *" (5 half-moves, plies 0..4).
        We use ply 2 for dedup and ply 4 for engine-evaluated (both within PGN range).
        """
        from app.models.game_position import GamePosition
        from app.services.eval_drain import _DEDUP_MAX_PLY

        now = datetime.now(timezone.utc)
        dedup_hash = 0xBEEF_DED0_0001  # unique dedup source hash (ply 2 in source)

        # Parity source: full_evals_completed_at set, lichess_evals_at NULL.
        source_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            evals_completed_at=now,
            full_evals_completed_at=now,
        )
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user_117,
            source_game_id,
            [
                # SEED-044 self-join: the predecessor row (ply 1) holds the post-move
                # eval of the dedup position (ply 2); the dedup position's own row
                # carries the best_move FROM it. _fetch_dedup_evals recovers
                # (eval=30 from ply 1, best_move="g1f3" from ply 2).
                {"ply": 1, "full_hash": 0xBEEF_DED0_00FF, "eval_cp": 30, "eval_mate": None},
                {
                    "ply": 2,  # within DEDUP_MAX_PLY — the dedup'd position
                    "full_hash": dedup_hash,
                    "eval_cp": 31,
                    "eval_mate": None,
                    "best_move": "g1f3",  # the transplanted best_move (FROM this position)
                },
            ],
        )

        # Target game using _SIMPLE_PGN (plies 0..4 in PGN).
        target_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIMPLE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )
        # ply 2 (dedup-eligible, same hash as source) and ply 4 (engine-evaluated).
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user_117,
            target_game_id,
            [
                {
                    "ply": 2,
                    "full_hash": dedup_hash,  # will be dedup'd from source
                    "eval_cp": None,
                    "eval_mate": None,
                },
                {
                    "ply": 4,
                    "full_hash": 0xBEEF_DED0_0002,  # unique → engine-evaluated
                    "eval_cp": None,
                    "eval_mate": None,
                },
            ],
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, target_game_id, full_drain_test_user_117
        )

        # Engine is only called for the non-dedup ply (ply 4 — not in dedup_map).
        mock_evaluate = AsyncMock(return_value=(40, None, "d2d4", "d2d4"))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        assert 2 <= _DEDUP_MAX_PLY, f"ply 2 must be within DEDUP_MAX_PLY={_DEDUP_MAX_PLY}"

        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            async with full_drain_session_maker() as verify:
                rows = await verify.execute(
                    select(GamePosition.ply, GamePosition.best_move)
                    .where(GamePosition.game_id == target_game_id)
                    .order_by(GamePosition.ply)
                )
                bm_by_ply = {r[0]: r[1] for r in rows.all()}

            # Dedup'd ply 2: best_move transplanted from source (not engine-called).
            assert bm_by_ply.get(2) == "g1f3", (
                f"Dedup'd ply 2 must carry transplanted best_move 'g1f3', got {bm_by_ply.get(2)!r}"
            )
            # Engine-evaluated ply 4: best_move from engine.
            assert bm_by_ply.get(4) == "d2d4", (
                f"Engine-evaluated ply 4 must carry best_move 'd2d4', got {bm_by_ply.get(4)!r}"
            )
        finally:
            await _delete_games(full_drain_session_maker, [source_game_id, target_game_id])


# ─── EVAL-04: flaw PV written at ply N+1 (D-117-02) ──────────────────────────


def _blunder_eval_sequence() -> list[tuple[int, None, str, str]]:
    """Return an engine eval sequence whose POST-MOVE written rows cause exactly ONE
    blunder (white, ply 2) for _SIX_PLY_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 *".

    SEED-044 post-move convention: the drain stores at row k the eval of the position
    AFTER move k = the engine eval of the NEXT position (`_post_move_eval`). The engine
    is called per pre-push position (plies 0..5) PLUS the terminal position (ply 6),
    in that order. So row k's stored eval = engine_result[k + 1]. To reproduce the
    desired WRITTEN eval-by-ply [20, 30, -500, -480, 60, 30] at rows 0..5, the engine
    sequence is that list shifted right by one: a leading ply-0 entry (its eval is the
    eval of the start position, never stored — it only supplies row 0's best_move),
    then the six desired values at engine calls 1..6 (the last being the terminal).

    Stored (post-move) eval-by-ply after the tick — same as the historic pre-shift
    sequence, so the ES analysis is unchanged:
      row 0: 20   row 1: 30   row 2: -500 (WHITE BLUNDER)   row 3: -480   row 4: 60   row 5: 30

    Exact ES analysis (LICHESS_K = 0.00368208), over the STORED rows:
      n=1 (black): ES_black(20) ≈ 0.498, ES_black(30) ≈ 0.473 → drop ≈ 0.025 < INACCURACY_DROP
      n=2 (white): ES_white(30) ≈ 0.527, ES_white(-500) ≈ 0.163 → drop ≈ 0.364 >> BLUNDER_DROP
      n=3 (black): ES_black(-500) ≈ 0.837, ES_black(-480) ≈ 0.829 → drop ≈ 0.008 < threshold
      n=4 (white): ES_white(-480) ≈ 0.171, ES_white(60) ≈ 0.555 → drop = negative (improvement)
      n=5 (black): ES_black(60) ≈ 0.445, ES_black(30) ≈ 0.473 → drop = negative (improvement)

    Result: exactly one blunder (white at ply 2). PV must be written at ply 3 (the
    refutation board = engine_result_map[3]), nowhere else.
    """
    return [
        # engine call ply 0 — eval unused for storage (no row before move 0); supplies
        # row 0's best_move. The remaining six entries become the stored rows 0..5.
        (20, None, "e2e4", "e2e4 e7e5"),
        (20, None, "e2e4", "e2e4 e7e5"),  # → row 0 = 20 (balanced)
        (30, None, "e7e5", "e7e5 g1f3"),  # → row 1 = 30 (stable; black tiny drop)
        (
            -500,
            None,
            "g1f3",
            "g1f3 g8f6 d2d4",
        ),  # → row 2 = -500 (white BLUNDER; PV from here at ply 3)
        (-480, None, "g8f6", "g8f6 f1c4 d7d5"),  # → row 3 = -480 (still black winning)
        (60, None, "f1c4", "f1c4 f8c5"),  # → row 4 = 60 (white recovers)
        (30, None, "f8c5", "f8c5"),  # terminal call → row 5 = 30 (stable)
    ]


class TestFlawPv:
    """EVAL-04 / D-117-02: game_positions.pv is written ONLY at ply N+1 for a flaw at ply N.

    Pitfall 4: the PV belongs to the position AFTER the flawed move (the refutation
    line starts from the resulting position), NOT to the flaw position itself.
    """

    async def test_flaw_pv_written_at_ply_n_plus_one(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After a drain tick on a game with a clear blunder at ply 2 (white's move),
        game_positions.pv is set at ply 3 (ply N+1) and NULL at all other plies.

        classify_game_flaws emits a FlawRecord for ply 2 (n=2, mover=white).
        The PV for ply 3 (the refutation board) comes from engine_result_map[3].
        Plies 0,1,2,4,5 must have pv=NULL (pv only written at the flaw-adjacent ply).
        """
        from app.models.game_position import GamePosition

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIX_PLY_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user_117
        )

        eval_sequence = _blunder_eval_sequence()
        mock_evaluate = AsyncMock(side_effect=eval_sequence)
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        gp_rows = [
            {"ply": i, "full_hash": 0xBEEF_F1A0 + i, "eval_cp": None, "eval_mate": None}
            for i in range(6)
        ]
        await _insert_game_positions(
            full_drain_session_maker, full_drain_test_user_117, game_id, gp_rows
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            async with full_drain_session_maker() as verify:
                rows = await verify.execute(
                    select(GamePosition.ply, GamePosition.pv)
                    .where(GamePosition.game_id == game_id)
                    .order_by(GamePosition.ply)
                )
                pv_by_ply = {r[0]: r[1] for r in rows.all()}

            # ply 3 must have the PV from engine_result_map[3] (D-117-02 / Pitfall 4).
            assert pv_by_ply.get(3) is not None, (
                "game_positions.pv at ply 3 (N+1 for blunder at ply 2) must be set "
                "— D-117-02 flaw PV write."
            )
            # All other plies must NOT have a PV set (pv is only written at flaw N+1).
            for ply in [0, 1, 2, 4, 5]:
                assert pv_by_ply.get(ply) is None, (
                    f"game_positions.pv at ply {ply} must be NULL — pv is only written "
                    "at the ply AFTER a flaw (D-117-02 / Pitfall 4)."
                )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])

    async def test_flaw_pv_written_for_analyzed_lichess_game(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """D-117-13: analyzed lichess games still get a flaw PV even though every ply
        already carries a lichess %eval.

        Regression guard for the prod-observed 0% flaw-PV coverage on analyzed
        lichess games: the is_analyzed eval-preservation filter dropped every
        flaw-adjacent ply before the engine gather, so the refutation PV was never
        captured (lichess supplies %eval but no PV). The D-117-13 fix pre-classifies
        flaws and exempts {flaw_ply + 1} from the filter.

        Setup: all 6 plies carry a pre-existing %eval encoding a white blunder at
        ply 2. Only ply 3 (flaw_ply + 1) should be engine-evaluated (for the PV);
        the other five plies are preserved without an engine call. Before the fix,
        the engine was called 0 times and pv at ply 3 stayed NULL.
        """
        from app.models.game_position import GamePosition

        now = datetime.now(timezone.utc)
        # Analyzed lichess game: lichess_evals_at set; claim reports is_analyzed=True.
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIX_PLY_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
            lichess_evals_at=now,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch,
            full_drain_session_maker,
            game_id,
            full_drain_test_user_117,
            is_analyzed=True,
        )

        # Only ply 3 (flaw_ply + 1) should reach the engine — one PV result.
        mock_evaluate = AsyncMock(return_value=(-480, None, "g8f6", "g8f6 f1c4 d7d5"))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        # Pre-existing lichess %evals on EVERY ply, encoding a white blunder at ply 2
        # (30 cp -> -500 cp). Without D-117-13 the is_analyzed filter would drop all
        # six plies (each has an eval) and no PV would ever be captured.
        cp_by_ply = [20, 30, -500, -480, 60, 30]
        gp_rows = [
            {
                "ply": i,
                "full_hash": 0xABCDE000 + i,
                "eval_cp": cp_by_ply[i],
                "eval_mate": None,
            }
            for i in range(6)
        ]
        await _insert_game_positions(
            full_drain_session_maker, full_drain_test_user_117, game_id, gp_rows
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            # Exactly one engine call: the flaw-adjacent ply 3 (D-117-13). The other
            # five plies are preserved without burning a 1M-node eval.
            assert mock_evaluate.await_count == 1, (
                "Only the flaw-adjacent ply (flaw_ply + 1) should be engine-evaluated "
                f"for an analyzed game — got {mock_evaluate.await_count} engine calls."
            )

            async with full_drain_session_maker() as verify:
                rows = await verify.execute(
                    select(GamePosition.ply, GamePosition.pv, GamePosition.eval_cp)
                    .where(GamePosition.game_id == game_id)
                    .order_by(GamePosition.ply)
                )
                by_ply = {r[0]: (r[1], r[2]) for r in rows.all()}

            assert by_ply.get(3, (None, None))[0] is not None, (
                "game_positions.pv at ply 3 must be set for an analyzed lichess game "
                "— D-117-13 flaw-PV fix (lichess provides %eval but no PV)."
            )
            # Preserved lichess %evals are untouched (D-116-04 still holds).
            assert by_ply.get(3, (None, None))[1] == -480, (
                "The lichess %eval at the flaw-adjacent ply must be preserved, not "
                "overwritten by the engine eval (D-116-04)."
            )
            for ply in [0, 1, 2, 4, 5]:
                assert by_ply.get(ply, (None, None))[0] is None, (
                    f"game_positions.pv at ply {ply} must be NULL — pv is only written "
                    "at the ply AFTER a flaw (D-117-02 / Pitfall 4)."
                )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])


# ─── EVAL-06: classify hook + oracle counts ───────────────────────────────────


class TestClassifyHook:
    """EVAL-06: classify_game_flaws runs automatically after full eval completes.

    After a drain tick, game_flaws rows must exist for any game with sufficient
    eval coverage and at least one mistake/blunder.
    """

    async def test_classify_hook_inserts_game_flaws(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After a drain tick with a blunder at ply 2, game_flaws rows exist
        for the game (EVAL-06 / _classify_and_fill_oracle hook)."""
        from app.models.game_flaw import GameFlaw

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIX_PLY_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user_117
        )

        eval_sequence = _blunder_eval_sequence()
        mock_evaluate = AsyncMock(side_effect=eval_sequence)
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        gp_rows = [
            {"ply": i, "full_hash": 0xBEEF_B00C + i, "eval_cp": None, "eval_mate": None}
            for i in range(6)
        ]
        await _insert_game_positions(
            full_drain_session_maker, full_drain_test_user_117, game_id, gp_rows
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            async with full_drain_session_maker() as verify:
                flaw_count = await verify.scalar(
                    select(sa.func.count()).select_from(GameFlaw).where(GameFlaw.game_id == game_id)
                )

            assert flaw_count is not None and flaw_count > 0, (
                f"game_flaws must have rows after drain tick for game {game_id} "
                "— _classify_and_fill_oracle EVAL-06 hook must have run."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])


class TestOracleCounts:
    """EVAL-06 / D-117-08: oracle count columns are filled after full eval and match game_flaws."""

    async def test_oracle_counts_filled_and_match_game_flaws(
        self,
        full_drain_test_user_117: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After a drain tick, white/black inaccuracy/mistake/blunder columns on games
        are filled (D-117-08) and the blunder counts match the game_flaws rows.

        _blunder_eval_sequence creates one blunder at ply 2 (white's move). So:
          white_blunders = 1, white_mistakes = 0, white_inaccuracies = ? (via count_game_severities)
          black_blunders = 0, black_mistakes = 0, black_inaccuracies = ?
        The test verifies white_blunders >= 1 and black_blunders == 0 to avoid
        over-specifying the inaccuracy count (depends on exact sigmoid thresholds).
        It also verifies that sum(game_flaws severity=blunder for white) == white_blunders.
        """
        from app.models.game import Game
        from app.models.game_flaw import GameFlaw

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user_117,
            pgn=_SIX_PLY_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )

        drain_module = _patch_drain_for_tick_tests(
            monkeypatch, full_drain_session_maker, game_id, full_drain_test_user_117
        )

        eval_sequence = _blunder_eval_sequence()
        mock_evaluate = AsyncMock(side_effect=eval_sequence)
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes_with_pv", mock_evaluate)

        gp_rows = [
            {"ply": i, "full_hash": 0xBEEF_0AC0 + i, "eval_cp": None, "eval_mate": None}
            for i in range(6)
        ]
        await _insert_game_positions(
            full_drain_session_maker, full_drain_test_user_117, game_id, gp_rows
        )
        try:
            processed = await drain_module._full_drain_tick()
            assert processed is True, "Tick must report a processed game"

            async with full_drain_session_maker() as verify:
                game_row = await verify.execute(
                    select(
                        Game.white_blunders,
                        Game.white_mistakes,
                        Game.white_inaccuracies,
                        Game.black_blunders,
                        Game.black_mistakes,
                        Game.black_inaccuracies,
                    ).where(Game.id == game_id)
                )
                oracle = game_row.one_or_none()

                # White blunder rows in game_flaws: white plays at even plies (ply % 2 == 0).
                # ply 2 is white's blunder in the blunder-eval sequence.
                _SEVERITY_BLUNDER = 2
                white_blunder_rows = await verify.scalar(
                    select(sa.func.count())
                    .select_from(GameFlaw)
                    .where(
                        GameFlaw.game_id == game_id,
                        GameFlaw.severity == _SEVERITY_BLUNDER,
                        GameFlaw.ply % 2 == 0,  # white plays at even plies
                    )
                )

            assert oracle is not None, "Game row must exist after drain tick"
            white_blunders, white_mistakes, white_inaccuracies = oracle[0], oracle[1], oracle[2]
            black_blunders, black_mistakes, black_inaccuracies = oracle[3], oracle[4], oracle[5]

            # Oracle counts must be filled (not NULL).
            assert white_blunders is not None, "white_blunders must be set after drain (D-117-08)"
            assert white_mistakes is not None, "white_mistakes must be set after drain (D-117-08)"
            assert white_inaccuracies is not None, "white_inaccuracies must be set after drain"
            assert black_blunders is not None, "black_blunders must be set after drain (D-117-08)"
            assert black_mistakes is not None, "black_mistakes must be set after drain (D-117-08)"
            assert black_inaccuracies is not None, "black_inaccuracies must be set after drain"

            # The blunder sequence has exactly one clear blunder for white at ply 2.
            assert white_blunders >= 1, (
                f"white_blunders must be >= 1 for the blunder-sequence game, got {white_blunders}"
            )
            assert black_blunders == 0, (
                f"black_blunders must be 0 (no black blunders in eval sequence), got {black_blunders}"
            )

            # Oracle blunder count must match game_flaws blunder rows for white (D-117-08).
            assert white_blunders == white_blunder_rows, (
                f"white_blunders ({white_blunders}) must equal game_flaws blunder rows "
                f"for white ({white_blunder_rows}) — D-117-08 oracle consistency."
            )
        finally:
            await _delete_games(full_drain_session_maker, [game_id])
