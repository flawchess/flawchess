"""Per-user pooled percentile compute service.

Phase 94.2 (supersedes Phase 94.1 Plan 13): the per-user compute consumes
the pooled-per-user CTE from ``app/services/canonical_slice_sql.py``. Each
``(user_id, metric_id)`` lookup runs a single SQL query that emits either
one row (``metric_value``, ``n_games``) or zero rows (user below the ≥30
floor on the pooled set). The Plan 13 dual-query / dual-floor mechanism and
the ``apply_floor`` argument are gone — no cells, no averaging.

The compute helper returns ``tuple[float, int] | None``; Stage A/B
destructure ``(value, n_games)`` and pass both to ``upsert_percentile`` per
D-9-amend.

Stage A/B trigger contract preserved verbatim from 94.1 (PCTL-09):

- ``compute_stage_a(user_id)`` — eval-independent; computes ``score_gap``
  from the pooled per-user CTE and UPSERTs one row. Hooked by
  ``_complete_import_job`` in ``app/services/import_service.py`` (D-03) via
  ``asyncio.create_task``, AFTER the import transaction commits.

- ``compute_stage_b(user_id)`` — eval-dependent; computes 3 metrics
  (``achievable_score_gap``, ``section2_score_gap_conv``,
  ``section2_score_gap_parity``). Hooked by ``eval_drain.py`` when a user's
  pending-eval count reaches zero (D-01). Same fire-and-forget pattern.

Both stages do NOT run inside the import transaction (ROADMAP success
criterion 3). Both are non-blocking — exceptions are captured to Sentry and
swallowed (D-04); neither propagates back to the import worker or drain
coroutine.

Stage A / Stage B race-condition non-issue (RESEARCH Pitfall 2):
  The 4 metrics are partitioned between stages: Stage A owns ``score_gap``,
  Stage B owns the other 3. Each stage writes disjoint ``(user_id, metric)``
  PK rows. Even when both stages race on a first import, they never conflict.

Security (V5 — T-94.2-03-01):
  ``user_id`` flows through the query via a SQLAlchemy named bindparam
  (``:user_id``) on a static SQL template. It is never f-stringed into the
  query string.

Session discipline (CLAUDE.md hard rule):
  Each ``compute_stage_*`` opens its own session via the resolved
  ``session_maker`` factory. The session is never shared with the trigger
  site (D-04).

``session_maker`` keyword parameter (enables Plan 06 backfill):
  Both entry points accept an optional ``session_maker`` kwarg. When None,
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

# TODO Plan 05 (94.4-05): cut over to interpolate_cohort_percentile + per-TC
# STAGE_B_METRIC_FAMILIES (8-value CdfMetricId × outer-key TC). Plan 04
# (94.4-04) collapsed CdfMetricId from 16 → 8 (CONTEXT D-13), so the old
# TC-suffixed entries below are no longer members of CdfMetricId. They are
# typed ``str`` here as a transient stub until Plan 05 finishes the cutover.
STAGE_A_METRIC: CdfMetricId = "score_gap"
STAGE_B_METRICS: tuple[str, ...] = (
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    # Phase 94.3 per-(metric × TC) time-pressure additions (CONTEXT.md D-7/D-10).
    # All 12 cells compute in Stage B (post-cold-drain): Time Pressure Score Gap
    # and Clock Gap both depend on Stockfish-eval-derived endgame-entry detection;
    # Net Flag Rate is outcome-only and could be Stage A, but bundles with Stage B
    # to avoid a special-case hook. Order mirrors the IN_SCOPE_METRICS tuple in
    # scripts/gen_global_percentile_cdf.py and the benchmark_metric ENUM (post
    # 20260524_170733 migration).
    "time_pressure_score_gap_bullet",
    "time_pressure_score_gap_blitz",
    "time_pressure_score_gap_rapid",
    "time_pressure_score_gap_classical",
    "clock_gap_bullet",
    "clock_gap_blitz",
    "clock_gap_rapid",
    "clock_gap_classical",
    "net_flag_rate_bullet",
    "net_flag_rate_blitz",
    "net_flag_rate_rapid",
    "net_flag_rate_classical",
)


# ---------------------------------------------------------------------------
# Internal helper.
# ---------------------------------------------------------------------------


async def _compute_metric_for_user(
    session: AsyncSession,
    user_id: int,
    metric_id: CdfMetricId,
) -> tuple[float, int] | None:
    """Run the pooled-per-user CTE for one user and one metric (Phase 94.2).

    Returns ``(metric_value, n_games)`` from the single row of
    ``per_user_values``, or ``None`` if the user is below the metric's ≥30
    inclusion floor (the CTE's HAVING clause emits no row).

    Phase 94.2 supersedes the 94.1 Plan 13 single-query-with-``apply_floor=True``
    path: under the pooled model there are no per-(elo_bucket, tc_bucket) cells
    to average, so the prior ``avg(metric_value)`` wrapper is gone. One row
    per user → SELECT (value, n_games) directly.

    Return-type widening to ``tuple[float, int] | None`` (from 94.1's
    ``float | None``) is per CONTEXT.md Amendment 2026-05-24 (D-9-amend):
    ``n_games`` is re-added to the storage table and must thread from the CTE
    to the UPSERT.

    Security (V5): ``user_id`` is bound via SQLAlchemy ``.bindparams()``,
    never f-stringed into the query text.
    """
    su_cte = selected_users_cte(source="single_user")
    pooled_cte = per_user_cte_for(metric_id, source="single_user", snapshot_date=None)
    sql = (
        f"WITH {su_cte},\n{pooled_cte}\n"
        f"SELECT metric_value::float AS value, n_games::int AS n_games\n"
        f"FROM per_user_values\n"
        f"LIMIT 1"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
    row = result.fetchone()
    if row is None or row.value is None or row.n_games is None:
        return None
    return (float(row.value), int(row.n_games))


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
    (D-04 / ROADMAP SC-3). Called by ``_complete_import_job`` via
    ``asyncio.create_task`` after the import transaction commits.

    Floor convention (Phase 94.2): if ``_compute_metric_for_user`` returns
    None (user below ≥30 pooled floor), no row is written. The chip
    suppresses naturally.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            result = await _compute_metric_for_user(session, user_id, STAGE_A_METRIC)
            # If result is None (below pooled floor): no row, early exit.
            if result is None:
                return
            value, n_games = result
            percentile: float | None = interpolate_percentile(STAGE_A_METRIC, value)
            await upsert_percentile(
                session,
                user_id=user_id,
                metric=STAGE_A_METRIC,
                value=value,
                n_games=n_games,
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
    vs per-metric sessions). Per-metric errors are isolated: an inner
    try/except wraps each metric's compute + UPSERT so a failure in one metric
    does not prevent the others from being written. All 3 are committed in one
    ``session.commit()`` at the end; if an individual metric fails its inner
    try/except catches and reports it to Sentry, and the loop continues.

    Floor convention (Phase 94.2): if ``_compute_metric_for_user`` returns
    None for a metric, no row is written for that metric. The loop simply
    continues to the next metric.

    Stage A / Stage B race: the 4 metrics are disjoint across the two stages,
    so concurrent UPSERTs for the same user never collide (RESEARCH Pitfall 2).
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            for metric_id_raw in STAGE_B_METRICS:
                # TODO Plan 05 (94.4-05): cut over to interpolate_cohort_percentile +
                # per-TC STAGE_B_METRIC_FAMILIES. CdfMetricId collapsed 16 → 8 in
                # Plan 04, so the legacy TC-suffixed names in STAGE_B_METRICS are
                # not members of the new Literal — cast through CdfMetricId here
                # as a transient stub so the loop compiles. Plan 05 replaces
                # this entire loop with the per-(family × TC) iteration.
                metric_id: CdfMetricId = metric_id_raw  # ty: ignore[invalid-assignment]
                try:
                    result = await _compute_metric_for_user(session, user_id, metric_id)
                    if result is None:
                        # Below pooled floor for this metric → no row.
                        continue
                    value, n_games = result
                    percentile: float | None = interpolate_percentile(metric_id, value)
                    await upsert_percentile(
                        session,
                        user_id=user_id,
                        metric=metric_id,
                        value=value,
                        n_games=n_games,
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
