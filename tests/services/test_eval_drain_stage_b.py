"""Wave 0 scaffolding for Stage B hook tests.

Phase 94.1 Plan 02, Task 1.

Tests cover the Stage B hook at eval_drain.py (after _mark_evals_completed commit):
- Hook fires only when a user's pending-eval count drops to 0 (D-01)
- No duplicate fires per user per drain batch
- No per-user duplicate fires when multiple games for the same user in one batch
- Exception does not crash the drain coroutine (D-04)

All tests are skipped pre-implementation via pytest.importorskip on
app.services.user_benchmark_percentiles_service.

Design decisions documented:
- D-01: Per-batch group-by-user check; fire only when count -> 0
- D-02: No periodic sweeper — backfill script is the safety net
- D-04: Stage B errors must not propagate to the drain coroutine
- ix_games_evals_pending: partial index used by the count query
"""

from __future__ import annotations

import pytest

# ── Skip entire module until implementation modules exist ─────────────────────
user_benchmark_percentiles_service = pytest.importorskip(
    "app.services.user_benchmark_percentiles_service"
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_A_ID: int = 99202  # unique per module to avoid FK conflicts
_TEST_USER_B_ID: int = 99203
_USER_A_TOTAL_GAMES: int = 10   # all drained in one batch -> pending after = 0
_USER_B_TOTAL_GAMES: int = 100  # only 10 drained -> pending after = 90
_DRAIN_BATCH_SIZE: int = 10     # matches eval_drain._DRAIN_BATCH_SIZE

pytestmark = pytest.mark.asyncio


async def test_stage_b_fires_only_for_users_whose_pending_count_drops_to_zero(
    test_engine,
    monkeypatch,
) -> None:
    """Stage B fires for user A (all 10 games drained, pending = 0) but NOT
    for user B (90 games remain pending after first batch).

    Seeds:
    - user A: 10 games all needing eval (all drain in one batch of 10)
    - user B: 100 games needing eval (only 10 drained in first batch)

    Asserts:
    - compute_stage_b called exactly once for user A (D-01)
    - compute_stage_b NOT called for user B (D-01)
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_stage_b_fires_once_per_user_per_completion(
    test_engine,
    monkeypatch,
) -> None:
    """When a drain batch contains multiple games for the same user and draining
    all of them brings their pending count to 0, compute_stage_b is called
    exactly ONCE for that user (no duplicate fires).

    Seeds user with exactly _DRAIN_BATCH_SIZE games, all needing eval, so one
    batch drains all. Asserts compute_stage_b called exactly once.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_stage_b_per_user_count_query_uses_partial_index(
    test_engine,
) -> None:
    """Sanity gate: the pending-count query routes through
    game_repository.count_pending_evals (which the partial index
    ix_games_evals_pending already optimises).

    Defensible approach: assert count_pending_evals from game_repository is
    called with the correct user_id. The partial-index optimisation lives at
    the repository layer; we verify the correct path is taken.

    This avoids an EXPLAIN plan parse, which is DB-version-sensitive.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_stage_b_exception_does_not_crash_drain_coroutine(
    monkeypatch,
) -> None:
    """compute_stage_b raising RuntimeError does not crash or halt the eval
    drain coroutine. The drain continues to the next iteration normally.

    asyncio.create_task fire-and-forget isolates the exception from the drain
    loop (D-04). This test pins the isolation behavior.
    """
    pytest.skip("implementation pending Plans 05/06")
