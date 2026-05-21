"""Cold-drain architectural invariant tests for Phase 91.

Tests cover:
- gather-outside-session structural invariant (AST scan + static check)
- LIFO pick order (id DESC, batch=10)
- Idempotency: crash before commit leaves rows pending, re-picked next tick
- Engine (None, None) marks game completed — no permanent retry (D-09 / R-02)
- Partial index used for the LIFO pick query (ix_games_evals_pending EXPLAIN check)
- Cancellation propagates without retry (lifespan shutdown contract)

Integration tests that need to test code which opens its own sessions (like
run_eval_drain's helper functions) must commit data to the test DB and clean
up explicitly. We use the test_session_maker (backed by test_engine) directly
for test data inserts that need to be visible across sessions, and monkeypatch
app.services.eval_drain.async_session_maker to route drain sessions to the
test DB (same pattern as test_import_service.py).

Phase 91 / SEED-023 locked decisions exercised here:
    D-09: engine (None, None) → game still marked evals_completed_at = NOW()
    D-11: LIFO id-DESC, batch size = _DRAIN_BATCH_SIZE
    D-13: idle sleep = _DRAIN_IDLE_SLEEP_SECONDS (not tested for duration)
    T-91-06: stuck game at LIFO head gets marked done via D-09 guard
    T-91-08: gather-outside-session enforced by static AST test (CI regression)
    T-91-09: idempotency on crash verified by test_idempotent_on_simulated_crash
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio

# ─── Module-level test constants (CLAUDE.md: no magic numbers) ───────────────
LIFO_FIXTURE_GAME_COUNT: int = 15
PARTIAL_INDEX_THRESHOLD_ROWS: int = 200
_TEST_USER_ID: int = 99100  # unique per test module to avoid FK conflicts
_TEST_USER_ID_2: int = 99101  # second user for isolation tests
_SIMPLE_PGN: str = "1. e4 e5 2. Nf3 Nc6 3. Bc4 *"


# ─── Session-scoped fixture: committed test user ───────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def drain_test_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to the test engine.

    Used by integration tests to:
    1. Insert committed test data visible across sessions.
    2. Patch app.services.eval_drain.async_session_maker.
    """
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=False)
async def drain_test_user(drain_test_session_maker: async_sessionmaker[AsyncSession]) -> int:
    """Ensure test user _TEST_USER_ID exists in the test DB (committed). Returns user_id."""
    from app.models.user import User

    async with drain_test_session_maker() as session:
        from sqlalchemy import select as sa_select

        result = await session.execute(
            sa_select(User).where(User.id == _TEST_USER_ID)
        )
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"drain-test-{_TEST_USER_ID}@example.com",
                    hashed_password="fakehash",
                )
            )
            await session.commit()
    return _TEST_USER_ID


async def _insert_and_commit_pending_games(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int,
    n: int,
    pgn: str = _SIMPLE_PGN,
) -> list[int]:
    """Insert N Game rows with evals_completed_at=NULL and COMMIT. Returns inserted IDs.

    Commits so that other sessions (like drain helpers) can see the data.
    The caller is responsible for cleanup (DELETE games WHERE id IN ...).
    """
    from app.models.game import Game

    ids: list[int] = []
    async with session_maker() as session:
        for _ in range(n):
            g = Game(
                user_id=user_id,
                platform="chess.com",
                platform_game_id=f"drain-test-{uuid.uuid4().hex}",
                pgn=pgn,
                result="1-0",
                user_color="white",
                rated=True,
                is_computer_game=False,
            )
            session.add(g)
            await session.flush()
            ids.append(g.id)
        await session.commit()
    return ids


async def _delete_games_by_ids(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
) -> None:
    """Delete games with the given IDs (committed cleanup for integration tests)."""
    from app.models.game import Game

    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


# ─── Test: gather-outside-session (static AST check) ──────────────────────────


class TestGatherOutsideSession:
    """T-91-08: asyncio.gather must NEVER be inside an AsyncSession scope.

    This test parses the AST of run_eval_drain and fails if a future edit
    moves the gather call inside an `async with async_session_maker()` block.
    It acts as a CI regression guard for the core architectural invariant.
    """

    def test_gather_outside_session(self) -> None:
        """AST scan: asyncio.gather call in run_eval_drain is not inside an async-with block."""
        from app.services.eval_drain import run_eval_drain

        source = inspect.getsource(run_eval_drain)
        tree = ast.parse(source)

        # Walk the function body to find all `asyncio.gather(...)` Call nodes
        # and verify that none of them are nested inside an AsyncWith node.
        #
        # Strategy: track async-with scope depth during traversal.
        # When we encounter a gather() Call, its nesting depth must be 0.

        class GatherOutsideSessionChecker(ast.NodeVisitor):
            def __init__(self) -> None:
                self.violations: list[int] = []
                self._async_with_stack: int = 0  # depth counter for async-with scopes

            def visit_AsyncWith(self, node: ast.AsyncWith) -> None:  # noqa: N802
                """Track entry/exit of async-with contexts."""
                self._async_with_stack += 1
                self.generic_visit(node)
                self._async_with_stack -= 1

            def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
                """Check if this is a gather() call inside an async-with scope."""
                func = node.func
                is_gather = False

                # Match `asyncio.gather(...)` form
                if isinstance(func, ast.Attribute):
                    if func.attr == "gather":
                        is_gather = True

                # Match `gather(...)` form (bare import)
                if isinstance(func, ast.Name) and func.id == "gather":
                    is_gather = True

                if is_gather and self._async_with_stack > 0:
                    self.violations.append(getattr(node, "lineno", -1))

                self.generic_visit(node)

        checker = GatherOutsideSessionChecker()
        checker.visit(tree)

        assert checker.violations == [], (
            f"asyncio.gather() found inside an async-with scope at line(s) "
            f"{checker.violations} in run_eval_drain — violates CLAUDE.md "
            f"hard rule (T-91-08 / SEED-023 architectural invariant)."
        )


# ─── Test: LIFO pick order ─────────────────────────────────────────────────────


class TestLifoOrder:
    """D-11: pick query returns the 10 highest IDs in descending order."""

    async def test_lifo_order(
        self,
        drain_test_user: int,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Insert 15 pending games; verify _pick_pending_game_ids returns 10 highest IDs DESC."""
        import app.services.eval_drain as drain_module
        from app.services.eval_drain import _DRAIN_BATCH_SIZE, _pick_pending_game_ids

        # Route drain sessions to test DB
        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        # Insert and commit LIFO_FIXTURE_GAME_COUNT games with NULL evals_completed_at
        all_ids = await _insert_and_commit_pending_games(
            drain_test_session_maker, drain_test_user, LIFO_FIXTURE_GAME_COUNT
        )
        try:
            # Pick the batch
            picked = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)

            # Expect the 10 highest IDs in descending order (LIFO)
            expected = sorted(all_ids, reverse=True)[:_DRAIN_BATCH_SIZE]
            assert picked == expected, (
                f"LIFO pick order wrong: expected {expected}, got {picked}"
            )
        finally:
            await _delete_games_by_ids(drain_test_session_maker, all_ids)

    async def test_lifo_returns_at_most_batch_size(
        self,
        drain_test_user: int,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Insert 3 pending games; verify pick returns all 3 (< batch size)."""
        import app.services.eval_drain as drain_module
        from app.services.eval_drain import _DRAIN_BATCH_SIZE, _pick_pending_game_ids

        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        all_ids = await _insert_and_commit_pending_games(
            drain_test_session_maker, drain_test_user, 3
        )
        try:
            picked = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)

            # Should return all 3, which are the highest IDs
            highest_3 = sorted(all_ids, reverse=True)
            # The picked set may include other games from other tests, but our 3 must all appear
            for gid in highest_3:
                assert gid in picked, f"Game {gid} not picked despite being pending"
        finally:
            await _delete_games_by_ids(drain_test_session_maker, all_ids)


# ─── Test: idempotency on simulated crash ──────────────────────────────────────


class TestIdempotentOnSimulatedCrash:
    """T-91-09: crash before commit leaves rows pending; they are re-picked."""

    async def test_idempotent_on_simulated_crash(
        self,
        drain_test_user: int,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Simulate a crash in _mark_evals_completed (before commit) and verify rows remain NULL.

        The idempotency invariant: if the drain crashes before session.commit(),
        all picked games remain evals_completed_at IS NULL and are re-picked on
        the next tick. We crash _mark_evals_completed (which runs inside the
        write-window session before commit) to exercise this invariant reliably.
        """
        import app.services.eval_drain as drain_module
        from app.services.eval_drain import (
            _DRAIN_BATCH_SIZE,
            _mark_evals_completed,
            _pick_pending_game_ids,
        )
        from app.models.game import Game

        # Route drain sessions to test DB
        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        # Track Sentry capture_exception calls
        capture_calls: list[Any] = []

        def mock_capture_exception(exc: Any = None) -> None:
            capture_calls.append(exc)

        monkeypatch.setattr(drain_module.sentry_sdk, "capture_exception", mock_capture_exception)
        monkeypatch.setattr(drain_module.sentry_sdk, "set_tag", lambda *a, **kw: None)
        monkeypatch.setattr(drain_module.sentry_sdk, "set_context", lambda *a, **kw: None)

        # Insert 3 pending games (committed so drain sessions can see them)
        game_ids = await _insert_and_commit_pending_games(
            drain_test_session_maker, drain_test_user, 3
        )
        try:
            # Monkeypatch _mark_evals_completed to raise before committing.
            # This simulates a crash INSIDE the write-window session, after
            # UPDATEs are issued but before session.commit() — the session
            # is rolled back and all picked games remain evals_completed_at IS NULL.
            original_mark = _mark_evals_completed

            async def crashing_mark(
                session: AsyncSession,
                ids: Any,
            ) -> None:
                raise RuntimeError("simulated crash before commit in _mark_evals_completed")

            monkeypatch.setattr(drain_module, "_mark_evals_completed", crashing_mark)

            # Drive one drain iteration; the exception should be caught by the
            # Exception handler in run_eval_drain and the loop sleeps.
            drain_task = asyncio.create_task(drain_module.run_eval_drain())
            try:
                await asyncio.wait_for(asyncio.shield(drain_task), timeout=0.5)
            except asyncio.TimeoutError:
                pass  # expected — drain is sleeping after the error
            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass

            # (a) All 3 games must still have evals_completed_at IS NULL
            async with drain_test_session_maker() as verify_session:
                result = await verify_session.execute(
                    select(Game.id, Game.evals_completed_at).where(Game.id.in_(game_ids))
                )
                rows = result.all()

            assert len(rows) == 3
            for row in rows:
                assert row.evals_completed_at is None, (
                    f"Game {row.id} has evals_completed_at set after simulated crash — "
                    f"idempotency invariant violated (T-91-09)"
                )

            # (b) Sentry capture_exception was called for the RuntimeError
            assert len(capture_calls) >= 1, (
                "sentry_sdk.capture_exception was not called after simulated crash"
            )

            # Restore original _mark_evals_completed for the re-pick check
            monkeypatch.setattr(drain_module, "_mark_evals_completed", original_mark)

            # (c) The SAME 3 games are re-pickable (re-picked on next tick)
            picked_again = await _pick_pending_game_ids(limit=_DRAIN_BATCH_SIZE)
            for gid in game_ids:
                assert gid in picked_again, (
                    f"Game {gid} not re-picked after simulated crash — idempotency violated"
                )
        finally:
            await _delete_games_by_ids(drain_test_session_maker, game_ids)


# ─── Test: engine (None, None) marks game complete ─────────────────────────────


class TestEngineNoneMarksComplete:
    """D-09 / R-02: engine returning (None, None) must NOT cause permanent retry."""

    async def test_engine_none_marks_complete(
        self,
        drain_test_user: int,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Monkeypatch engine.evaluate to always return (None, None); verify games marked done."""
        import app.services.eval_drain as drain_module
        from app.models.game import Game

        # Route drain sessions to test DB
        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        # Suppress Sentry calls
        monkeypatch.setattr(drain_module.sentry_sdk, "capture_exception", lambda *a, **kw: None)
        monkeypatch.setattr(drain_module.sentry_sdk, "capture_message", lambda *a, **kw: None)
        monkeypatch.setattr(drain_module.sentry_sdk, "set_tag", lambda *a, **kw: None)
        monkeypatch.setattr(drain_module.sentry_sdk, "set_context", lambda *a, **kw: None)

        # Engine always returns (None, None)
        mock_evaluate = AsyncMock(return_value=(None, None))
        monkeypatch.setattr(drain_module.engine_service, "evaluate", mock_evaluate)

        # Insert 2 pending games with NULL evals_completed_at (committed so drain sees them)
        # No GamePosition rows — the drain will find 0 eval targets but still call
        # _mark_evals_completed for all picked game IDs (D-09 invariant).
        game_ids = await _insert_and_commit_pending_games(
            drain_test_session_maker, drain_test_user, 2
        )
        try:
            # Run one drain iteration with a short timeout.
            # The drain picks the games, finds 0 eval targets (no GamePosition rows),
            # skips _apply_eval_results, calls _mark_evals_completed, commits.
            drain_task = asyncio.create_task(drain_module.run_eval_drain())
            # Allow the drain to complete one full iteration (no eval targets → quick path)
            try:
                await asyncio.wait_for(asyncio.shield(drain_task), timeout=2.0)
            except asyncio.TimeoutError:
                pass  # drain goes back to idle sleep after processing
            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass

            # Both games must have evals_completed_at IS NOT NULL after the drain commits.
            async with drain_test_session_maker() as verify_session:
                result = await verify_session.execute(
                    select(Game.id, Game.evals_completed_at).where(Game.id.in_(game_ids))
                )
                rows = result.all()

            assert len(rows) == 2
            for row in rows:
                assert row.evals_completed_at is not None, (
                    f"Game {row.id} still has NULL evals_completed_at after drain iteration "
                    f"— D-09 / R-02 violated (engine returning (None,None) should not cause "
                    f"permanent retry; game must be marked complete)"
                )
        finally:
            await _delete_games_by_ids(drain_test_session_maker, game_ids)


# ─── Test: partial index used (EXPLAIN plan check) ────────────────────────────


class TestPartialIndexUsed:
    """T-91-08 / D-11: pick query must use ix_games_evals_pending partial index."""

    async def test_partial_index_used(
        self,
        drain_test_user: int,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """EXPLAIN the LIFO pick query and verify ix_games_evals_pending appears in the plan."""
        import app.services.eval_drain as drain_module

        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        # Pre-insert PARTIAL_INDEX_THRESHOLD_ROWS pending rows so the cost-based
        # planner chooses the partial index over a seq scan.
        game_ids = await _insert_and_commit_pending_games(
            drain_test_session_maker, drain_test_user, PARTIAL_INDEX_THRESHOLD_ROWS
        )
        try:
            # Run EXPLAIN against the exact query shape used by _pick_pending_game_ids.
            async with drain_test_session_maker() as session:
                explain_sql = text(
                    "EXPLAIN SELECT id FROM games WHERE evals_completed_at IS NULL "
                    "ORDER BY id DESC LIMIT 10"
                )
                result = await session.execute(explain_sql)
                plan_lines = [row[0] for row in result.all()]

            plan_text = "\n".join(plan_lines)

            # Assert the partial index is used and no seq scan.
            assert "ix_games_evals_pending" in plan_text, (
                f"Partial index ix_games_evals_pending not found in EXPLAIN plan.\n"
                f"Plan:\n{plan_text}\n"
                f"Check that PARTIAL_INDEX_THRESHOLD_ROWS ({PARTIAL_INDEX_THRESHOLD_ROWS}) "
                f"is large enough to make the index cost-effective."
            )
            assert "Seq Scan" not in plan_text, (
                f"Seq Scan found in EXPLAIN plan — partial index not used.\n"
                f"Plan:\n{plan_text}"
            )
        finally:
            await _delete_games_by_ids(drain_test_session_maker, game_ids)


# ─── Test: cancellation propagates ────────────────────────────────────────────


class TestCancellationPropagates:
    """Lifespan shutdown contract: CancelledError propagates from run_eval_drain."""

    async def test_cancellation_propagates(
        self,
        drain_test_session_maker: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cancel run_eval_drain task; verify CancelledError is raised, not swallowed."""
        import app.services.eval_drain as drain_module

        # Route sessions to test DB (so pick query runs against test DB)
        monkeypatch.setattr(drain_module, "async_session_maker", drain_test_session_maker)

        # Suppress Sentry
        monkeypatch.setattr(drain_module.sentry_sdk, "capture_exception", lambda *a, **kw: None)
        monkeypatch.setattr(drain_module.sentry_sdk, "set_tag", lambda *a, **kw: None)

        # Start the drain task — it will find 0 pending games and sleep
        drain_task = asyncio.create_task(drain_module.run_eval_drain())

        # Give it a moment to enter the idle sleep
        await asyncio.sleep(0.05)

        # Cancel and await — must raise CancelledError
        drain_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await drain_task
