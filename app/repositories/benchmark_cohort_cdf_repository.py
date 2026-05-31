"""Async repository for reading ``benchmark_cohort_cdf`` breakpoint data.

This is the ONLY async DB access for Phase 99.1 (D-04).  ``global_percentile_cdf``
stays 100% pure and synchronous; this repository handles the DB round-trip and
reconstructs ``CdfTable`` instances from the long-format rows.

Design (D-03): ``load_cohort_cells`` is a BATCHED PREFETCH loader.  The caller
issues ONE call before a per-import loop, pulling all needed (metric, anchor, TC)
cells into an in-memory dict.  Each subsequent interpolation hits that dict, not
the DB (~32 lookups per import, zero extra queries).

Row ordering: ``ORDER BY metric, anchor_elo, tc, percentile`` is load-bearing.
``CdfTable.breakpoints`` is indexed parallel to ``BREAKPOINT_PERCENTILES``
(p1..p99), so rows must arrive in ascending-percentile order within each cell to
produce a valid breakpoint tuple.

Sentry: errors here propagate to the top-level handler in
``user_benchmark_percentiles_service`` (per-import try/except block).  No
``capture_exception`` here -- the caller owns that boundary.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_cohort_cdf import BenchmarkCohortCdf
from app.models.user_rating_anchors import TimeControlBucket
from app.services.global_percentile_cdf import BENCHMARK_DB_SNAPSHOT_MONTH, CdfMetricId, CdfTable

__all__ = ["load_cohort_cells"]

# A complete breakpoint cell has exactly this many rows (p1..p99).
_EXPECTED_BREAKPOINTS: int = 99


async def load_cohort_cells(
    session: AsyncSession,
    anchors: Sequence[int],
    tcs: Sequence[TimeControlBucket],
) -> dict[tuple[CdfMetricId, int, TimeControlBucket], CdfTable]:
    """Return a prefetched dict of CdfTable cells for the given anchor x TC grid.

    Issues a single SELECT covering all (metric, anchor_elo, tc) combinations
    needed by the caller.  Rows are grouped by (metric, anchor_elo, tc) and
    ``value`` floats are assembled into a ``CdfTable.breakpoints`` tuple in
    p1..p99 percentile order (guaranteed by the ORDER BY clause).

    Cells with fewer than 99 rows are skipped -- a complete cell always has
    exactly 99 breakpoints.  The caller receives None for missing keys (the chip
    suppression / graceful-degradation path).

    Args:
        session: An open async SQLAlchemy session.
        anchors: The anchor ELO values to fetch (typically the rounded grid
            values for a user's active time controls).
        tcs: The time control bucket values to fetch.

    Returns:
        dict keyed by (metric, anchor_elo, tc) mapping to CdfTable instances.
        Returns {} immediately when anchors or tcs is empty (no query issued).
    """
    if not anchors or not tcs:
        return {}

    stmt = (
        select(BenchmarkCohortCdf)
        .where(
            BenchmarkCohortCdf.anchor_elo.in_(anchors),
            BenchmarkCohortCdf.tc.in_(tcs),
        )
        .order_by(
            BenchmarkCohortCdf.metric,
            BenchmarkCohortCdf.anchor_elo,
            BenchmarkCohortCdf.tc,
            BenchmarkCohortCdf.percentile,
        )
    )

    rows_result = await session.execute(stmt)
    rows = list(rows_result.scalars())

    return _group_rows_into_cells(rows)


def _group_rows_into_cells(
    rows: list[BenchmarkCohortCdf],
) -> dict[tuple[CdfMetricId, int, TimeControlBucket], CdfTable]:
    """Group ordered rows into CdfTable cells keyed by (metric, anchor_elo, tc).

    Relies on rows arriving in (metric, anchor_elo, tc, percentile) order from
    the ORDER BY clause -- do not call with unsorted rows.

    Cells with fewer than _EXPECTED_BREAKPOINTS rows are silently dropped
    (defensive guard: a complete cell always has exactly 99 breakpoints).
    """
    # Accumulate value lists per cell key; preserve insertion order (percentile order).
    values_by_key: dict[tuple[CdfMetricId, int, TimeControlBucket], list[float]] = defaultdict(list)
    # Store audit fields from the first row of each cell (identical across all 99 rows).
    audit_by_key: dict[
        tuple[CdfMetricId, int, TimeControlBucket], tuple[int | None, str | None]
    ] = {}

    for row in rows:
        # row.metric / row.tc are Mapped ENUM columns; at runtime they carry the
        # Literal string value.  ty infers LiteralString from str() which is not
        # assignable to the Literal union -- suppress with the correct ty rule.
        metric: CdfMetricId = str(row.metric)  # ty: ignore[invalid-assignment]
        tc: TimeControlBucket = str(row.tc)  # ty: ignore[invalid-assignment]
        key: tuple[CdfMetricId, int, TimeControlBucket] = (metric, row.anchor_elo, tc)
        values_by_key[key].append(row.value)
        if key not in audit_by_key:
            audit_by_key[key] = (row.n_users, row.snapshot_month)

    result: dict[tuple[CdfMetricId, int, TimeControlBucket], CdfTable] = {}
    for key, values in values_by_key.items():
        if len(values) < _EXPECTED_BREAKPOINTS:
            # Incomplete cell -- skip defensively.
            continue
        n_users_raw, snapshot_month_raw = audit_by_key[key]
        # CdfTable.n_users is typed int (non-optional); DB column is NULLable.
        # Coalesce NULL to 0 -- n_users is audit-only and does not affect
        # interpolation, so parity is unaffected.
        n_users: int = n_users_raw or 0
        snapshot_month: str = snapshot_month_raw or BENCHMARK_DB_SNAPSHOT_MONTH
        result[key] = CdfTable(
            breakpoints=tuple(values),
            n_users=n_users,
            snapshot_month=snapshot_month,
        )

    return result
