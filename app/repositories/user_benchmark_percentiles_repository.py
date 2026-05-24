"""Repository for user_benchmark_percentiles: UPSERT + per-user SELECT.

Phase 94.1 Plan 04 — implements the write/read path for materialised
canonical-slice percentile rows.

Phase 94.1 Plan 13 (gap-closure): ``n_cells_floor`` column dropped.
Row existence now implies above-floor — no row is written for below-floor
(user, metric) pairs. ``PercentileRow``, ``upsert_percentile``, and
``fetch_for_user`` no longer reference ``n_cells_floor``.

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

    Row existence implies above-floor (Plan 13): callers need not check
    ``n_cells_floor``; if the row is present, the user passed the floor.
    """

    value: float
    percentile: float | None
    cdf_snapshot: datetime.date


async def upsert_percentile(
    session: AsyncSession,
    *,
    user_id: int,
    metric: CdfMetricId,
    value: float,
    n_games: int,
    percentile: float | None,
    cdf_snapshot: datetime.date,
) -> None:
    """Insert or update one (user_id, metric) row in user_benchmark_percentiles.

    Uses ``INSERT ... ON CONFLICT (user_id, metric) DO UPDATE`` so the
    operation is atomic and idempotent. The caller is responsible for committing
    the session after all writes in a unit of work are done.

    Only call this function when ``value`` is not None (i.e., the user is above
    the pooled inclusion floor). Below-floor users produce no row — callers
    must skip the upsert when ``_compute_metric_for_user`` returns None.

    Phase 94.2 (D-9-amend): the ``n_games`` parameter is required. Under the
    pooled-per-user model it carries per-metric meaning — see the
    ``UserBenchmarkPercentile`` class docstring for the per-metric mapping. The
    parameter participates in both the insert values and the on-conflict update
    so refreshed UPSERTs replace the prior count.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Internal user PK.
        metric: One of the 4 CdfMetricId values.
        value: User's pooled metric value (above-floor by construction).
        n_games: Per-metric pooled count (binding inclusion-floor count).
        percentile: Lookup percentile in [0, 100], or None for future use.
        cdf_snapshot: Date of the CDF artifact used for interpolation.
    """
    stmt = pg_insert(UserBenchmarkPercentile).values(
        user_id=user_id,
        metric=metric,
        value=value,
        n_games=n_games,
        percentile=percentile,
        cdf_snapshot=cdf_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "metric"],
        set_={
            "value": stmt.excluded.value,
            "n_games": stmt.excluded.n_games,
            "percentile": stmt.excluded.percentile,
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

    An absent entry also means the user is below floor for that metric (Plan 13):
    the chip suppresses naturally when the dict does not contain the metric.

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK.

    Returns:
        Dict keyed by CdfMetricId, values are PercentileRow dataclasses.
    """
    result = await session.execute(
        select(
            UserBenchmarkPercentile.metric,
            UserBenchmarkPercentile.value,
            UserBenchmarkPercentile.percentile,
            UserBenchmarkPercentile.cdf_snapshot,
        ).where(UserBenchmarkPercentile.user_id == user_id)
    )
    rows = result.fetchall()
    return {
        row.metric: PercentileRow(
            value=row.value,
            percentile=row.percentile,
            cdf_snapshot=row.cdf_snapshot,
        )
        for row in rows
    }
