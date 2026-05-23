"""Wave 0 scaffolding for chip-decoupling tests (PCTL-07 / D-12).

Phase 94.1 Plan 02, Task 2.

Tests cover the D-12 rewire: the 4 {metric}_percentile response fields read from
user_benchmark_percentiles (materialised at import time) instead of per-request
interpolate_percentile(filter_applied_value). This makes the chip filter-independent.

Security domain V4 (Information Disclosure):
- test_chip_percentile_scopes_by_authenticated_user_id: verifies the SELECT
  filters WHERE user_id = current_user.id; user_id is never accepted as a query param.

Skipped pre-implementation via pytest.importorskip on the repository module.
"""

from __future__ import annotations

import pytest

# ── Skip entire module until repository module exists ─────────────────────────
user_benchmark_percentiles_repository = pytest.importorskip(
    "app.repositories.user_benchmark_percentiles_repository"
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_A_ID: int = 99204  # unique per module to avoid FK conflicts
_TEST_USER_B_ID: int = 99205
_KNOWN_SCORE_GAP_PERCENTILE: float = 72.5  # planted materialised value
_KNOWN_ACHIEVABLE_PERCENTILE: float = 55.0
_KNOWN_CONV_PERCENTILE: float = 41.0
_KNOWN_PARITY_PERCENTILE: float = 68.0

pytestmark = pytest.mark.asyncio


async def test_chip_percentile_unchanged_across_filter_toggles(
    test_engine,
) -> None:
    """toggling filter inputs (recency, time_control, etc.) does not change
    {metric}_percentile values in the API response.

    Seeds user_benchmark_percentiles with known (value, percentile) for the
    test user. Makes two GET requests to the endgame endpoint with different
    filter sets. Asserts score_gap_percentile == _KNOWN_SCORE_GAP_PERCENTILE
    in both responses (and similarly for the other 3 chipped metrics).

    The row's filter-applied score_difference WILL differ between calls (it
    still comes from per-request compute), but the percentile chip is locked
    to the materialised value (D-12 / PCTL-07).
    """
    pytest.skip("implementation pending Plans 07/08")


async def test_chip_percentile_scopes_by_authenticated_user_id(
    test_engine,
) -> None:
    """V4 Information Disclosure guard: the response contains the authenticated
    user's percentile, NOT another user's percentile.

    Seeds 2 users (A and B) with distinct materialised percentiles.
    Authenticates as user A. Asserts:
    - response contains user A's score_gap_percentile (_KNOWN_SCORE_GAP_PERCENTILE)
    - response does NOT contain user B's percentile value

    The SELECT in endgame_service.py must carry WHERE user_id = current_user.id.
    user_id is derived server-side from the FastAPI-Users auth dependency — it is
    NEVER accepted as a query parameter (V4 Tampering guard).

    Documented: authenticated user = the source of user_id; no bypass via param.
    """
    pytest.skip("implementation pending Plans 07/08")


async def test_chip_percentile_is_none_when_no_row_in_table(
    test_engine,
) -> None:
    """Graceful degradation: when user has no row in user_benchmark_percentiles,
    all 4 {metric}_percentile fields in the API response are None.

    Phase 94's chip renders nothing (chip absent on FE) when the field is None.
    This is the "not yet computed" state for new users who have not yet gone
    through Stage A / Stage B.
    """
    pytest.skip("implementation pending Plans 07/08")


async def test_chip_percentile_is_none_when_percentile_column_is_null(
    test_engine,
) -> None:
    """When a user_benchmark_percentiles row exists with value=X but percentile=NULL
    (below-floor case per D-10), the API response field is None.

    This is the 'computed but below inclusion floor' state — the value is stored
    for future floor-change recompute, but the chip does not render (percentile=NULL
    emits as None on the wire, chip absent on FE).
    """
    pytest.skip("implementation pending Plans 07/08")
