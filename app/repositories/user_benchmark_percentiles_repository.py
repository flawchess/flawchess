"""Repository for user_benchmark_percentiles: UPSERT + per-user SELECT.

Phase 94.1 Plan 04 — implements the write/read path for materialised
canonical-slice percentile rows.

Phase 94.1 Plan 13 (gap-closure): ``n_cells_floor`` column dropped.
Row existence implies above-floor — no row is written for below-floor
(user, metric, tc) triples.

Phase 94.4 D-01: composite PK widens to
(user_id, metric, time_control_bucket). ``upsert_percentile`` takes
``time_control_bucket`` as a keyword arg and uses a 3-column index_elements
on the ON CONFLICT clause. ``fetch_for_user`` returns a nested dict
(RESEARCH Pattern 5 Option B): ``dict[CdfMetricId, dict[TimeControlBucket,
PercentileRow]]``.

Phase 94.4 D-08: ``PercentileRow`` gains ``n_games: int`` so the API shaper
(Plan 05c) can compute the game-count-weighted mean of per-TC percentiles
when producing aggregated page-level chips.

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
from app.models.user_rating_anchors import TimeControlBucket
from app.services.global_percentile_cdf import CdfMetricId


@dataclass(frozen=True)
class PercentileRow:
    """Internal dataclass for a single user_benchmark_percentiles row.

    Used by ``fetch_for_user`` to return structured data with attribute access.
    Frozen dataclass (immutable) per CLAUDE.md internal-structured-data rule.

    Row existence implies above-floor (Plan 13): callers need not check
    ``n_cells_floor``; if the row is present, the user passed the floor.

    Phase 94.4 D-08: ``n_games`` is required on this dataclass — the API shaper
    in Plan 05c needs it to compute a game-count-weighted mean of per-TC
    percentiles when surfacing aggregated page-level ΔES chips.
    """

    value: float
    percentile: float | None
    cdf_snapshot: datetime.date
    n_games: int


async def upsert_percentile(
    session: AsyncSession,
    *,
    user_id: int,
    metric: CdfMetricId,
    time_control_bucket: TimeControlBucket,
    value: float,
    n_games: int,
    percentile: float | None,
    cdf_snapshot: datetime.date,
) -> None:
    """Insert or update one (user_id, metric, time_control_bucket) row.

    Uses ``INSERT ... ON CONFLICT (user_id, metric, time_control_bucket) DO
    UPDATE`` so the operation is atomic and idempotent. The caller is
    responsible for committing the session after all writes in a unit of work
    are done.

    Only call this function when ``value`` is not None (i.e., the user is above
    the pooled inclusion floor for the (metric, tc) cell). Below-floor cells
    produce no row — callers must skip the upsert when the per-(metric, tc)
    compute returns None.

    Phase 94.4 D-01: the PK now includes ``time_control_bucket``, so the
    index_elements on the ON CONFLICT clause widens from 2 to 3 columns. A
    single user has at most one row per (metric, tc) cell.

    Phase 94.2 (D-9-amend) / 94.4 D-08: the ``n_games`` parameter is required
    and participates in both the insert values and the on-conflict update so
    refreshed UPSERTs replace the prior count. See
    ``UserBenchmarkPercentile`` class docstring for the per-metric mapping.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Internal user PK.
        metric: One of the 8 CdfMetricId values (Phase 94.4 D-13).
        time_control_bucket: One of bullet/blitz/rapid/classical.
        value: User's pooled metric value (above-floor by construction).
        n_games: Per-(metric, tc) pooled count.
        percentile: Lookup percentile in [0, 100], or None when no cohort
            CDF exists for the user's (metric, tc, anchor) cell.
        cdf_snapshot: Date of the CDF artifact used for interpolation.
    """
    stmt = pg_insert(UserBenchmarkPercentile).values(
        user_id=user_id,
        metric=metric,
        time_control_bucket=time_control_bucket,
        value=value,
        n_games=n_games,
        percentile=percentile,
        cdf_snapshot=cdf_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "metric", "time_control_bucket"],
        set_={
            "value": stmt.excluded.value,
            "n_games": stmt.excluded.n_games,
            "percentile": stmt.excluded.percentile,
            "cdf_snapshot": stmt.excluded.cdf_snapshot,
            "computed_at": func.now(),  # server-side NOW() refresh on every update
        },
    )
    await session.execute(stmt)


async def has_any_rows(session: AsyncSession, *, user_id: int) -> bool:
    """Return True if at least one percentile row exists for the user.

    V4 Information Disclosure mitigation: Caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_active_user.id``); never accept
    ``user_id`` as a query parameter from the client.

    Row existence is the Tier-2 signal for ``GET /imports/readiness``.
    ``computed_at`` is refreshed on every upsert (``func.now()`` in the
    ``on_conflict_do_update`` set), so a row's presence is a post-commit signal
    with no Stage-B race against ``asyncio.create_task(compute_stage_b())``.

    Uses a bounded-count query (``LIMIT 1``) rather than an unbounded scan or a
    Python-side ``len(rows)``, so it exits after finding the first matching row.

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK. Keyword-only to match the
            V4 access-control convention used by ``fetch_for_user``.

    Returns:
        True if any row exists for the user; False otherwise.
    """
    result = await session.execute(
        select(func.count(UserBenchmarkPercentile.user_id))
        .where(UserBenchmarkPercentile.user_id == user_id)
        .limit(1)
    )
    return (result.scalar() or 0) > 0


async def fetch_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]:
    """Return all percentile rows for a user, keyed by (metric, tc).

    V4 Information Disclosure mitigation: Caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_user.id``); never accept
    ``user_id`` as a query parameter from the client.

    Phase 94.4 D-01: return shape is a nested dict per RESEARCH Pattern 5
    Option B — ``result[metric][tc] = PercentileRow``. Missing outer keys
    mean the user has no above-floor cell for that metric on any TC;
    missing inner keys mean the user is below floor (or not yet computed)
    for the (metric, tc) pair specifically. The chip suppresses naturally
    when the nested lookup misses (Plan 13 gap-closure).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK.

    Returns:
        Nested dict keyed first by CdfMetricId, then by TimeControlBucket,
        with PercentileRow dataclasses as values.
    """
    result = await session.execute(
        select(
            UserBenchmarkPercentile.metric,
            UserBenchmarkPercentile.time_control_bucket,
            UserBenchmarkPercentile.value,
            UserBenchmarkPercentile.percentile,
            UserBenchmarkPercentile.cdf_snapshot,
            UserBenchmarkPercentile.n_games,
        ).where(UserBenchmarkPercentile.user_id == user_id)
    )
    rows = result.fetchall()
    out: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {}
    for row in rows:
        out.setdefault(row.metric, {})[row.time_control_bucket] = PercentileRow(
            value=row.value,
            percentile=row.percentile,
            cdf_snapshot=row.cdf_snapshot,
            n_games=row.n_games,
        )
    return out
