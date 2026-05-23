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

Floor convention (Plan 13 gap-closure):
  ``_compute_metric_for_user`` uses a single CTE query with ``apply_floor=True``.
  If the user has zero floor-passing cells, the CTE returns no rows → the
  function returns ``None``. The caller skips the upsert entirely, so no row is
  written. Row absence is the new below-floor signal — the chip suppresses
  naturally. The dual-query / dual-floor approach from Plans 05-12 is removed.

  Correctness bug fixed (Plan 13): the prior implementation ran two queries —
  one with ``apply_floor=False`` for ``value_raw`` and one with
  ``apply_floor=True`` for ``n_cells_floor``. The stored ``value`` was the
  unfiltered average, meaning tiny below-floor cells (n=1, n=3) dragged the
  value far from the floor-passing signal. User 28's ``achievable_score_gap``
  reported Top 6% when the floor-respecting value indicated Top 71%.

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


# ---------------------------------------------------------------------------
# Internal helper.
# ---------------------------------------------------------------------------


async def _compute_metric_for_user(
    session: AsyncSession,
    user_id: int,
    metric_id: CdfMetricId,
) -> float | None:
    """Run the canonical-slice CTE for one user and one metric.

    Uses a single SQL query with ``apply_floor=True``. Only floor-passing
    ``(elo_bucket, tc_bucket)`` cells contribute to the returned value.

    Returns the floor-respecting ``avg(metric_value)`` across the user's
    floor-passing cells, or ``None`` if the user has zero floor-passing cells
    for this metric (CTE returns no rows).

    Plan 13 correctness fix: the prior dual-query approach averaged ALL cells
    (including tiny n=1, n=3 below-floor cells) into ``value``, while the
    benchmark CDF was built from floor-passing cells only. This caused user 28's
    ``achievable_score_gap`` to read Top 6% when the floor-respecting value
    indicated Top 71% (+0.1204 raw vs -0.0322 floor-respecting). Using a single
    ``apply_floor=True`` query ensures the stored value matches the CDF input.

    Security (V5): ``user_id`` is bound via SQLAlchemy ``.bindparams()``,
    never f-stringed into the query text.
    """
    su_cte = selected_users_cte(source="single_user")
    floor_cte = per_user_cte_for(metric_id, source="single_user", apply_floor=True)
    sql = (
        f"WITH {su_cte},\n{floor_cte}\n"
        f"SELECT avg(metric_value)::float AS value\n"
        f"FROM per_user_values"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
    row = result.fetchone()
    if row is None or row.value is None:
        return None
    return float(row.value)


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

    Floor convention (Plan 13): if ``_compute_metric_for_user`` returns None
    (zero floor-passing cells), no row is written. The chip suppresses naturally.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            value = await _compute_metric_for_user(session, user_id, STAGE_A_METRIC)
            # If value is None (zero floor-passing cells): no row, early exit.
            if value is None:
                return
            percentile: float | None = interpolate_percentile(STAGE_A_METRIC, value)
            await upsert_percentile(
                session,
                user_id=user_id,
                metric=STAGE_A_METRIC,
                value=value,
                percentile=percentile,
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
    pending-eval count reaches zero AND no active import is in progress (D-01 /
    Plan 13 Stage B gate — see ``users_with_zero_pending`` in game_repository.py).

    A single session is opened for all 3 metrics (halves session-open overhead
    vs per-metric sessions).  Per-metric errors are isolated: an inner
    try/except wraps each metric's compute + UPSERT so a failure in one metric
    does not prevent the others from being written.  All 3 are committed in one
    ``session.commit()`` at the end; if an individual metric fails its inner
    try/except catches and reports it to Sentry, and the loop continues.

    Floor convention (Plan 13): if ``_compute_metric_for_user`` returns None
    for a metric, no row is written for that metric. The loop simply continues
    to the next metric.

    Stage A / Stage B race: the 4 metrics are disjoint across the two stages,
    so concurrent UPSERTs for the same user never collide (RESEARCH Pitfall 2).
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            for metric_id in STAGE_B_METRICS:
                try:
                    value = await _compute_metric_for_user(session, user_id, metric_id)
                    if value is None:
                        # Zero floor-passing cells for this metric → no row.
                        continue
                    percentile: float | None = interpolate_percentile(metric_id, value)
                    await upsert_percentile(
                        session,
                        user_id=user_id,
                        metric=metric_id,
                        value=value,
                        percentile=percentile,
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
