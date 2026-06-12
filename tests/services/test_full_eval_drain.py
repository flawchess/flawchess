"""Integration tests for run_full_eval_drain (Phase 116 EVAL-01/03/05/QUEUE-07).

Tests cover:
- EVAL-01: all non-terminal plies collected; terminal position excluded
- EVAL-01: PGN parse failure returns empty list
- EVAL-03: dedup returns hit for known parity hash (full_evals_completed_at gated)
- EVAL-03: dedup ignores depth-15 source (no full_evals_completed_at marker)
- EVAL-05: full_evals_completed_at set after drain tick
- EVAL-05: marker set even when engine returns (None, None) holes
- QUEUE-07: asyncio.gather is NOT inside an async-with session scope (AST scan)
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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ─── Module-level test constants ──────────────────────────────────────────────

_TEST_USER_ID: int = 99200  # unique to this module to avoid FK conflicts
# A short PGN ending in checkmate (Scholar's mate in 4 moves = 8 half-moves).
# The final position IS checkmate; the iterator should never visit it.
_CHECKMATE_PGN: str = "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6?? 4. Qxf7# 1-0"
# A simple non-terminal PGN used for general tests.
_SIMPLE_PGN: str = "1. e4 e5 2. Nf3 Nc6 3. Bc4 *"
# A minimal PGN with only 2 moves (4 half-moves).
_TWO_MOVE_PGN: str = "1. e4 e5 *"


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
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"full-drain-test-{_TEST_USER_ID}@example.com",
                    hashed_password="fakehash",
                )
            )
            await session.commit()
    return _TEST_USER_ID


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def _insert_game(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    pgn: str = _SIMPLE_PGN,
    *,
    evals_completed_at: datetime | None = None,
    full_evals_completed_at: datetime | None = None,
    white_blunders: int | None = None,
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
    "eval_mate": int|None}.
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
                    move_san=None,
                    phase=0,
                    endgame_class=None,
                    eval_cp=r.get("eval_cp"),
                    eval_mate=r.get("eval_mate"),
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
        """A game_position row at ply<=20 whose game has full_evals_completed_at IS NOT NULL
        should be returned by _fetch_dedup_evals."""
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
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            source_game_id,
            [{"ply": 5, "full_hash": target_hash, "eval_cp": 42, "eval_mate": None}],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash in result, (
                f"Parity source (full_evals_completed_at set, ply {5} <= {_DEDUP_MAX_PLY}) "
                "must be returned by _fetch_dedup_evals (EVAL-03)."
            )
            assert result[target_hash] == (42, None)
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
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            depth15_game_id,
            [{"ply": 5, "full_hash": target_hash, "eval_cp": 100, "eval_mate": None}],
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
        """A drain-completed is_analyzed game (white_blunders set) must NOT be a dedup
        source (WR-02): its preserved rows are lichess post-move evals, which are not
        position-keyed by full_hash — only engine-written rows are safe to transplant."""
        from app.services.eval_drain import _fetch_dedup_evals

        now = datetime.now(timezone.utc)
        analyzed_game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            evals_completed_at=now,
            full_evals_completed_at=now,
            white_blunders=1,  # is_analyzed marker
        )
        target_hash = 0xDEAD_BEEF_0003
        await _insert_game_positions(
            full_drain_session_maker,
            full_drain_test_user,
            analyzed_game_id,
            [{"ply": 5, "full_hash": target_hash, "eval_cp": 77, "eval_mate": None}],
        )
        try:
            async with full_drain_session_maker() as session:
                result = await _fetch_dedup_evals(session, [target_hash])

            assert target_hash not in result, (
                "is_analyzed source (white_blunders IS NOT NULL) must NOT be returned "
                "by _fetch_dedup_evals — lichess post-move evals are not position-keyed "
                "by full_hash (WR-02)."
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
) -> Any:
    """Shared monkeypatching for direct _full_drain_tick tests (WR-07).

    Routes drain sessions to the test DB, suppresses Sentry, and forces the
    yield gate to False — the gate would otherwise depend on whether OTHER
    tests in the same worker left committed games with evals_completed_at
    IS NULL (the ordering-dependent flake the tick refactor eliminates).
    The gate itself is covered by TestYieldGate.

    Returns the drain module.
    """
    import app.services.eval_drain as drain_module

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
    return drain_module


class TestMarkerWrite:
    """EVAL-05: full_evals_completed_at is set after a drain tick.

    WR-07: tests call _full_drain_tick() directly — deterministic, scoped to
    one LIFO pick (the just-inserted game has the highest id), no wall-clock
    sleeps or loop cancellation.
    """

    async def test_marker_set_after_drain(
        self,
        full_drain_test_user: int,
        full_drain_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After one drain tick on a seeded game, full_evals_completed_at IS NOT NULL."""
        from app.models.game import Game

        drain_module = _patch_drain_for_tick_tests(monkeypatch, full_drain_session_maker)

        # Engine returns a valid eval so the write path exercises the UPDATE.
        mock_evaluate = AsyncMock(return_value=(50, None))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes", mock_evaluate)

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
        """When evaluate_nodes fails for SOME plies, the marker is still set, the
        successful eval is written, and the failed ply remains NULL (D-116-07).

        WR-05: this must be a PARTIAL failure — an all-fail game now trips the
        circuit breaker and stays pending (see test_all_fail_keeps_game_pending).
        """
        from app.models.game import Game
        from app.models.game_position import GamePosition

        drain_module = _patch_drain_for_tick_tests(monkeypatch, full_drain_session_maker)

        # Engine succeeds for the first target (ply 0), fails for the second (ply 1).
        mock_evaluate = AsyncMock(side_effect=[(50, None), (None, None)])
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes", mock_evaluate)

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            pgn=_SIMPLE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )
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
                "Successful eval for ply 0 must be written alongside the hole at ply 1."
            )
            assert evals_by_ply.get(1) == (None, None), (
                "game_position.eval_cp/eval_mate must remain NULL when engine returned "
                "(None, None) — NULL holes stay NULL (D-116-07)."
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

        drain_module = _patch_drain_for_tick_tests(monkeypatch, full_drain_session_maker)

        # Engine always returns (None, None) — simulated dead pool.
        mock_evaluate = AsyncMock(return_value=(None, None))
        monkeypatch.setattr(drain_module.engine_service, "evaluate_nodes", mock_evaluate)

        now = datetime.now(timezone.utc)
        game_id = await _insert_game(
            full_drain_session_maker,
            full_drain_test_user,
            pgn=_SIMPLE_PGN,
            evals_completed_at=now,
            full_evals_completed_at=None,
        )
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
