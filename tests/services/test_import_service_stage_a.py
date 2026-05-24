"""Wave 0 scaffolding for Stage A hook tests.

Phase 94.1 Plan 02, Task 1.

Tests cover the Stage A hook at _complete_import_job (import_service.py:480):
- Hook fires AFTER session.commit() (D-03 / ROADMAP success criterion 3)
- Hook does NOT fire inside the import transaction
- Hook exceptions do not propagate to the import worker (D-04)

All tests are skipped pre-implementation via pytest.importorskip on
app.services.user_benchmark_percentiles_service.

Design decisions documented:
- D-03: Stage A hook lives in _complete_import_job, fires AFTER commit
- D-04: Stage A is non-blocking; errors must not propagate to the trigger site
- ROADMAP SC 3: hook does not run inside the import transaction
"""

from __future__ import annotations

import pytest

# ── Skip entire module until implementation modules exist ─────────────────────
user_benchmark_percentiles_service = pytest.importorskip(
    "app.services.user_benchmark_percentiles_service"
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_ID: int = 99201  # unique per module to avoid FK conflicts
_TEST_JOB_ID: str = "test-stage-a-job-001"

pytestmark = pytest.mark.asyncio


async def test_stage_a_fires_after_import_commit(monkeypatch) -> None:
    """compute_stage_a is called exactly once after _complete_import_job commits.

    Call-ordering contract (D-03 / ROADMAP SC 3):
    - session.commit() must be called BEFORE compute_stage_a
    - compute_stage_a must be called exactly once with the correct user_id

    Implementation note: the test captures call order by recording call positions
    in a shared list. The commit_calls list must contain a 'commit' entry before
    any 'stage_a' entry.

    AFTER commit = D-03 / ROADMAP SC 3 compliance.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_stage_a_runs_outside_import_transaction(monkeypatch) -> None:
    """compute_stage_a is NOT called when the import transaction (session.commit)
    raises — demonstrating the hook is OUTSIDE the transaction.

    Inverse behavior documented: if the hook were INSIDE the transaction, our spy
    would have been called even when the commit failed. This test pins the
    OUTSIDE-transaction guarantee (ROADMAP success criterion 3).

    Implementation note: patch session.commit to raise after the import-tx write
    but before the hook enqueue. Assert spy was NOT called.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_stage_a_exception_does_not_break_import_completion(
    monkeypatch,
) -> None:
    """_complete_import_job returns successfully even when compute_stage_a raises.

    asyncio.create_task isolates the background task exception from the caller.
    This test pins the fire-and-forget isolation behavior (D-04).

    The test patches compute_stage_a to raise RuntimeError and asserts that
    _complete_import_job completes (returns) without propagating the exception.
    """
    pytest.skip("implementation pending Plans 05/06")
