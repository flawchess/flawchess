"""Per-user pooled percentile compute service.

Consumes the cohort CDF (``benchmark_cohort_cdf`` via ``load_cohort_cells`` +
``interpolate_cohort_percentile``) and the per-(user, TC) median rating
anchor (``user_rating_anchors``). Stage B iterates ``STAGE_B_METRIC_FAMILIES``
× the user's above-floor TCs.

Stage A (eval-independent — wired into import completion):

  1. Compute and UPSERT per-(user, TC) median rating anchors via the
     ``compute_anchors_for_user`` helper. Anchors come FIRST so the per-TC
     ``score_gap`` percentile lookup can read the anchor's ``anchor_rating``.
  2. Issue ONE batched ``load_cohort_cells`` prefetch for all (anchor, TC)
     pairs, then resolve from the in-memory dict.
  3. For each TC, interpolate against the cohort CDF and UPSERT one
     ``user_benchmark_percentiles(user_id, metric, time_control_bucket)``
     row.

Stage B (eval-dependent — wired into the eval drain): for each
metric family in ``STAGE_B_METRIC_FAMILIES`` × each TC with an above-floor
anchor, dispatch to the matching per-TC builder, interpolate against the
cohort CDF, and UPSERT one row per (family, tc).

Game-weighted blended anchor:

  ``compute_anchors_for_user`` implements the blended anchor. Per-game
  conversion is done SQL-side via the ``chesscom_conversion_lookup`` VALUES
  CTE in ``per_user_cte_median_anchor(blend=True)``:

  - chess.com (non-Daily) games: converted per-game to lichess-equivalent
    via the nearest anchor of the composed native-TC grid
    (``canonical_slice_sql._chesscom_conversion_values_sql``).
  - Lichess games: pass through native rating unchanged.
  - The per-user median of the combined pool is the blended anchor.
  - Per-platform game counts and native medians are persisted alongside
    the blended anchor for tooltip disclosure.
  - Suppression rule: skip TC if pooled count < MEDIAN_ANCHOR_MIN_GAMES.

Both stages are non-blocking — exceptions are captured to Sentry and
swallowed; neither propagates back to the import worker or drain
coroutine.

Sentry pattern (CLAUDE.md Backend Rules):
  Variables flow into ``sentry_sdk.set_context("percentile_compute",
  {...})`` (user_id, stage, metric, tc) BEFORE
  ``sentry_sdk.capture_exception(exc)``. No variables in error messages —
  preserves Sentry issue grouping per CLAUDE.md.

Security:
  ``user_id`` flows through every CTE via the SQLAlchemy named bindparam
  ``:user_id`` on static SQL templates (no f-stringed user input).

Session discipline (CLAUDE.md hard rule):
  Each ``compute_stage_*`` opens its own session via the resolved
  ``session_maker`` factory. The session is never shared with the trigger
  site.

``session_maker`` keyword parameter:
  Both entry points accept an optional ``session_maker`` kwarg. When
  None, they fall back to ``app.core.database.async_session_maker``.
  When provided, they use the injected factory — this lets the backfill
  script target a different DB URL without mutating module-level state.

Stage A / Stage B race-condition non-issue:
  Stage A owns ``(score_gap, *)`` percentile rows + ALL anchor rows.
  Stage B owns the other 10 metric families (``STAGE_B_METRIC_FAMILIES``)
  × {bullet, blitz, rapid, classical}. The PK is
  ``(user_id, metric, time_control_bucket)`` so disjoint writes never
  collide.
"""

from __future__ import annotations

import asyncio
import itertools
from datetime import UTC, datetime
from typing import Literal

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker as _default_session_maker
from app.services import percentile_compute_registry
from app.models.user_rating_anchors import TimeControlBucket
from app.repositories.user_benchmark_percentiles_repository import upsert_percentile
from app.repositories.user_rating_anchors_repository import (
    RatingAnchorRow,
    fetch_anchors_for_user,
    upsert_anchor,
)
from app.services.canonical_slice_sql import (
    MEDIAN_ANCHOR_MIN_GAMES,
    per_user_cte_achievable_tc,
    per_user_cte_clock_gap,
    per_user_cte_conv_rate_tc,
    per_user_cte_median_anchor,
    per_user_cte_net_flag_rate,
    per_user_cte_parity_rate_tc,
    per_user_cte_recovery_rate_tc,
    per_user_cte_score_gap_tc,
    per_user_cte_score_gap_bucket_tc,
    per_user_cte_time_pressure_score_gap,
    selected_users_cte,
)
from app.repositories.benchmark_cohort_cdf_repository import load_cohort_cells
from app.services.global_percentile_cdf import (
    CdfMetricId,
    CdfTable,
    round_anchor_to_grid,
    interpolate_cohort_percentile,
)

# ---------------------------------------------------------------------------
# Module-level constants (CLAUDE.md: no magic numbers).
# ---------------------------------------------------------------------------

# Sweep order — canonical bullet → blitz → rapid → classical. Matches
# ``ALL_TIME_CONTROLS`` in ``scripts/gen_global_percentile_cdf.py`` so two
# sides of the percentile pipeline iterate TCs in identical order.
_ALL_TIME_CONTROLS: tuple[TimeControlBucket, ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)


# Stage A metric — eval-independent, runs at import-completion time.
STAGE_A_METRIC: CdfMetricId = "score_gap"

# Stage B metric families (10-tuple) — eval-dependent, runs once the user's
# pending evals reach zero. Each family is computed per the user's
# above-floor TCs. TC is an outer key of the benchmark_cohort_cdf table,
# not part of the metric name.
STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = (
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
)


# Bounds how many compute_stage_a/compute_stage_b bodies can hold a DB
# connection from the 10+10 pool at once. The measured mean query time for
# one compute is 1,111.7ms — under a burst of import completions (or an
# eval-drain batch crossing many users to zero-pending at once) an
# unbounded fan-out could hold a large share of the pool in these
# queries alone. 2 keeps that worst case to at most 2 of 20 connections.
PERCENTILE_COMPUTE_LIMIT = 2

# Lazy-initialized (module import time predates the event loop starting;
# constructing an asyncio.Semaphore before a running loop exists raises on
# some Python versions). Mirrors app/core/rate_limiters.py's shape.
_percentile_semaphore: asyncio.Semaphore | None = None


def get_percentile_semaphore() -> asyncio.Semaphore:
    """Return the shared percentile-compute concurrency semaphore (lazy init).

    Acquired INSIDE compute_stage_a and compute_stage_b (not at their
    asyncio.create_task call sites) because compute_stage_b has two
    independent trigger sites — app/services/import_service.py's
    import-completion path and app/services/eval_drain.py's zero-pending
    crossing — and only an in-function acquisition covers
    both by construction.
    """
    global _percentile_semaphore
    if _percentile_semaphore is None:
        _percentile_semaphore = asyncio.Semaphore(PERCENTILE_COMPUTE_LIMIT)
    return _percentile_semaphore


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _per_user_cte_for_family_and_tc(
    family: CdfMetricId,
    tc: TimeControlBucket,
) -> str:
    """Dispatch to the per-TC ``per_user_values`` CTE builder for one family.

    Mirrors ``scripts/gen_global_percentile_cdf.py::_per_user_cte_for_metric_and_tc``
    so the benchmark-side and single-user-side compute consume byte-identical
    SQL pooled bodies (source-mode parity). The dispatch covers all 11
    CdfMetricId values; Stage A passes ``family='score_gap'`` and Stage B
    passes one of the other 10 families.
    """
    if family == "score_gap":
        return per_user_cte_score_gap_tc(tc, source="single_user", snapshot_date=None)
    if family == "achievable_score_gap":
        return per_user_cte_achievable_tc(tc, source="single_user", snapshot_date=None)
    if family == "score_gap_conv":
        return per_user_cte_score_gap_bucket_tc(
            tc, source="single_user", snapshot_date=None, bucket_label="conversion"
        )
    if family == "score_gap_parity":
        return per_user_cte_score_gap_bucket_tc(
            tc, source="single_user", snapshot_date=None, bucket_label="parity"
        )
    if family == "recovery_score_gap":
        return per_user_cte_score_gap_bucket_tc(
            tc, source="single_user", snapshot_date=None, bucket_label="recovery"
        )
    if family == "time_pressure_score_gap":
        return per_user_cte_time_pressure_score_gap(tc, source="single_user", snapshot_date=None)
    if family == "clock_gap":
        return per_user_cte_clock_gap(tc, source="single_user", snapshot_date=None)
    if family == "net_flag_rate":
        return per_user_cte_net_flag_rate(tc, source="single_user", snapshot_date=None)
    # Raw-rate families (conversion/parity/recovery) — dispatch to
    # the shared builders from canonical_slice_sql so CDF construction and
    # per-user lookup share one code path (drift-proof).
    if family == "conversion_rate":
        return per_user_cte_conv_rate_tc(tc, source="single_user", snapshot_date=None)
    if family == "parity_rate":
        return per_user_cte_parity_rate_tc(tc, source="single_user", snapshot_date=None)
    if family == "recovery_rate":
        return per_user_cte_recovery_rate_tc(tc, source="single_user", snapshot_date=None)
    # Defensive — the CdfMetricId Literal closes the value set; an unhandled
    # branch indicates a missed dispatcher arm rather than user input.
    raise ValueError(f"Unknown CdfMetricId for per-TC dispatch: {family!r}")


async def _compute_metric_for_user_per_tc(
    session: AsyncSession,
    user_id: int,
    family: CdfMetricId,
    tc: TimeControlBucket,
) -> tuple[float, int] | None:
    """Run the per-TC pooled CTE for one user, one metric family, one TC.

    Returns ``(metric_value, n_games)`` from the single row of
    ``per_user_values``, or ``None`` if the user is below the metric's
    per-TC ≥30 inclusion floor (the CTE's HAVING clause emits no row).

    The metric-family-to-builder dispatch is delegated to
    ``_per_user_cte_for_family_and_tc``; this function only handles the
    SQL composition (selected_users_cte + per_user_values block) and row
    materialisation. ``user_id`` is bound via ``.bindparams()``; never
    f-stringed.
    """
    su_cte = selected_users_cte(source="single_user")
    pooled_cte = _per_user_cte_for_family_and_tc(family, tc)
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
# compute_anchors_for_user — blended anchor.
# ---------------------------------------------------------------------------


async def compute_anchors_for_user(
    session: AsyncSession,
    user_id: int,
) -> dict[TimeControlBucket, RatingAnchorRow]:
    """Compute per-(user, TC) blended anchors and UPSERT them.

    Per-game conversion + pooled median: chess.com (non-Daily) games
    convert via the composed native-TC grid to lichess-equivalent; lichess
    games pass through native; the per-user median of the pooled set is the
    anchor. Per-platform game counts and native medians are emitted
    alongside for tooltip composition disclosure (rendered by the
    RankedMetricPopover anchor disclosure).

    Suppression rule: if the pooled count (n_chesscom_games +
    n_lichess_games) < MEDIAN_ANCHOR_MIN_GAMES for a TC, no anchor row is
    produced for that TC and the chip suppresses naturally.

    Sentry pattern (CLAUDE.md):
      Per-TC exceptions trip an inner try/except; ``set_context`` carries
      ``user_id``, ``stage='anchor'``, ``tc`` BEFORE ``capture_exception``.
      No variables in error messages (CLAUDE.md Backend Rules).
    """
    anchors: dict[TimeControlBucket, RatingAnchorRow] = {}
    for tc in _ALL_TIME_CONTROLS:
        try:
            su_cte = selected_users_cte(source="single_user")
            anchor_cte = per_user_cte_median_anchor(
                tc,
                source="single_user",
                snapshot_date=None,
                blend=True,
                min_games=MEDIAN_ANCHOR_MIN_GAMES,
            )
            sql = (
                f"WITH {su_cte},\n{anchor_cte}\n"
                f"SELECT anchor_rating::int AS anchor_rating, "
                f"n_chesscom_games::int AS n_chesscom_games, "
                f"n_lichess_games::int AS n_lichess_games, "
                f"chesscom_median_native AS chesscom_median_native, "
                f"lichess_median_native AS lichess_median_native "
                f"FROM per_user_anchor LIMIT 1"
            )
            result = await session.execute(text(sql).bindparams(user_id=user_id))
            row = result.fetchone()
            if row is None or row.anchor_rating is None:
                # Below MEDIAN_ANCHOR_MIN_GAMES on the pooled count, OR
                # the user has zero non-Daily games — chip suppresses
                # for that (user, TC).
                continue
            chesscom_median = (
                int(row.chesscom_median_native) if row.chesscom_median_native is not None else None
            )
            lichess_median = (
                int(row.lichess_median_native) if row.lichess_median_native is not None else None
            )
            await upsert_anchor(
                session,
                user_id=user_id,
                time_control_bucket=tc,
                anchor_rating=int(row.anchor_rating),
                n_chesscom_games=int(row.n_chesscom_games),
                n_lichess_games=int(row.n_lichess_games),
                chesscom_median_native=chesscom_median,
                lichess_median_native=lichess_median,
            )
            anchors[tc] = RatingAnchorRow(
                anchor_rating=int(row.anchor_rating),
                n_chesscom_games=int(row.n_chesscom_games),
                n_lichess_games=int(row.n_lichess_games),
                chesscom_median_native=chesscom_median,
                lichess_median_native=lichess_median,
            )
        except asyncio.CancelledError:
            raise  # lifespan shutdown contract
        except Exception as exc:
            # Per-TC capture: other TCs keep computing.
            sentry_sdk.set_context(
                "percentile_compute",
                {"user_id": user_id, "stage": "anchor", "tc": tc},
            )
            sentry_sdk.capture_exception(exc)
    return anchors


async def is_below_anchor_floor(
    session: AsyncSession,
    user_id: int,
    *,
    total_games: int,
) -> bool:
    """Return True iff the user qualifies for NO per-TC anchor in ANY time control.

    Such a user can never produce ``user_benchmark_percentiles`` rows: both
    ``compute_stage_a`` and ``compute_stage_b`` iterate the user's above-floor
    anchors, and with zero anchors both are deterministic no-ops. The readiness
    gate uses this to distinguish "wrote nothing because below floor (compute is
    done)" from "compute has not run yet", so below-floor users are not locked
    out of the endgames page forever.

    Bug context: prod user 145 imported 13 chess.com games (all
    below the 30-game floor), so Stage A/B wrote no anchors and no percentile
    rows. ``has_any_rows`` stayed False, so ``GET /imports/readiness`` kept
    ``tier2=False`` and the endgames page stayed on the "Analyzing endgames"
    screen permanently even though Stockfish was done.

    Consistency: this probe runs the SAME blended-anchor candidate SQL
    (``per_user_cte_median_anchor(blend=True)`` with the same ``min_games``)
    that ``compute_anchors_for_user`` uses to decide whether to write an anchor
    row, so the two can never disagree about floor status. Read-only — no UPSERT.

    Cheap short-circuit: a user with fewer than ``MEDIAN_ANCHOR_MIN_GAMES`` games
    TOTAL cannot reach the floor in any single TC, so we answer True without
    touching the DB (covers the common small-import case with zero queries).
    """
    if total_games < MEDIAN_ANCHOR_MIN_GAMES:
        return True
    for tc in _ALL_TIME_CONTROLS:
        su_cte = selected_users_cte(source="single_user")
        anchor_cte = per_user_cte_median_anchor(
            tc,
            source="single_user",
            snapshot_date=None,
            blend=True,
            min_games=MEDIAN_ANCHOR_MIN_GAMES,
        )
        sql = f"WITH {su_cte},\n{anchor_cte}\nSELECT 1 FROM per_user_anchor LIMIT 1"
        result = await session.execute(text(sql).bindparams(user_id=user_id))
        if result.fetchone() is not None:
            # At least one TC clears the floor — user is above floor somewhere.
            return False
    return True


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------


async def _compute_and_upsert_cell(
    session: AsyncSession,
    *,
    user_id: int,
    metric: CdfMetricId,
    tc: TimeControlBucket,
    anchor: RatingAnchorRow,
    cohort: dict[tuple[CdfMetricId, int, TimeControlBucket], CdfTable],
    stage_label: Literal["A", "B"],
) -> None:
    """Compute one (metric, tc) cell for a user and upsert its percentile row.

    Shared per-cell body for ``compute_stage_a`` and ``compute_stage_b``:
    re-raises cancellation, captures and continues on any other exception.
    ``stage_label`` keeps a cell failure attributable to its originating stage
    in Sentry.
    """
    try:
        result = await _compute_metric_for_user_per_tc(session, user_id, metric, tc)
        if result is None:
            # Below per-TC floor for this (metric, tc) → no row.
            return
        value, n_games = result
        table = cohort.get((metric, round_anchor_to_grid(anchor.anchor_rating), tc))
        percentile: float | None = interpolate_cohort_percentile(value, table)
        await upsert_percentile(
            session,
            user_id=user_id,
            metric=metric,
            time_control_bucket=tc,
            value=value,
            n_games=n_games,
            percentile=percentile,
            cdf_snapshot=datetime.now(UTC).date(),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Per-cell capture: other cells continue.
        sentry_sdk.set_context(
            "percentile_compute",
            {
                "user_id": user_id,
                "stage": stage_label,
                "metric": metric,
                "tc": tc,
            },
        )
        sentry_sdk.capture_exception(exc)


async def compute_stage_a(
    user_id: int,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Compute anchors + per-TC ``score_gap`` percentiles for one user.

    Background task — never propagates exceptions back to the trigger site.
    Called by ``_complete_import_job`` via ``asyncio.create_task`` after the
    import transaction commits.

    Anchors are computed FIRST, then per-TC ``score_gap`` percentiles are
    interpolated against the cohort CDF at ``(anchor_rating, tc)``. If the
    user has no above-floor anchors (all TCs below floor or all chess.com
    anchors out-of-range), no percentile rows are written and the chip
    suppresses naturally.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    # Bound how many compute_stage_a/compute_stage_b bodies hold a pooled DB
    # connection at once. Acquired outside the try/except so the existing
    # Sentry capture semantics below are unchanged.
    async with get_percentile_semaphore():
        try:
            async with maker() as session:
                anchors = await compute_anchors_for_user(session, user_id)
                # One batched prefetch per import for all (anchor, TC) cells.
                # The per-TC lookups inside the loop then hit the in-memory dict.
                rounded_anchors = [round_anchor_to_grid(a.anchor_rating) for a in anchors.values()]
                cohort_a = await load_cohort_cells(session, rounded_anchors, list(anchors.keys()))
                for tc, anchor in anchors.items():
                    await _compute_and_upsert_cell(
                        session,
                        user_id=user_id,
                        metric=STAGE_A_METRIC,
                        tc=tc,
                        anchor=anchor,
                        cohort=cohort_a,
                        stage_label="A",
                    )
                await session.commit()
        except asyncio.CancelledError:
            raise  # lifespan shutdown contract
        except Exception as exc:
            # Top-level capture for session-open / commit / anchor-compute failures.
            # CLAUDE.md Backend Rules: variables via set_context, NEVER in message.
            sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": "A"})
            sentry_sdk.capture_exception(exc)
            # Do NOT re-raise — Stage A errors must not propagate to import worker.


async def compute_stage_b(
    user_id: int,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Compute the 10 eval-dependent metric families × user's above-floor TCs.

    Background task — never propagates exceptions. Scheduled via
    ``asyncio.create_task`` from ``eval_drain.py`` (once the user's pending
    evals reach zero and no import is active) and from ``import_service`` at
    import completion.

    Reads anchors from ``user_rating_anchors`` via
    ``fetch_anchors_for_user`` — Stage A is the canonical writer, so by
    the time Stage B runs the user's anchors are persisted. If no anchors
    exist (Stage A failed, all TCs below floor, etc.), Stage B is a
    no-op — the chip suppresses naturally for the user.

    Per-(family, tc) errors are isolated: an inner try/except wraps each
    cell's compute + UPSERT so a failure in one cell does not prevent
    the others from being written. All cells are committed in one
    ``session.commit()`` at the end.

    Stage A / Stage B race: PK is ``(user_id, metric,
    time_control_bucket)`` and Stage A writes only ``score_gap`` rows;
    Stage B writes the other 10 families. Disjoint write sets never
    conflict.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    # Bound how many compute_stage_a/compute_stage_b bodies hold a pooled DB
    # connection at once. Acquired outside the try/except so the existing
    # Sentry capture semantics below are unchanged. This also covers the
    # eval_drain.py trigger site since the semaphore lives inside the
    # function, not at either asyncio.create_task call site.
    async with get_percentile_semaphore():
        try:
            async with maker() as session:
                anchors = await fetch_anchors_for_user(session, user_id=user_id)
                if not anchors:
                    # No above-floor anchors — Stage A wrote nothing, Stage B has
                    # no per-TC cohort key to interpolate against; no-op.
                    return
                # One batched prefetch per import for all (anchor, TC) cells.
                # The (family × TC) lookups inside the loop then hit the in-memory dict.
                rounded_anchors_b = [
                    round_anchor_to_grid(a.anchor_rating) for a in anchors.values()
                ]
                cohort_b = await load_cohort_cells(session, rounded_anchors_b, list(anchors.keys()))
                # One loop over the (family, tc) product keeps the per-cell helper
                # call within the depth-4 nesting gate. itertools.product iterates
                # family-major, tc-minor.
                for family, (tc, anchor) in itertools.product(
                    STAGE_B_METRIC_FAMILIES, anchors.items()
                ):
                    await _compute_and_upsert_cell(
                        session,
                        user_id=user_id,
                        metric=family,
                        tc=tc,
                        anchor=anchor,
                        cohort=cohort_b,
                        stage_label="B",
                    )
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Top-level capture for session-open / commit / anchor-fetch failures.
            sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": "B"})
            sentry_sdk.capture_exception(exc)
        finally:
            # Release the Tier-2 readiness gate regardless of how
            # Stage B exits — success, the no-anchors early return, the top-level
            # exception path, or cancellation (finally runs before the re-raise
            # propagates). Clearing even when zero rows are written is what prevents
            # below-floor / no-anchor users from being locked out of the page forever.
            # Additive only: does not replace the Sentry capture above.
            percentile_compute_registry.clear(user_id)
