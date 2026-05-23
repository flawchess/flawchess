"""Per-user canonical-slice percentile compute service.

Phase 94.1 Plan 05 — PCTL-08 / PCTL-09 / D-03 / D-04 / ROADMAP SC 3.

Two public entry points:

- ``compute_stage_a(user_id)`` — eval-independent; computes ``score_gap``
  from the canonical slice and UPSERTs one row. Hooked by
  ``_complete_import_job`` in ``app/services/import_service.py`` (D-03) via
  ``asyncio.create_task``, AFTER the import transaction commits.

- ``compute_stage_b(user_id)`` — eval-dependent; computes 3 metrics
  (``achievable_score_gap``, ``section2_score_gap_conv``,
  ``section2_score_gap_parity``). Hooked by ``eval_drain.py`` when a user's
  pending-eval count reaches zero (D-01). Same fire-and-forget pattern.

Both stages do NOT run inside the import transaction (ROADMAP success
criterion 3).  Both are non-blocking — exceptions are captured to Sentry and
swallowed (D-04); neither propagates back to the import worker or drain
coroutine.

Pooled-value formula (RESEARCH Open Q2 / Assumption A2):
  ``avg(metric_value)`` across qualifying ``(elo_bucket, tc_bucket)`` cells
  for the user — unweighted cell average.  This matches the benchmark CDF's
  ``percentile_cont`` treatment of per-(user, cell) rows; both consumers pool
  across TCs with no per-TC cap (D-09).

Below-floor convention (CONTEXT.md Claude's Discretion):
  If ``value_raw`` is computable but no ``(elo, tc)`` cell passes the
  inclusion-floor HAVING gate (``n_cells_floor == 0``), we still write the
  row with ``percentile=NULL`` and the computable ``value``.  If
  ``value_raw`` is NULL (zero canonical-slice games for the user), we write
  no row at all.

Stage A / Stage B race-condition non-issue (RESEARCH Pitfall 2):
  The 4 metrics are partitioned between stages: Stage A owns ``score_gap``,
  Stage B owns the other 3.  Each stage writes disjoint ``(user_id, metric)``
  PK rows.  Even when both stages race on a first import, they never conflict.

Security (V5 — T-94.1-10):
  ``user_id`` flows through the query via a SQLAlchemy named bindparam
  (``:user_id``) on a static SQL template.  It is never f-stringed into the
  query string.

Session discipline (CLAUDE.md hard rule):
  Each ``compute_stage_*`` opens its own session via the resolved
  ``session_maker`` factory.  The session is never shared with the trigger
  site (D-04).

``session_maker`` keyword parameter (enables Plan 08 backfill):
  Both entry points accept an optional ``session_maker`` kwarg.  When None,
  they fall back to ``app.core.database.async_session_maker`` (the app DB).
  When provided, they use the injected factory — this lets the backfill
  script target a different DB URL (e.g., prod via the tunnel) without
  mutating module-level state.
"""

from __future__ import annotations

import asyncio
from datetime import date

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker as _default_session_maker
from app.repositories.user_benchmark_percentiles_repository import upsert_percentile
from app.services.canonical_slice_sql import (
    ACHIEVABLE_MIN_GAMES,
    SCORE_GAP_MIN_ENDGAME_N,
    SECTION2_MIN_SPANS_PER_BUCKET,
    per_user_cte_for,
    selected_users_cte,
)
from app.services.global_percentile_cdf import CdfMetricId, interpolate_percentile

# ---------------------------------------------------------------------------
# Module-level constants (CLAUDE.md: no magic numbers; mirrors CONTEXT D-10).
# ---------------------------------------------------------------------------

STAGE_A_METRIC: CdfMetricId = "score_gap"
STAGE_B_METRICS: tuple[CdfMetricId, ...] = (
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
)

# Per-metric inclusion-floor constants, mirrored for the floor-check in each
# Stage entry point.  The HAVING clauses in ``canonical_slice_sql.py`` enforce
# these at the DB level; we re-check the cell count in Python to decide
# whether to set ``percentile=NULL``.
_FLOOR_BY_METRIC: dict[CdfMetricId, int] = {
    "score_gap": SCORE_GAP_MIN_ENDGAME_N,
    "achievable_score_gap": ACHIEVABLE_MIN_GAMES,
    "section2_score_gap_conv": SECTION2_MIN_SPANS_PER_BUCKET,
    "section2_score_gap_parity": SECTION2_MIN_SPANS_PER_BUCKET,
}


# ---------------------------------------------------------------------------
# Internal helper.
# ---------------------------------------------------------------------------


async def _compute_metric_for_user(
    session: AsyncSession,
    user_id: int,
    metric_id: CdfMetricId,
) -> tuple[float | None, int]:
    """Run the canonical-slice CTE for one user and one metric.

    Returns ``(value_raw, n_cells_floor)`` where:

    - ``value_raw``     — ``avg(metric_value)`` across ALL cells regardless of
                          the inclusion floor (``apply_floor=False``).  ``None``
                          when the user has zero canonical-slice games.

    - ``n_cells_floor`` — count of ``(elo_bucket, tc_bucket)`` cells that
                          PASS the per-metric inclusion-floor HAVING gate
                          (``apply_floor=True``).  0 when below floor.

    Two separate SQL executions are used so the raw value is always available
    (for ``percentile=NULL``-but-value-stored semantics) while the floor check
    is cheap (just a COUNT on a much smaller result set).

    Security (V5): ``user_id`` is bound via SQLAlchemy ``.bindparams()``,
    never f-stringed into the query text.
    """
    su_cte = selected_users_cte(source="single_user")

    # Query 1: raw pooled value (no floor gate).
    raw_cte = per_user_cte_for(metric_id, source="single_user", apply_floor=False)
    raw_sql = (
        f"WITH {su_cte},\n{raw_cte}\n"
        f"SELECT avg(metric_value)::float AS value_raw\n"
        f"FROM per_user_values"
    )
    raw_result = await session.execute(text(raw_sql).bindparams(user_id=user_id))
    raw_row = raw_result.fetchone()
    value_raw: float | None = raw_row.value_raw if raw_row is not None else None

    # Query 2: count of floor-passing cells.
    floor_cte = per_user_cte_for(metric_id, source="single_user", apply_floor=True)
    floor_sql = (
        f"WITH {su_cte},\n{floor_cte}\nSELECT count(*)::int AS n_cells_floor\nFROM per_user_values"
    )
    floor_result = await session.execute(text(floor_sql).bindparams(user_id=user_id))
    floor_row = floor_result.fetchone()
    n_cells_floor: int = (floor_row.n_cells_floor or 0) if floor_row is not None else 0

    return value_raw, n_cells_floor


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------


async def compute_stage_a(
    user_id: int,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Compute and UPSERT the ``score_gap`` percentile for one user.

    Background task — never propagates exceptions back to the trigger site
    (D-04 / ROADMAP SC-3).  Called by ``_complete_import_job`` via
    ``asyncio.create_task`` after the import transaction commits.

    Floor convention: if ``n_cells_floor == 0`` (below inclusion floor) but
    the raw value is computable, the row is written with ``percentile=NULL``.
    If ``value_raw is None`` (zero canonical-slice games), no row is written.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            value, n_cells_floor = await _compute_metric_for_user(session, user_id, STAGE_A_METRIC)
            # Always call interpolate_percentile when we have a value, even for
            # below-floor users.  This lets callers (and tests) override it via
            # mock patching, and keeps the code path uniform.
            # If value is None (zero canonical-slice games): no row, early exit.
            if value is None:
                return
            percentile: float | None = interpolate_percentile(STAGE_A_METRIC, value)
            if n_cells_floor == 0:
                # Below inclusion floor: store value but suppress the chip
                # (D-10 / CONTEXT Claude's Discretion).
                percentile = None
            await upsert_percentile(
                session,
                user_id=user_id,
                metric=STAGE_A_METRIC,
                value=value,
                percentile=percentile,
                n_cells_floor=n_cells_floor,
                cdf_snapshot=date.today(),
            )
            await session.commit()
    except asyncio.CancelledError:
        raise  # lifespan shutdown contract (eval_drain.py:550-554)
    except Exception as exc:
        # CLAUDE.md Backend Rules: variables via set_context, NEVER in message.
        sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": "A"})
        sentry_sdk.capture_exception(exc)
        # Do NOT re-raise — Stage A errors must not propagate to import worker.


async def compute_stage_b(
    user_id: int,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Compute and UPSERT the 3 eval-dependent percentiles for one user.

    Background task — never propagates exceptions (D-04 / ROADMAP SC-3).
    Called by ``eval_drain.py`` via ``asyncio.create_task`` once the user's
    pending-eval count reaches zero (D-01).

    A single session is opened for all 3 metrics (halves session-open overhead
    vs per-metric sessions).  Per-metric errors are isolated: an inner
    try/except wraps each metric's compute + UPSERT so a failure in one metric
    does not prevent the others from being written.  All 3 are committed in one
    ``session.commit()`` at the end; if an individual metric fails its inner
    try/except catches and reports it to Sentry, and the loop continues.

    Stage A / Stage B race: the 4 metrics are disjoint across the two stages,
    so concurrent UPSERTs for the same user never collide (RESEARCH Pitfall 2).
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            for metric_id in STAGE_B_METRICS:
                try:
                    value, n_cells_floor = await _compute_metric_for_user(
                        session, user_id, metric_id
                    )
                    if value is None:
                        # Zero canonical-slice games for this metric → no row.
                        continue
                    percentile: float | None = interpolate_percentile(metric_id, value)
                    if n_cells_floor == 0:
                        percentile = None
                    await upsert_percentile(
                        session,
                        user_id=user_id,
                        metric=metric_id,
                        value=value,
                        percentile=percentile,
                        n_cells_floor=n_cells_floor,
                        cdf_snapshot=date.today(),
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Per-metric capture: other metrics continue (plan spec).
                    sentry_sdk.set_context(
                        "percentile_compute",
                        {"user_id": user_id, "stage": "B", "metric": metric_id},
                    )
                    sentry_sdk.capture_exception(exc)
            await session.commit()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Top-level capture for session-open or commit failures.
        sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": "B"})
        sentry_sdk.capture_exception(exc)
