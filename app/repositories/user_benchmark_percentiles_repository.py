"""Repository for user_benchmark_percentiles: UPSERT + per-user SELECT.

Phase 94.1 Plan 04 — implements the write/read path for materialised
canonical-slice percentile rows.

V4 Information Disclosure mitigation: ``fetch_for_user`` requires ``user_id``
as a keyword argument. The caller in Plan 07 passes ``current_user.id`` from
the FastAPI-Users dependency. Never accept ``user_id`` as a query parameter.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.user_benchmark_percentile import UserBenchmarkPercentile
from app.services.global_percentile_cdf import CdfMetricId


@dataclass(frozen=True)
class PercentileRow:
    """Internal dataclass for a single user_benchmark_percentiles row.

    Used by ``fetch_for_user`` to return structured data with attribute access.
    Frozen dataclass (immutable) per CLAUDE.md internal-structured-data rule.
    """

    value: float
    percentile: float | None
    n_cells_floor: int
    cdf_snapshot: datetime.date


async def upsert_percentile(
    session: AsyncSession,
    *,
    user_id: int,
    metric: CdfMetricId,
    value: float,
    percentile: float | None,
    n_cells_floor: int,
    cdf_snapshot: datetime.date,
) -> None:
    """Insert or update one (user_id, metric) row in user_benchmark_percentiles.

    Uses ``INSERT ... ON CONFLICT (user_id, metric) DO UPDATE`` so the
    operation is atomic and idempotent. The caller is responsible for committing
    the session after all writes in a unit of work are done.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Internal user PK.
        metric: One of the 4 CdfMetricId values.
        value: User's canonical-slice metric value (pooled across TCs).
        percentile: Lookup percentile in [0, 100], or None when below floor (D-06).
        n_cells_floor: Count of (elo_bucket, tc_bucket) cells that passed the
            per-metric HAVING inclusion floor at compute time. NOT a game
            count. See Phase 94.1 REVIEW.md CR-01.
        cdf_snapshot: Date of the CDF artifact used for interpolation.
    """
    stmt = pg_insert(UserBenchmarkPercentile).values(
        user_id=user_id,
        metric=metric,
        value=value,
        percentile=percentile,
        n_cells_floor=n_cells_floor,
        cdf_snapshot=cdf_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "metric"],
        set_={
            "value": stmt.excluded.value,
            "percentile": stmt.excluded.percentile,
            "n_cells_floor": stmt.excluded.n_cells_floor,
            "cdf_snapshot": stmt.excluded.cdf_snapshot,
            "computed_at": func.now(),  # server-side NOW() refresh on every update
        },
    )
    await session.execute(stmt)


async def fetch_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[CdfMetricId, PercentileRow]:
    """Return all percentile rows for a user, keyed by metric ID.

    V4 Information Disclosure mitigation: Caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_user.id``); never accept
    ``user_id`` as a query parameter from the client.

    Returns only the metrics that have been computed — missing metrics are
    absent from the dict, not represented as None/empty rows (e.g., Stage A
    has fired but Stage B has not: only ``score_gap`` will be present).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK.

    Returns:
        Dict keyed by CdfMetricId, values are PercentileRow TypedDicts.
    """
    result = await session.execute(
        select(
            UserBenchmarkPercentile.metric,
            UserBenchmarkPercentile.value,
            UserBenchmarkPercentile.percentile,
            UserBenchmarkPercentile.n_cells_floor,
            UserBenchmarkPercentile.cdf_snapshot,
        ).where(UserBenchmarkPercentile.user_id == user_id)
    )
    rows = result.fetchall()
    return {
        row.metric: PercentileRow(
            value=row.value,
            percentile=row.percentile,
            n_cells_floor=row.n_cells_floor,
            cdf_snapshot=row.cdf_snapshot,
        )
        for row in rows
    }
