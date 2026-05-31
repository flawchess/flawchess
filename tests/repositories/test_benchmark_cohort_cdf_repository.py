"""Repository tests for benchmark_cohort_cdf_repository: load_cohort_cells.

Phase 99.1 Plan 03 Task 2 -- TDD RED/GREEN tests for the batched prefetch
loader (D-03/D-04).

Tests:
1. test_empty_anchors_returns_empty -- early-return guard for empty anchors
2. test_empty_tcs_returns_empty -- early-return guard for empty tcs
3. test_cell_round_trip -- seeded (metric, anchor_elo, tc) reconstructs the
   correct 99-tuple CdfTable with matching n_users and snapshot_month
4. test_grouping_keys -- multiple cells returned with correct tuple keys
5. test_incomplete_cell_skipped -- cell with <99 rows is excluded defensively

Data isolation: all tests use the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` -- no committed rows leak between tests. Each test inserts
its own fixture rows via direct model inserts into the rolled-back transaction.
"""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_cohort_cdf import BenchmarkCohortCdf
from app.models.user_rating_anchors import TimeControlBucket
from app.repositories.benchmark_cohort_cdf_repository import load_cohort_cells
from app.services.global_percentile_cdf import (
    BREAKPOINT_PERCENTILES,
    CdfMetricId,
    CdfTable,
)

# ---------------------------------------------------------------------------
# Test constants -- no magic numbers
# ---------------------------------------------------------------------------

_METRIC: CdfMetricId = cast(CdfMetricId, "score_gap")
_METRIC_B: CdfMetricId = cast(CdfMetricId, "conversion_rate")
_ANCHOR_ELO: int = 1000
_ANCHOR_ELO_B: int = 1050
_TC: TimeControlBucket = cast(TimeControlBucket, "blitz")
_TC_B: TimeControlBucket = cast(TimeControlBucket, "rapid")
_SNAPSHOT_MONTH: str = "2026-05"
_N_USERS: int = 42
_N_PERCENTILES: int = 99  # BREAKPOINT_PERCENTILES has 99 entries (p1..p99)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_breakpoints(offset: float = 0.0) -> tuple[float, ...]:
    """Return a monotone 99-tuple with distinct values for round-trip testing.

    Values are anchored to percentile index so they're guaranteed unique per cell.
    """
    return tuple(float(i) * 0.001 + offset for i in range(1, _N_PERCENTILES + 1))


async def _insert_cell(
    session: AsyncSession,
    metric: CdfMetricId,
    anchor_elo: int,
    tc: TimeControlBucket,
    breakpoints: tuple[float, ...],
    n_users: int = _N_USERS,
    snapshot_month: str = _SNAPSHOT_MONTH,
) -> None:
    """Insert all 99 breakpoint rows for a single (metric, anchor_elo, tc) cell."""
    for idx, bp_float in enumerate(BREAKPOINT_PERCENTILES):
        percentile = int(bp_float)  # p1..p99
        value = breakpoints[idx]
        session.add(
            BenchmarkCohortCdf(
                metric=metric,
                anchor_elo=anchor_elo,
                tc=tc,
                percentile=percentile,
                value=value,
                n_users=n_users,
                snapshot_month=snapshot_month,
            )
        )
    await session.flush()


# ---------------------------------------------------------------------------
# Test 1: empty anchors returns {}
# ---------------------------------------------------------------------------


async def test_empty_anchors_returns_empty(db_session: AsyncSession) -> None:
    """load_cohort_cells with empty anchors list returns {} without querying."""
    result = await load_cohort_cells(db_session, [], [_TC])
    assert result == {}


# ---------------------------------------------------------------------------
# Test 2: empty tcs returns {}
# ---------------------------------------------------------------------------


async def test_empty_tcs_returns_empty(db_session: AsyncSession) -> None:
    """load_cohort_cells with empty tcs list returns {} without querying."""
    result = await load_cohort_cells(db_session, [_ANCHOR_ELO], [])
    assert result == {}


# ---------------------------------------------------------------------------
# Test 3: single cell round-trip
# ---------------------------------------------------------------------------


async def test_cell_round_trip(db_session: AsyncSession) -> None:
    """Seeded (metric, anchor_elo, tc) reconstructs the correct CdfTable.

    Checks that:
    - The dict key is (metric, anchor_elo, tc).
    - breakpoints is a 99-tuple in percentile order.
    - n_users and snapshot_month are taken from the cell rows.
    - Values match what was inserted.
    """
    expected_breakpoints = _make_breakpoints(offset=0.0)
    await _insert_cell(
        db_session,
        metric=_METRIC,
        anchor_elo=_ANCHOR_ELO,
        tc=_TC,
        breakpoints=expected_breakpoints,
        n_users=_N_USERS,
        snapshot_month=_SNAPSHOT_MONTH,
    )

    result = await load_cohort_cells(db_session, [_ANCHOR_ELO], [_TC])

    key = (_METRIC, _ANCHOR_ELO, _TC)
    assert key in result, f"Expected key {key!r} in result dict"
    table: CdfTable = result[key]

    assert len(table.breakpoints) == _N_PERCENTILES
    assert table.breakpoints == expected_breakpoints
    assert table.n_users == _N_USERS
    assert table.snapshot_month == _SNAPSHOT_MONTH


# ---------------------------------------------------------------------------
# Test 4: grouping keys -- multiple cells with correct tuple keys
# ---------------------------------------------------------------------------


async def test_grouping_keys(db_session: AsyncSession) -> None:
    """Multiple cells returned with correct (metric, anchor_elo, tc) tuple keys.

    Inserts two cells: (metric_a, anchor_a, tc_a) and (metric_b, anchor_b, tc_b).
    Both should appear in the result with their respective keys.
    """
    bp_a = _make_breakpoints(offset=0.0)
    bp_b = _make_breakpoints(offset=1.0)

    await _insert_cell(db_session, metric=_METRIC, anchor_elo=_ANCHOR_ELO, tc=_TC, breakpoints=bp_a)
    await _insert_cell(
        db_session, metric=_METRIC_B, anchor_elo=_ANCHOR_ELO_B, tc=_TC_B, breakpoints=bp_b
    )

    result = await load_cohort_cells(
        db_session,
        [_ANCHOR_ELO, _ANCHOR_ELO_B],
        [_TC, _TC_B],
    )

    key_a = (_METRIC, _ANCHOR_ELO, _TC)
    key_b = (_METRIC_B, _ANCHOR_ELO_B, _TC_B)

    assert key_a in result, f"Expected key {key_a!r} in result"
    assert key_b in result, f"Expected key {key_b!r} in result"
    assert result[key_a].breakpoints == bp_a
    assert result[key_b].breakpoints == bp_b


# ---------------------------------------------------------------------------
# Test 5: incomplete cell (fewer than 99 rows) is skipped defensively
# ---------------------------------------------------------------------------


async def test_incomplete_cell_skipped(db_session: AsyncSession) -> None:
    """A cell with fewer than 99 rows is not included in the result.

    This is a defensive guard -- a complete cell always has exactly 99 breakpoints.
    Inserts only 5 rows for (metric, anchor_elo, tc) and asserts the key is absent.
    """
    # Insert only 5 rows for one cell (incomplete)
    for percentile in range(1, 6):
        db_session.add(
            BenchmarkCohortCdf(
                metric=_METRIC,
                anchor_elo=_ANCHOR_ELO,
                tc=_TC,
                percentile=percentile,
                value=float(percentile) * 0.001,
                n_users=_N_USERS,
                snapshot_month=_SNAPSHOT_MONTH,
            )
        )
    await db_session.flush()

    result = await load_cohort_cells(db_session, [_ANCHOR_ELO], [_TC])

    key = (_METRIC, _ANCHOR_ELO, _TC)
    assert key not in result, "Incomplete cell (< 99 rows) must be skipped"
