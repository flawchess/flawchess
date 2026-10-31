"""Repository for user_benchmark_percentiles: UPSERT + per-user SELECT.

Implements the write/read path for materialised
canonical-slice percentile rows.

The PK is (user_id, metric, time_control_bucket, color); a row exists only for
above-floor cells, so no row is written for below-floor (user, metric, tc[, colour])
triples. ``upsert_percentile`` takes ``time_control_bucket`` as a keyword arg and an
optional ``color`` (default ``'all'``, the colour-agnostic Endgames rows) and uses a
4-column index_elements on the ON CONFLICT clause.
``fetch_for_user`` returns a nested dict:
``dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]`` over the ``'all'`` rows
only, so the Endgames read shape is unchanged by the per-colour opening rows.

``PercentileRow`` carries ``n_games: int`` so the API shaper can compute the
game-count-weighted mean of per-TC percentiles when producing aggregated
page-level chips.

V4 Information Disclosure mitigation: ``fetch_for_user`` requires ``user_id``
as a keyword argument. Callers pass ``current_user.id`` from the FastAPI-Users
dependency. Never accept ``user_id`` as a query parameter.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.user_benchmark_percentile import PercentileColor, UserBenchmarkPercentile
from app.models.user_rating_anchors import TimeControlBucket
from app.schemas.normalization import Color
from app.services.global_percentile_cdf import OPENING_OUT_METRICS, CdfMetricId, OpeningOutMetricId


@dataclass(frozen=True)
class PercentileRow:
    """Internal dataclass for a single user_benchmark_percentiles row.

    Used by ``fetch_for_user`` to return structured data with attribute access.
    Frozen dataclass (immutable) per CLAUDE.md internal-structured-data rule.

    Row existence implies above-floor: if the row is present, the user passed
    the floor.

    ``n_games`` is required on this dataclass — the API shaper needs it to
    compute a game-count-weighted mean of per-TC percentiles when surfacing
    aggregated page-level ΔES chips.
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
    color: PercentileColor = "all",
) -> None:
    """Insert or update one (user_id, metric, time_control_bucket, color) row.

    Uses ``INSERT ... ON CONFLICT (user_id, metric, time_control_bucket, color) DO
    UPDATE`` so the operation is atomic and idempotent. The caller is
    responsible for committing the session after all writes in a unit of work
    are done.

    Only call this function when ``value`` is not None (i.e., the user is above
    the pooled inclusion floor for the (metric, tc) cell). Below-floor cells
    produce no row — callers must skip the upsert when the per-(metric, tc)
    compute returns None.

    The PK includes ``time_control_bucket`` and ``color``, so the index_elements on
    the ON CONFLICT clause has 4 columns (a narrower target would match no unique
    constraint and fail every write). A single user has at most one row per
    (metric, tc, colour) cell; Endgames rows use the default ``'all'`` colour.

    The ``n_games`` parameter is required
    and participates in both the insert values and the on-conflict update so
    refreshed UPSERTs replace the prior count. See
    ``UserBenchmarkPercentile`` class docstring for the per-metric mapping.

    Args:
        session: AsyncSession. Caller commits.
        user_id: Internal user PK.
        metric: A CdfMetricId value.
        time_control_bucket: One of bullet/blitz/rapid/classical.
        value: User's pooled metric value (above-floor by construction).
        n_games: Per-(metric, tc) pooled count.
        percentile: Lookup percentile in [0, 100], or None when no cohort
            CDF exists for the user's (metric, tc, anchor) cell.
        cdf_snapshot: Date of the CDF artifact used for interpolation.
        color: ``'all'`` (default) for colour-agnostic rows, ``'white'`` /
            ``'black'`` for the per-colour opening rows.
    """
    stmt = pg_insert(UserBenchmarkPercentile).values(
        user_id=user_id,
        metric=metric,
        time_control_bucket=time_control_bucket,
        color=color,
        value=value,
        n_games=n_games,
        percentile=percentile,
        cdf_snapshot=cdf_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "metric", "time_control_bucket", "color"],
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
    """Return all colour-agnostic percentile rows for a user, keyed by (metric, tc).

    V4 Information Disclosure mitigation: Caller MUST pass the authenticated
    user's ID (from FastAPI-Users dep ``current_user.id``); never accept
    ``user_id`` as a query parameter from the client.

    The return shape is a nested dict — ``result[metric][tc] = PercentileRow``.
    Missing outer keys mean the user has no above-floor cell for that metric on
    any TC; missing inner keys mean the user is below floor (or not yet
    computed) for the (metric, tc) pair specifically. The chip suppresses
    naturally when the nested lookup misses.

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
        )
        .where(UserBenchmarkPercentile.user_id == user_id)
        # Colour-agnostic rows only: the per-colour opening rows (Phase 243) share
        # (metric, tc) keys with nothing here, but must never leak into the Endgames
        # shape, which has one PercentileRow per (metric, tc).
        .where(UserBenchmarkPercentile.color == "all")
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


async def fetch_opening_out_rows(
    session: AsyncSession,
    *,
    user_id: int,
) -> dict[tuple[OpeningOutMetricId, TimeControlBucket, Color], PercentileRow]:
    """Return the user's per-colour opening worse/better rows keyed (metric, tc, colour).

    Only ``'white'`` / ``'black'`` rows of the opening metrics: the colour-agnostic
    ``'all'`` rows (Endgames) are excluded, as is every other metric.

    V4 Information Disclosure mitigation: Caller MUST pass the authenticated user's
    ID (from FastAPI-Users dep ``current_user.id``); never accept ``user_id`` as a
    query parameter from the client.
    """
    result = await session.execute(
        select(
            UserBenchmarkPercentile.metric,
            UserBenchmarkPercentile.time_control_bucket,
            UserBenchmarkPercentile.color,
            UserBenchmarkPercentile.value,
            UserBenchmarkPercentile.percentile,
            UserBenchmarkPercentile.cdf_snapshot,
            UserBenchmarkPercentile.n_games,
        )
        .where(UserBenchmarkPercentile.user_id == user_id)
        .where(UserBenchmarkPercentile.color.in_(("white", "black")))
        .where(UserBenchmarkPercentile.metric.in_(OPENING_OUT_METRICS))
    )
    out: dict[tuple[OpeningOutMetricId, TimeControlBucket, Color], PercentileRow] = {}
    for row in result.fetchall():
        color: Color = "white" if row.color == "white" else "black"
        metric: OpeningOutMetricId = (
            "opening_worse_rate" if row.metric == "opening_worse_rate" else "opening_better_rate"
        )
        out[(metric, row.time_control_bucket, color)] = PercentileRow(
            value=row.value,
            percentile=row.percentile,
            cdf_snapshot=row.cdf_snapshot,
            n_games=row.n_games,
        )
    return out
