"""One-shot backfill script for user_rating_anchors + user_benchmark_percentiles.

Phase 94.4 Plan 06 — cohort-CDF cutover repopulate
Phase 94.4 Plan 12 — D-12 Reversal Amendment repopulate
---------------------------------------------------

Populates BOTH ``user_rating_anchors`` and ``user_benchmark_percentiles``
for all existing users so the cohort-percentile chip lights up at deploy
time, not only for users who import after the phase ships.

After Plan 09's reshape migration, both tables are empty: this
script is the canonical repopulate path. The 3-stage per-user flow
mirrors the import-time fire-and-forget path exactly:

  1. ``compute_stage_a`` — opens its own session, calls
     ``compute_anchors_for_user`` (D-12 Reversal: game-weighted blended
     anchor, pooling converted chess.com + native Lichess ratings), then
     per-TC score_gap percentiles. RESEARCH Pitfall 9 backfill ordering is
     enforced INSIDE ``compute_stage_a`` (anchors first, then percentiles).
  2. ``compute_stage_b`` — opens its own session, reads anchors via
     ``fetch_anchors_for_user``, computes the 7 eval-dependent metric
     families × the user's above-floor TCs.

Transactional boundary note: ``compute_stage_a`` and ``compute_stage_b``
each own their session and commit internally (the steady-state
fire-and-forget hooks rely on this). The backfill preserves that
contract — a partial failure at Stage B will leave a user with anchors
+ score_gap rows but missing other-family rows. The next backfill rerun
fills the gap idempotently (UPSERT semantics).

CLI usage:

    uv run python scripts/backfill_user_percentiles.py --target dev|prod
        [--user-id N] [--metric METRIC] [--tc TC] [--skip-anchors]
        [--snapshot-date YYYY-MM-DD]

    --target dev   : run against the local dev DB (Docker, localhost:5432)
    --target prod  : run against prod via the SSH tunnel (localhost:15432)
                     REQUIRES: ``bin/prod_db_tunnel.sh`` first.
    --snapshot-date: date to use as the snapshot date for the backfill
                     (defaults to today; used for reproducibility).

Examples:

    # Full dev backfill (anchors + percentiles)
    uv run python scripts/backfill_user_percentiles.py --target dev

    # Full dev backfill with explicit snapshot date (D-12 Reversal Amendment)
    uv run python scripts/backfill_user_percentiles.py --target dev --snapshot-date 2026-05-27

    # Prod backfill (tunnel must be running)
    bin/prod_db_tunnel.sh
    uv run python scripts/backfill_user_percentiles.py --target prod --snapshot-date 2026-05-27
    bin/prod_db_tunnel.sh stop

    # Single user
    uv run python scripts/backfill_user_percentiles.py --target dev --user-id 42

    # Single metric (one of 8 CdfMetricId values; per CONTEXT D-13)
    uv run python scripts/backfill_user_percentiles.py --target dev --metric score_gap

    # Single TC (narrow-testing the per-TC iteration)
    uv run python scripts/backfill_user_percentiles.py --target dev --tc rapid

    # Re-run after anchors are already populated (idempotency optimization)
    uv run python scripts/backfill_user_percentiles.py --target dev --skip-anchors

The 8 valid ``--metric`` values (CONTEXT D-13, Plan 04 collapse):

    score_gap, achievable_score_gap, score_gap_conv,
    score_gap_parity, recovery_score_gap, time_pressure_score_gap,
    clock_gap, net_flag_rate

The 12 legacy TC-suffixed composite metric IDs (e.g.
``time_pressure_score_gap_bullet``) retire — TC is now an outer
dimension of the cohort CDF + a separate column on
``user_benchmark_percentiles``, not a metric-name suffix.

Safety guards (V4 Tampering / Pitfall 6 / T-94.1-16 / T-94.4-06-01):

- ``--target dev``  refuses if the resolved URL does not contain ``:5432``.
- ``--target prod`` refuses if the resolved URL does not contain ``:15432``.
- ``--target prod`` refuses if ``localhost:15432`` has no socket listener
  (i.e. the tunnel from ``bin/prod_db_tunnel.sh`` is not up).

Idempotency: re-running produces no state drift — both UPSERTs refresh
``computed_at`` but leave ``value`` / ``percentile`` / ``anchor_rating``
unchanged when inputs are the same.

Cross-environment guard (V4):

  A backfill-local ``engine`` + ``async_sessionmaker`` is constructed
  against the resolved ``--target`` URL.  The global
  ``app.core.database.async_session_maker`` is NEVER touched by this script,
  ensuring ``--target prod`` writes only to the prod URL and ``--target dev``
  writes only to the dev URL.

  After engine construction, ``str(engine.url)`` is asserted against the
  resolved URL before any DB I/O; the script aborts if there is a mismatch.

Summary output (per CONTEXT D-13 + Plan 12 D-12 Reversal Amendment truth):

  Two tables print at end-of-run:

    1. Anchor Composition Summary — counts per (TC × composition): mixed
       (both platforms), pure_lichess, pure_chesscom, no_anchor (below
       ``MEDIAN_ANCHOR_MIN_GAMES`` floor or chess.com Daily-only). Derived
       from the ``n_chesscom_games`` / ``n_lichess_games`` fields on the
       upserted ``RatingAnchorRow`` (D-12 Reversal Amendment schema).

    2. Percentile summary — counts per (metric × TC): users-included
       (row written), users-floor-rejected (no row written, below per-TC
       pool inclusion floor), users-suppressed (row written but
       ``percentile=NULL`` because the cohort CDF has no cell at the
       user's rounded anchor — i.e. ``interpolate_cohort_percentile``
       returned None).

  A per-100-users progress line continues to print mid-run (Phase 94.3
  backfill discipline).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import sys
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Bootstrap project root so ``app.*`` imports resolve when run as a script.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.models import oauth_account as _oauth_account_module  # noqa: E402,F401 — registers OAuthAccount for SQLAlchemy mapper (User.oauth_accounts relationship)
from app.models.user import User  # noqa: E402
from app.models.user_rating_anchors import TimeControlBucket  # noqa: E402
from app.repositories.user_rating_anchors_repository import RatingAnchorRow  # noqa: E402
from app.services.global_percentile_cdf import CdfMetricId  # noqa: E402
from app.services.user_benchmark_percentiles_service import (  # noqa: E402
    STAGE_A_METRIC,
    STAGE_B_METRIC_FAMILIES,
    compute_anchors_for_user,
    compute_stage_a,
    compute_stage_b,
)

# All 8 CdfMetricId values exposed at module level for argparse + summary
# iteration. Plan 05's STAGE_B_METRIC_FAMILIES is the 7-tuple of eval-
# dependent families; STAGE_A_METRIC is the single eval-independent
# family. Together they cover all 8 CdfMetricId values (D-13).
_ALL_METRICS: tuple[CdfMetricId, ...] = (STAGE_A_METRIC, *STAGE_B_METRIC_FAMILIES)

# Sweep order — canonical bullet → blitz → rapid → classical. Matches
# ``_ALL_TIME_CONTROLS`` in user_benchmark_percentiles_service.py so the
# two sides of the percentile pipeline iterate TCs in identical order.
_ALL_TIME_CONTROLS: tuple[TimeControlBucket, ...] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)

# Composition categories for the per-(TC × composition) anchor summary table.
# Derived from n_chesscom_games / n_lichess_games on the upserted RatingAnchorRow
# (D-12 Reversal Amendment schema — composition replaces the old per-platform grouping).
AnchorComposition = Literal["mixed", "pure_lichess", "pure_chesscom", "no_anchor"]
_ALL_ANCHOR_COMPOSITIONS: tuple[AnchorComposition, ...] = (
    "mixed",
    "pure_lichess",
    "pure_chesscom",
    "no_anchor",
)

# ---------------------------------------------------------------------------
# Constants (CLAUDE.md: no magic numbers)
# ---------------------------------------------------------------------------

_TARGET_PORT: dict[Literal["dev", "prod"], int] = {"dev": 5432, "prod": 15432}
_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})
_PROD_TUNNEL_HINT: str = "Run `bin/prod_db_tunnel.sh` first"
_PROGRESS_LOG_EVERY_N_USERS: int = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log(msg: str = "") -> None:
    """Print a timestamped log line."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _mask_password(url: str) -> str:
    """Replace the password in a DB URL with '***' for safe logging."""
    parsed = urlparse(url)
    if parsed.password:
        masked_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
        return urlunparse(parsed._replace(netloc=masked_netloc))
    return url


def _db_url(target: Literal["dev", "prod"]) -> str:
    """Build the asyncpg URL for the chosen --target.

    Derives the URL from ``settings.DATABASE_URL`` by replacing host:port with
    ``localhost:<target-port>``.  The target-specific
    ``BACKFILL_{TARGET}_DB_URL`` env var overrides this for operators who use
    non-default credentials — typically only needed for prod.

    All targets are reached via localhost (dev via Docker, prod via the SSH
    tunnel from ``bin/prod_db_tunnel.sh``).  Override hosts MUST be in
    ``_LOCAL_HOSTS``; a non-local host (e.g. the Docker-internal ``db``) will
    fail to resolve from a developer workstation.

    Ports:
        dev:  localhost:5432  (flawchess-dev Docker compose)
        prod: localhost:15432 (SSH tunnel via bin/prod_db_tunnel.sh)
    """
    override_var = f"BACKFILL_{target.upper()}_DB_URL"
    override = os.environ.get(override_var)
    if override:
        host = urlparse(override).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"{override_var} host is {host!r}, but this script always reaches "
                f"the database via localhost (dev via Docker, prod via "
                f"the SSH tunnel from bin/prod_db_tunnel.sh). Update the override "
                f"to use localhost:{_TARGET_PORT[target]} (keeping the credentials)."
            )
        return override

    port = _TARGET_PORT[target]
    parsed = urlparse(settings.DATABASE_URL)
    # Replace host and port; keep scheme, path (DB name), user, password.
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _assert_target_safe(url: str, target: Literal["dev", "prod"]) -> None:
    """Refuse to run if the URL does not match the expected target port.

    For ``--target prod``, also verifies the tunnel is up via a socket probe.

    Raises:
        SystemExit: with a descriptive message if the safety check fails.
    """
    port = _TARGET_PORT[target]
    port_token = f":{port}"
    if port_token not in url:
        raise SystemExit(
            f"Refusing to run: URL does not contain {port_token!r} "
            f"(expected for --target {target}). "
            f"Check your BACKFILL_{target.upper()}_DB_URL or settings.DATABASE_URL."
        )
    if target == "prod":
        try:
            sock = socket.create_connection(("localhost", _TARGET_PORT["prod"]), timeout=2)
            sock.close()
        except OSError:
            raise SystemExit(
                f"Refusing to run: localhost:{_TARGET_PORT['prod']} is not reachable. "
                f"The prod DB tunnel is not up. {_PROD_TUNNEL_HINT}"
            )


# ---------------------------------------------------------------------------
# User iteration
# ---------------------------------------------------------------------------


async def _iter_users(
    session: AsyncSession,
    *,
    user_id_filter: int | None,
) -> AsyncIterator[int]:
    """Yield user_ids in created_at ASC order (oldest accounts first).

    Pre-skips users with zero completed imports via an EXISTS sub-query against
    ``import_jobs`` to avoid per-user canonical-slice query overhead on accounts
    that have never imported any games.  If ``user_id_filter`` is set, only
    that user is yielded.

    Note: the ``games`` table has no ``status`` column; completeness is gated on
    ``import_jobs.status = 'completed'`` instead.
    """
    stmt = (
        select(User.id)
        .where(
            text(
                "EXISTS ("
                "  SELECT 1 FROM import_jobs ij"
                "  WHERE ij.user_id = users.id AND ij.status = 'completed'"
                ")"
            )
        )
        .order_by(User.created_at.asc())
    )
    if user_id_filter is not None:
        stmt = stmt.where(User.id == user_id_filter)

    result = await session.execute(stmt)
    for row in result.all():
        yield row[0]


# ---------------------------------------------------------------------------
# Summary counter types
# ---------------------------------------------------------------------------


def _classify_composition(row: RatingAnchorRow) -> AnchorComposition:
    """Classify an anchor row by platform composition (D-12 Reversal Amendment).

    Derives the composition from ``n_chesscom_games`` / ``n_lichess_games``
    on the upserted ``RatingAnchorRow``.  The ``"no_anchor"`` category is
    handled separately in the caller (no row produced for that TC).

    Returns:
        "mixed"          — games from both platforms present.
        "pure_chesscom"  — chess.com games only (no Lichess games).
        "pure_lichess"   — Lichess games only (no chess.com games).
    """
    if row.n_chesscom_games > 0 and row.n_lichess_games > 0:
        return "mixed"
    elif row.n_chesscom_games > 0:
        return "pure_chesscom"
    else:
        return "pure_lichess"


class _AnchorSummary:
    """Accumulates per-(TC × composition) anchor counts (D-12 Reversal Amendment).

    For each (TimeControlBucket, AnchorComposition) cell we count the number
    of users whose anchor compute produced a row with that composition.

    Composition categories:
      ``mixed``         — user has games on both chess.com and Lichess in this TC.
      ``pure_lichess``  — user has Lichess games only in this TC.
      ``pure_chesscom`` — user has chess.com games only in this TC.
      ``no_anchor``     — user has a completed import but no anchor row for
                          this TC (below ``MEDIAN_ANCHOR_MIN_GAMES`` floor, or
                          chess.com Daily-only — neither path produces a row).
    """

    def __init__(self) -> None:
        # cells[(tc, composition)] = count of users with that composition.
        self.cells: dict[tuple[TimeControlBucket, AnchorComposition], int] = {
            (tc, comp): 0 for tc in _ALL_TIME_CONTROLS for comp in _ALL_ANCHOR_COMPOSITIONS
        }


class _PercentileSummary:
    """Accumulates per-(metric × TC) percentile-row counts under the cohort-CDF model.

    Three counters per (metric, TC) cell:

      ``users_included`` — row exists with non-NULL percentile (the user
        passed the per-TC pool inclusion floor AND the cohort CDF has a
        cell at their rounded anchor).

      ``users_floor_rejected`` — no row written. The per-TC pooled CTE
        emitted no row because the user is below the metric's per-TC
        inclusion floor (e.g. < 30 endgames in the recent-3000 × 36-month
        pool, or no above-floor anchor in that TC).

      ``users_suppressed`` — row written with ``percentile=NULL``. The
        user passed the per-TC floor but the cohort CDF has no cell at
        their rounded anchor (``interpolate_cohort_percentile`` returned
        None). This is the new bucket added by Plan 04 + 05 cohort cutover:
        suppression now happens at the CDF lookup, not at the inclusion
        floor.

    The three buckets are mutually exclusive at the (user, metric, TC)
    granularity.
    """

    def __init__(self) -> None:
        self.cells: dict[
            tuple[CdfMetricId, TimeControlBucket],
            tuple[int, int, int],
        ] = {(metric, tc): (0, 0, 0) for metric in _ALL_METRICS for tc in _ALL_TIME_CONTROLS}

    def _bump(
        self,
        metric: CdfMetricId,
        tc: TimeControlBucket,
        *,
        included: int = 0,
        floor_rejected: int = 0,
        suppressed: int = 0,
    ) -> None:
        i, fr, s = self.cells[(metric, tc)]
        self.cells[(metric, tc)] = (i + included, fr + floor_rejected, s + suppressed)

    def bump_included(self, metric: CdfMetricId, tc: TimeControlBucket) -> None:
        self._bump(metric, tc, included=1)

    def bump_floor_rejected(self, metric: CdfMetricId, tc: TimeControlBucket) -> None:
        self._bump(metric, tc, floor_rejected=1)

    def bump_suppressed(self, metric: CdfMetricId, tc: TimeControlBucket) -> None:
        self._bump(metric, tc, suppressed=1)


# ---------------------------------------------------------------------------
# Row probes (post-compute classification)
# ---------------------------------------------------------------------------


async def _classify_anchor_rows(
    session: AsyncSession,
    *,
    user_id: int,
    summary: _AnchorSummary,
    tc_filter: TimeControlBucket | None,
) -> None:
    """Probe ``user_rating_anchors`` for this user and update the anchor summary.

    For each TC in ``_ALL_TIME_CONTROLS`` (or just ``tc_filter`` if set),
    check whether an anchor row exists; if yes, classify its composition from
    ``n_chesscom_games`` / ``n_lichess_games`` and bump the (tc, composition)
    cell; otherwise bump the ``no_anchor`` cell for that TC.

    Uses a single query that returns all of the user's anchor rows in one
    round-trip (D-12 Reversal Amendment — reads game counts, not platform column).
    """
    result = await session.execute(
        text(
            "SELECT time_control_bucket::text AS tc, "
            "       n_chesscom_games, n_lichess_games "
            "FROM user_rating_anchors WHERE user_id = :uid"
        ).bindparams(uid=user_id)
    )
    # Build a composition map keyed by TC.  Construct a minimal RatingAnchorRow
    # (anchor_rating + native medians are irrelevant here; only the two game
    # counts are needed) and delegate to _classify_composition.
    seen: dict[TimeControlBucket, AnchorComposition] = {}
    for row in result.all():
        tc: TimeControlBucket = row.tc  # type: ignore[assignment]
        stub_row = RatingAnchorRow(
            anchor_rating=0,
            n_chesscom_games=row.n_chesscom_games,
            n_lichess_games=row.n_lichess_games,
            chesscom_median_native=None,
            lichess_median_native=None,
        )
        seen[tc] = _classify_composition(stub_row)

    for tc in _ALL_TIME_CONTROLS:
        if tc_filter is not None and tc != tc_filter:
            continue
        composition: AnchorComposition = seen.get(tc, "no_anchor")
        summary.cells[(tc, composition)] += 1


async def _classify_percentile_rows(
    session: AsyncSession,
    *,
    user_id: int,
    summary: _PercentileSummary,
    metric_filter: CdfMetricId | None,
    tc_filter: TimeControlBucket | None,
) -> None:
    """Probe ``user_benchmark_percentiles`` for this user, update percentile summary.

    Pulls all of the user's percentile rows in one round-trip. For each
    (metric, TC) cell:

      - row present, percentile non-NULL → bump_included
      - row present, percentile NULL    → bump_suppressed (CDF had no cell)
      - row absent                       → bump_floor_rejected (below per-TC floor)

    Honors ``--metric`` and ``--tc`` filters when set.
    """
    result = await session.execute(
        text(
            "SELECT metric::text AS metric, "
            "       time_control_bucket::text AS tc, "
            "       percentile "
            "FROM user_benchmark_percentiles WHERE user_id = :uid"
        ).bindparams(uid=user_id)
    )
    seen: dict[tuple[CdfMetricId, TimeControlBucket], float | None] = {}
    for row in result.all():
        metric: CdfMetricId = row.metric  # type: ignore[assignment]
        tc: TimeControlBucket = row.tc  # type: ignore[assignment]
        seen[(metric, tc)] = row.percentile

    for metric in _ALL_METRICS:
        if metric_filter is not None and metric != metric_filter:
            continue
        for tc in _ALL_TIME_CONTROLS:
            if tc_filter is not None and tc != tc_filter:
                continue
            key = (metric, tc)
            if key not in seen:
                summary.bump_floor_rejected(metric, tc)
            elif seen[key] is None:
                # Row exists but percentile=NULL → cohort CDF had no cell at
                # the user's anchor (interpolate_cohort_percentile returned None).
                summary.bump_suppressed(metric, tc)
            else:
                summary.bump_included(metric, tc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(
    target: Literal["dev", "prod"],
    user_id_filter: int | None,
    metric_filter: CdfMetricId | None,
    tc_filter: TimeControlBucket | None = None,
    skip_anchors: bool = False,
) -> None:
    """Run the full backfill (or a filtered subset) against the chosen target.

    Constructs a backfill-local engine + ``async_sessionmaker`` so the global
    ``app.core.database.async_session_maker`` is NEVER touched — this is the
    V4 cross-environment guard ensuring ``--target prod`` writes only to the
    prod URL (T-94.1-16).

    Stage flow per user:

      1. (Optional) Stage A → ``compute_stage_a`` opens its own session
         and runs ``compute_anchors_for_user`` (Lichess-precedence) +
         per-TC score_gap percentiles. Skipped when ``skip_anchors=True``
         AND ``metric_filter`` excludes score_gap.
      2. Stage B → ``compute_stage_b`` opens its own session and reads
         the anchors via ``fetch_anchors_for_user`` (Stage A is the
         canonical writer), then per-(family, TC) percentiles for the 7
         eval-dependent families.
      3. Post-compute classification — probe both tables and bump the
         summary counters.

    Per-user errors are caught + Sentry-captured + logged; the loop
    continues to the next user.
    """
    start_epoch = time.monotonic()

    url = _db_url(target)
    _assert_target_safe(url, target)

    _log(f"Connecting to {_mask_password(url)} (target={target})")

    # Build a backfill-local engine and session factory — NOT the app global.
    engine = create_async_engine(url, pool_pre_ping=True)
    backfill_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    # V4 cross-environment guard: assert engine URL matches resolved URL before
    # any DB I/O. SQLAlchemy's str(engine.url) masks the password — use
    # render_as_string(hide_password=False) to obtain the full URL for comparison.
    actual_url = engine.url.render_as_string(hide_password=False)
    if actual_url != url:
        await engine.dispose()
        raise SystemExit(
            f"Engine URL mismatch (V4 guard). Expected:\n  {_mask_password(url)}\n"
            f"Got:\n  {_mask_password(actual_url)}\nAborting before any DB I/O."
        )

    anchor_summary = _AnchorSummary()
    percentile_summary = _PercentileSummary()
    failed_user_ids: list[int] = []
    processed: int = 0

    _log(
        f"Starting backfill (metric_filter={metric_filter!r}, "
        f"user_id_filter={user_id_filter!r}, tc_filter={tc_filter!r}, "
        f"skip_anchors={skip_anchors})"
    )

    # Iterate over users using a dedicated session for the user-enumeration query.
    async with backfill_session_maker() as enum_session:
        async for user_id in _iter_users(enum_session, user_id_filter=user_id_filter):
            try:
                await _backfill_user(
                    user_id=user_id,
                    backfill_session_maker=backfill_session_maker,
                    metric_filter=metric_filter,
                    tc_filter=tc_filter,
                    skip_anchors=skip_anchors,
                    anchor_summary=anchor_summary,
                    percentile_summary=percentile_summary,
                )
            except Exception as exc:
                # CLAUDE.md Backend Rules: variables via set_context, NEVER in message.
                sentry_sdk.set_context(
                    "backfill_user_percentiles", {"user_id": user_id, "target": target}
                )
                sentry_sdk.capture_exception(exc)
                _log(f"  user_id={user_id}: FAILED — {type(exc).__name__}")
                failed_user_ids.append(user_id)
                # Continue to next user.

            processed += 1
            if processed % _PROGRESS_LOG_EVERY_N_USERS == 0:
                _log(f"  progress: {processed} users processed")

    await engine.dispose()

    # Emit summary tables.
    elapsed = time.monotonic() - start_epoch
    print(
        f"\nBackfill complete (target={target}, users_processed={processed}, took {elapsed:.1f}s)\n"
    )
    _print_anchor_summary(anchor_summary, tc_filter=tc_filter)
    print()
    _print_percentile_summary(percentile_summary, metric_filter=metric_filter, tc_filter=tc_filter)

    if failed_user_ids:
        print(f"\nFAILED users ({len(failed_user_ids)}): {failed_user_ids}")
        sys.exit(1)


async def _backfill_user(
    *,
    user_id: int,
    backfill_session_maker: async_sessionmaker[AsyncSession],
    metric_filter: CdfMetricId | None,
    tc_filter: TimeControlBucket | None,
    skip_anchors: bool,
    anchor_summary: _AnchorSummary,
    percentile_summary: _PercentileSummary,
) -> None:
    """Run the 3-stage flow for a single user and update summary counters.

    RESEARCH Pitfall 9 backfill ordering: anchors come FIRST so per-TC
    percentile compute can read the anchor at lookup time. ``compute_stage_a``
    enforces this internally (it calls ``compute_anchors_for_user`` before
    its per-TC score_gap loop).

    ``skip_anchors=True`` semantics: skip the anchor compute path entirely —
    the operator has already populated ``user_rating_anchors`` in a prior
    run and wants only the percentile pass. In that case we explicitly
    invoke ``compute_anchors_for_user`` only when Stage A is in scope and
    the operator wants score_gap rows; otherwise Stage A is skipped (since
    its per-TC score_gap inner loop depends on the freshly-computed anchors
    dict).

    When ``--skip-anchors`` is combined with the default (no ``--metric``)
    or with ``--metric score_gap``, we still need anchors to interpolate
    score_gap percentiles. To preserve the optimization intent (don't
    recompute anchors that are already there), we read existing anchors
    via ``fetch_anchors_for_user`` and bypass compute_stage_a's anchor
    write path — calling its internal per-TC compute helper would require
    refactoring the service. Net: ``--skip-anchors`` is a Stage B
    optimization (avoid the anchor recompute when only Stage B failed in
    a previous run); for full re-runs without ``--skip-anchors``, the
    standard Stage A + Stage B path runs.
    """
    # Stage A — anchor compute + score_gap per-TC percentile compute.
    # Always run unless --skip-anchors AND --metric filter excludes score_gap.
    stage_a_in_scope = metric_filter is None or metric_filter == STAGE_A_METRIC
    if stage_a_in_scope and not skip_anchors:
        await compute_stage_a(user_id, session_maker=backfill_session_maker)
    elif stage_a_in_scope and skip_anchors:
        # Operator requested skip-anchors but score_gap is in scope.
        # compute_stage_a is the only path that produces score_gap rows,
        # and it internally calls compute_anchors_for_user (which UPSERTs
        # anchors idempotently — re-running is cheap even when anchors
        # are pre-populated). The "skip-anchors" optimization only saves
        # the anchor compute when Stage A is NOT in scope (i.e. when the
        # operator narrows to one of the 7 Stage B metric families with
        # ``--metric``). So when score_gap is in scope, --skip-anchors
        # falls through to the standard Stage A path. Document this in
        # the CLI epilog.
        await compute_stage_a(user_id, session_maker=backfill_session_maker)
    elif not stage_a_in_scope and not skip_anchors:
        # Metric filter narrows to a Stage B family; anchors are still
        # required by compute_stage_b (it reads via fetch_anchors_for_user).
        # Run only the anchor compute, not the full Stage A inner loop.
        async with backfill_session_maker() as anchor_session:
            await compute_anchors_for_user(anchor_session, user_id)
            await anchor_session.commit()
    # else: not stage_a_in_scope AND skip_anchors → assume anchors are
    # already populated; Stage B reads them from the table.

    # Stage B — eval-dependent metric families.
    # Compute when at least one Stage B family is in scope.
    stage_b_in_scope = metric_filter is None or metric_filter in STAGE_B_METRIC_FAMILIES
    if stage_b_in_scope:
        await compute_stage_b(user_id, session_maker=backfill_session_maker)

    # Post-compute classification — probe both tables once each.
    async with backfill_session_maker() as probe_session:
        await _classify_anchor_rows(
            probe_session,
            user_id=user_id,
            summary=anchor_summary,
            tc_filter=tc_filter,
        )
        await _classify_percentile_rows(
            probe_session,
            user_id=user_id,
            summary=percentile_summary,
            metric_filter=metric_filter,
            tc_filter=tc_filter,
        )


# ---------------------------------------------------------------------------
# Summary printers
# ---------------------------------------------------------------------------


def _print_anchor_summary(
    summary: _AnchorSummary,
    *,
    tc_filter: TimeControlBucket | None,
) -> None:
    """Print the per-(TC × composition) anchor count table (D-12 Reversal Amendment).

    Composition categories: mixed / pure_lichess / pure_chesscom / no_anchor.
    Replaces the old per-(TC × platform) table from Plan 06.
    """
    print("Anchor Composition Summary")
    print("--------------------------")
    print(f"  {'TC':<12} {'mixed':>8} {'pure_lichess':>14} {'pure_chesscom':>14} {'no_anchor':>12}")
    for tc in _ALL_TIME_CONTROLS:
        if tc_filter is not None and tc != tc_filter:
            continue
        mixed = summary.cells[(tc, "mixed")]
        pure_lichess = summary.cells[(tc, "pure_lichess")]
        pure_chesscom = summary.cells[(tc, "pure_chesscom")]
        no_anchor = summary.cells[(tc, "no_anchor")]
        print(f"  {tc:<12} {mixed:>8} {pure_lichess:>14} {pure_chesscom:>14} {no_anchor:>12}")


def _print_percentile_summary(
    summary: _PercentileSummary,
    *,
    metric_filter: CdfMetricId | None,
    tc_filter: TimeControlBucket | None,
) -> None:
    """Print the per-(metric × TC) percentile count table."""
    print("Percentile summary (user_benchmark_percentiles counts per metric × TC):")
    print(f"  {'metric':<28} {'TC':<10} {'included':>10} {'floor_rej':>10} {'suppressed':>11}")
    for metric in _ALL_METRICS:
        if metric_filter is not None and metric != metric_filter:
            continue
        for tc in _ALL_TIME_CONTROLS:
            if tc_filter is not None and tc != tc_filter:
                continue
            included, floor_rejected, suppressed = summary.cells[(metric, tc)]
            print(f"  {metric:<28} {tc:<10} {included:>10} {floor_rejected:>10} {suppressed:>11}")


# ---------------------------------------------------------------------------
# Argparse entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill user_rating_anchors + user_benchmark_percentiles for all "
            "existing users. For --target prod, bin/prod_db_tunnel.sh must be "
            "running first."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev\n"
            "  uv run python scripts/backfill_user_percentiles.py --target prod\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --user-id 42\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --metric score_gap\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --tc rapid\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --skip-anchors\n"
            "\n"
            "For --target prod, run `bin/prod_db_tunnel.sh` first.\n"
            "\n"
            "--skip-anchors note: the optimization only saves anchor recompute when\n"
            "narrowing to a Stage B metric family via --metric. When score_gap is in\n"
            "scope (default, or --metric score_gap), Stage A is invoked which always\n"
            "recomputes anchors (idempotent UPSERT) — the flag has no effect.\n"
        ),
    )
    parser.add_argument(
        "--target",
        choices=["dev", "prod"],
        required=True,
        help=(
            "Database target. 'dev' = localhost:5432 (Docker). "
            "'prod' = localhost:15432 (via bin/prod_db_tunnel.sh)."
        ),
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        help="Process only this user_id (optional; default: all users).",
    )
    parser.add_argument(
        "--metric",
        # Phase 94.4 Plan 06 (D-13 + Plan 04 cohort cutover): the 8-value
        # CdfMetricId Literal lifts TC out of the metric name into the
        # COHORT_PERCENTILE_CDF outer key + the user_benchmark_percentiles
        # time_control_bucket column. The 12 Phase 94.3 TC-suffixed
        # composite metric IDs retire entirely.
        choices=list(_ALL_METRICS),
        default=None,
        help="Process only this metric (optional; default: all 8 metrics).",
    )
    parser.add_argument(
        "--tc",
        choices=list(_ALL_TIME_CONTROLS),
        default=None,
        help=(
            "Process only this time-control bucket (optional; default: all 4 TCs). "
            "Narrows the summary tables and post-compute classification — does NOT "
            "skip the underlying compute (compute_stage_a / compute_stage_b iterate "
            "all TCs internally)."
        ),
    )
    parser.add_argument(
        "--skip-anchors",
        action="store_true",
        dest="skip_anchors",
        help=(
            "Skip the anchor compute path when narrowing to a Stage B metric family "
            "(--metric in achievable_score_gap, score_gap_bucket_*, recovery_score_gap, "
            "time_pressure_score_gap, clock_gap, net_flag_rate). Has no effect when "
            "score_gap is in scope (Stage A always recomputes anchors)."
        ),
    )
    parser.add_argument(
        "--snapshot-date",
        default=None,
        dest="snapshot_date",
        metavar="YYYY-MM-DD",
        help=(
            "Snapshot date for the backfill run (informational; defaults to today). "
            "Used for the D-12 Reversal Amendment repopulate to stamp the intended "
            "anchor computation date in the run log. Does not affect computed values "
            "(anchor computation always uses the current conversion snapshot). "
            "Example: --snapshot-date 2026-05-27 for the Plan 12 backfill. "
            "The anchor composition summary prints at the end of the run — "
            "see 'Anchor Composition Summary' (mixed / pure_lichess / pure_chesscom / no_anchor)."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    target: Literal["dev", "prod"] = args.target  # type: ignore[assignment]
    metric: CdfMetricId | None = args.metric  # type: ignore[assignment]
    tc: TimeControlBucket | None = args.tc  # type: ignore[assignment]
    snapshot_date: str = args.snapshot_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[backfill] snapshot_date={snapshot_date} (D-12 Reversal Amendment run)")
    asyncio.run(
        main(
            target=target,
            user_id_filter=args.user_id,
            metric_filter=metric,
            tc_filter=tc,
            skip_anchors=args.skip_anchors,
        )
    )
