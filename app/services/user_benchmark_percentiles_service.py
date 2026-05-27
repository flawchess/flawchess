"""Per-user pooled percentile compute service.

Phase 94.4 Plan 05b — cohort-keyed percentile cutover
-----------------------------------------------------

Rewrite of the post-94.3 service to consume the new cohort CDF artifact
(``COHORT_PERCENTILE_CDF`` via ``interpolate_cohort_percentile``) and the
per-(user, TC) median rating anchor (``user_rating_anchors``). The old
flat 12-name TC-suffixed Stage B metric tuple retires; Stage B now iterates
``STAGE_B_METRIC_FAMILIES`` (7-tuple) × the user's above-floor TCs and
the legacy 2-arg ``interpolate_percentile`` helper is no longer called.

Stage A (eval-independent — wired into import completion per D-03):

  1. Compute and UPSERT per-(user, TC) median rating anchors via the
     ``compute_anchors_for_user`` helper. Anchors come FIRST (RESEARCH
     Pitfall 9 backfill ordering) so the per-TC ``score_gap`` percentile
     lookup downstream can read the anchor's ``anchor_rating`` to key
     into ``COHORT_PERCENTILE_CDF[(anchor, tc)]``.
  2. For each TC where an anchor exists, run
     ``per_user_cte_score_gap_tc(tc, source='single_user', ...)`` to read
     the user's per-TC ``score_gap``, then interpolate against the
     cohort CDF at ``(metric='score_gap', anchor=<lichess-equivalent>,
     tc=<bucket>)`` and UPSERT one
     ``user_benchmark_percentiles(user_id, metric, time_control_bucket)``
     row.

Stage B (eval-dependent — wired into eval drain per D-01): for each
metric family in ``STAGE_B_METRIC_FAMILIES`` × each TC with an above-floor
anchor, dispatch to the matching per-TC builder, interpolate against the
cohort CDF, and UPSERT one row per (family, tc).

Lichess-precedence (D-12) + chesscom_raw_rating capture (D-07 bullet 4):

  ``compute_anchors_for_user`` implements the Lichess-first policy:

  - If the user has ANY Lichess games in the TC → call
    ``per_user_cte_median_anchor(tc, source='single_user',
    platform='lichess')``; persist with ``source_platform='lichess'`` and
    ``chesscom_raw_rating=None`` (Lichess-direct path; no conversion).
  - Otherwise → call ``per_user_cte_median_anchor(tc,
    source='single_user', platform='chesscom')`` to read the raw
    chess.com median, capture it as ``chesscom_raw_rating`` BEFORE
    conversion (so the Plan 07 tooltip can disclose "your chess.com X →
    Lichess-equivalent Y"), then convert via
    ``convert_chesscom_to_lichess(raw, source_tc=tc, target_tc=tc)``.
    If the conversion returns None (chess.com Daily, or out of the
    published range) the TC is skipped entirely — the chip suppresses
    for that (user, TC).

Both stages remain non-blocking — exceptions are captured to Sentry and
swallowed (D-04); neither propagates back to the import worker or drain
coroutine.

Sentry pattern (CLAUDE.md Backend Rules):
  Variables flow into ``sentry_sdk.set_context("percentile_compute",
  {...})`` (user_id, stage, metric, tc) BEFORE
  ``sentry_sdk.capture_exception(exc)``. No variables in error messages —
  preserves Sentry issue grouping per CLAUDE.md.

Security (V5 — T-94.2-03-01 / preserved):
  ``user_id`` flows through every CTE via the SQLAlchemy named bindparam
  ``:user_id`` on static SQL templates (no f-stringed user input).

Session discipline (CLAUDE.md hard rule):
  Each ``compute_stage_*`` opens its own session via the resolved
  ``session_maker`` factory. The session is never shared with the trigger
  site (D-04).

``session_maker`` keyword parameter (enables Plan 06 backfill):
  Both entry points accept an optional ``session_maker`` kwarg. When
  None, they fall back to ``app.core.database.async_session_maker``.
  When provided, they use the injected factory — this lets the backfill
  script target a different DB URL without mutating module-level state.

Stage A / Stage B race-condition non-issue (RESEARCH Pitfall 2):
  Stage A owns ``(score_gap, *)`` percentile rows + ALL anchor rows.
  Stage B owns the other 7 metric families × {bullet, blitz, rapid,
  classical}. The PK is now ``(user_id, metric, time_control_bucket)``
  so disjoint writes never collide.
"""

from __future__ import annotations

import asyncio
from datetime import date

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_maker as _default_session_maker
from app.models.user_rating_anchors import AnchorSource, TimeControlBucket
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
    per_user_cte_median_anchor,
    per_user_cte_net_flag_rate,
    per_user_cte_score_gap_tc,
    per_user_cte_score_gap_bucket_tc,
    per_user_cte_time_pressure_score_gap,
    selected_users_cte,
)
from app.services.chesscom_to_lichess import ChessComSourceTC, convert_chesscom_to_lichess
from app.services.global_percentile_cdf import CdfMetricId, interpolate_cohort_percentile

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


# Mapping from the user_rating_anchors ``TimeControlBucket`` Literal (bullet,
# blitz, rapid, classical) to the ChessGoals snapshot's chess.com source TC
# Literal (bullet, blitz, rapid, daily). chess.com's ``classical`` TC bucket is
# only ever populated by Daily-game imports (RESEARCH Pitfall 11) — Daily has
# no ChessGoals mapping, so ``convert_chesscom_to_lichess(..., source_tc='daily')``
# returns None and the chip suppresses naturally for the (user, classical) cell
# when the only source is chess.com (D-12 fall-through + Pitfall 2 / Pitfall 11).
_CHESSCOM_SOURCE_TC_BY_BUCKET: dict[TimeControlBucket, ChessComSourceTC] = {
    "bullet": "bullet",
    "blitz": "blitz",
    "rapid": "rapid",
    "classical": "daily",
}

# Stage A metric — eval-independent, runs at import-completion time.
STAGE_A_METRIC: CdfMetricId = "score_gap"

# Stage B metric families (7-tuple) — eval-dependent, runs at cold-drain
# time. Each family is computed per the user's above-floor TCs; the legacy
# 12-tuple of TC-suffixed names retires (CONTEXT D-13 — the 8-value
# CdfMetricId Literal lifts TC out of the metric name into the
# COHORT_PERCENTILE_CDF outer key).
STAGE_B_METRIC_FAMILIES: tuple[CdfMetricId, ...] = (
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)


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
    SQL pooled bodies (D-10 source-mode parity). The dispatch covers all 8
    CdfMetricId values; Stage A passes ``family='score_gap'`` and Stage B
    passes one of the other 7 families.
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
    f-stringed (V5).
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


async def _user_has_lichess_games_in_tc(
    session: AsyncSession,
    user_id: int,
    tc: TimeControlBucket,
) -> bool:
    """Return True iff the user has at least one Lichess game in ``tc``.

    Single existence query — short-circuits via ``LIMIT 1``. Used by
    ``compute_anchors_for_user`` to drive the D-12 Lichess-precedence
    rule before dispatching to the per-platform anchor compute.

    ``tc`` is constrained by ``TimeControlBucket`` so f-stringing it into
    the SQL has no injection vector (closed 4-value Literal); ``user_id``
    flows through ``.bindparams()`` per V5.
    """
    sql = (
        f"SELECT 1 FROM games "
        f"WHERE user_id = :user_id "
        f"  AND platform = 'lichess' "
        f"  AND time_control_bucket = '{tc}' "
        f"LIMIT 1"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
    return result.fetchone() is not None


async def _compute_median_anchor_for_platform(
    session: AsyncSession,
    user_id: int,
    tc: TimeControlBucket,
    platform: AnchorSource,
) -> tuple[int, int] | None:
    """Run ``per_user_cte_median_anchor`` for one (user, tc, platform).

    Returns ``(anchor_rating, n_games)`` from the single row of
    ``per_user_anchor``, or ``None`` when the user is below
    ``MEDIAN_ANCHOR_MIN_GAMES`` on the per-TC × platform pool (the CTE's
    HAVING clause emits no row).

    ``platform`` maps directly to the builder's ``platform`` kwarg
    ('lichess' or 'chesscom'); the Lichess-precedence rule lives in the
    caller (``compute_anchors_for_user``), not here. ``user_id`` is bound
    via ``.bindparams()`` (V5).
    """
    su_cte = selected_users_cte(source="single_user")
    anchor_cte = per_user_cte_median_anchor(
        tc,
        source="single_user",
        snapshot_date=None,
        platform=platform,
        min_games=MEDIAN_ANCHOR_MIN_GAMES,
    )
    sql = (
        f"WITH {su_cte},\n{anchor_cte}\n"
        f"SELECT anchor_rating::int AS anchor_rating, n_games::int AS n_games\n"
        f"FROM per_user_anchor\n"
        f"LIMIT 1"
    )
    result = await session.execute(text(sql).bindparams(user_id=user_id))
    row = result.fetchone()
    if row is None or row.anchor_rating is None or row.n_games is None:
        return None
    return (int(row.anchor_rating), int(row.n_games))


# ---------------------------------------------------------------------------
# compute_anchors_for_user — Lichess-precedence rule (D-12) + chesscom_raw_rating
# capture (D-07 bullet 4).
# ---------------------------------------------------------------------------


async def compute_anchors_for_user(
    session: AsyncSession,
    user_id: int,
) -> dict[TimeControlBucket, RatingAnchorRow]:
    """Compute per-(user, TC) anchors and UPSERT them.

    For each TC in ``_ALL_TIME_CONTROLS``:

    1. Decide source platform via D-12 precedence:

       - Has the user played ANY Lichess games in this TC? If yes,
         source_platform='lichess'. Otherwise source_platform='chesscom'.

    2. Run the per-platform median anchor compute on the recent-3000 ×
       36-month pool. Below-floor (n_games < MEDIAN_ANCHOR_MIN_GAMES)
       skips this TC entirely (no anchor row, chip suppresses).

    3. For chess.com anchors: capture the raw chess.com median rating
       BEFORE conversion into ``chesscom_raw_rating`` (D-07 bullet 4 —
       this is the value the Plan 07 tooltip discloses), then call
       ``convert_chesscom_to_lichess(raw, source_tc=tc, target_tc=tc)``
       to obtain the Lichess-equivalent that becomes the persisted
       ``anchor_rating``. If conversion returns None (chess.com Daily,
       or out of the published [500, 3000] chess.com Blitz range), skip
       the TC — the cohort CDF is Lichess-keyed and a chess.com-only
       anchor without a conversion has no defensible anchor to key
       against.

    4. For Lichess anchors: ``chesscom_raw_rating=None`` (no conversion
       involved); ``anchor_rating`` is the raw Lichess median.

    5. UPSERT via ``upsert_anchor``. Return the dict of fresh
       ``RatingAnchorRow`` values keyed by TC for the percentile loop.

    Sentry pattern (CLAUDE.md):
      Per-TC exceptions trip an inner try/except; ``set_context`` carries
      ``user_id``, ``stage='anchor'``, ``tc``, ``platform`` BEFORE
      ``capture_exception``. No variables in error messages.
    """
    anchors: dict[TimeControlBucket, RatingAnchorRow] = {}
    for tc in _ALL_TIME_CONTROLS:
        try:
            has_lichess = await _user_has_lichess_games_in_tc(session, user_id, tc)
            platform: AnchorSource = "lichess" if has_lichess else "chesscom"

            result = await _compute_median_anchor_for_platform(session, user_id, tc, platform)
            if result is None:
                # Below the per-TC × platform floor — skip this TC entirely.
                continue
            raw_anchor_rating, n_games = result

            if platform == "lichess":
                anchor_rating = raw_anchor_rating
                chesscom_raw_rating: int | None = None
            else:
                # chess.com path: capture raw rating BEFORE conversion
                # (D-07 bullet 4 tooltip disclosure source), then convert
                # to the Lichess-equivalent the CDF is keyed against.
                chesscom_raw_rating = raw_anchor_rating
                source_tc = _CHESSCOM_SOURCE_TC_BY_BUCKET[tc]
                lichess_equiv = convert_chesscom_to_lichess(
                    raw_anchor_rating, source_tc=source_tc, target_tc=tc
                )
                if lichess_equiv is None:
                    # Daily, or out-of-range — chip suppresses for this TC.
                    continue
                anchor_rating = lichess_equiv

            await upsert_anchor(
                session,
                user_id=user_id,
                time_control_bucket=tc,
                anchor_rating=anchor_rating,
                source_platform=platform,
                chesscom_raw_rating=chesscom_raw_rating,
                n_games=n_games,
            )
            anchors[tc] = RatingAnchorRow(
                anchor_rating=anchor_rating,
                source_platform=platform,
                chesscom_raw_rating=chesscom_raw_rating,
                n_games=n_games,
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


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------


async def compute_stage_a(
    user_id: int,
    *,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Compute anchors + per-TC ``score_gap`` percentiles for one user.

    Background task — never propagates exceptions back to the trigger site
    (D-04 / ROADMAP SC-3). Called by ``_complete_import_job`` via
    ``asyncio.create_task`` after the import transaction commits.

    Backfill ordering (RESEARCH Pitfall 9): anchors are computed FIRST,
    then per-TC ``score_gap`` percentiles are interpolated against the
    cohort CDF at ``(anchor_rating, tc)``. If the user has no above-floor
    anchors (all TCs below floor or all chess.com anchors out-of-range),
    no percentile rows are written and the chip suppresses naturally.
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            for tc, anchor in anchors.items():
                try:
                    result = await _compute_metric_for_user_per_tc(
                        session, user_id, STAGE_A_METRIC, tc
                    )
                    if result is None:
                        # Below per-TC floor for score_gap → no row.
                        continue
                    value, n_games = result
                    percentile: float | None = interpolate_cohort_percentile(
                        STAGE_A_METRIC, value, anchor.anchor_rating, tc
                    )
                    await upsert_percentile(
                        session,
                        user_id=user_id,
                        metric=STAGE_A_METRIC,
                        time_control_bucket=tc,
                        value=value,
                        n_games=n_games,
                        percentile=percentile,
                        cdf_snapshot=date.today(),
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Per-TC capture: other TCs continue.
                    sentry_sdk.set_context(
                        "percentile_compute",
                        {
                            "user_id": user_id,
                            "stage": "A",
                            "metric": STAGE_A_METRIC,
                            "tc": tc,
                        },
                    )
                    sentry_sdk.capture_exception(exc)
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
    """Compute the 7 eval-dependent metric families × user's above-floor TCs.

    Background task — never propagates exceptions (D-04 / ROADMAP SC-3).
    Called by ``eval_drain.py`` via ``asyncio.create_task`` once the
    user's pending-eval count reaches zero AND no active import is in
    progress (D-01 / Plan 13 Stage B gate).

    Reads anchors from ``user_rating_anchors`` via
    ``fetch_anchors_for_user`` — Stage A is the canonical writer, so by
    the time Stage B runs the user's anchors are persisted. If no anchors
    exist (Stage A failed, all TCs below floor, etc.), Stage B is a
    no-op — the chip suppresses naturally for the user.

    Per-(family, tc) errors are isolated: an inner try/except wraps each
    cell's compute + UPSERT so a failure in one cell does not prevent
    the others from being written. All cells are committed in one
    ``session.commit()`` at the end.

    Stage A / Stage B race: PK is now ``(user_id, metric,
    time_control_bucket)`` and Stage A writes only ``score_gap`` rows;
    Stage B writes the other 7 families. Disjoint write sets never
    conflict (RESEARCH Pitfall 2).
    """
    maker = session_maker if session_maker is not None else _default_session_maker
    try:
        async with maker() as session:
            anchors = await fetch_anchors_for_user(session, user_id=user_id)
            if not anchors:
                # No above-floor anchors — Stage A wrote nothing, Stage B has
                # no per-TC cohort key to interpolate against; no-op.
                return
            for family in STAGE_B_METRIC_FAMILIES:
                for tc, anchor in anchors.items():
                    try:
                        result = await _compute_metric_for_user_per_tc(session, user_id, family, tc)
                        if result is None:
                            # Below per-TC floor for this (family, tc) → no row.
                            continue
                        value, n_games = result
                        percentile: float | None = interpolate_cohort_percentile(
                            family, value, anchor.anchor_rating, tc
                        )
                        await upsert_percentile(
                            session,
                            user_id=user_id,
                            metric=family,
                            time_control_bucket=tc,
                            value=value,
                            n_games=n_games,
                            percentile=percentile,
                            cdf_snapshot=date.today(),
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        # Per-(family, tc) capture: other cells continue.
                        sentry_sdk.set_context(
                            "percentile_compute",
                            {
                                "user_id": user_id,
                                "stage": "B",
                                "metric": family,
                                "tc": tc,
                            },
                        )
                        sentry_sdk.capture_exception(exc)
            await session.commit()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Top-level capture for session-open / commit / anchor-fetch failures.
        sentry_sdk.set_context("percentile_compute", {"user_id": user_id, "stage": "B"})
        sentry_sdk.capture_exception(exc)
