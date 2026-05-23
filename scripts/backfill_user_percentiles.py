"""One-shot backfill script for user_benchmark_percentiles (PCTL-10 / D-14).

Phase 94.1 Plan 08 — PCTL-10 / D-14 / ROADMAP SC-6.

Populates ``user_benchmark_percentiles`` for all existing users so the
percentile chip lights up at deploy time, not only for users who import
after the phase ships.  Also the operator tool for re-running after CDF
regeneration.

CLI usage:

    uv run python scripts/backfill_user_percentiles.py --target dev|prod [--user-id N] [--metric METRIC]

    --target dev   : run against the local dev DB (Docker, localhost:5432)
    --target prod  : run against prod via the SSH tunnel (localhost:15432)
                     REQUIRES: ``bin/prod_db_tunnel.sh start`` first.

Examples:

    # Full dev backfill
    uv run python scripts/backfill_user_percentiles.py --target dev

    # Prod backfill (tunnel must be running)
    bin/prod_db_tunnel.sh start
    uv run python scripts/backfill_user_percentiles.py --target prod
    bin/prod_db_tunnel.sh stop

    # Single user
    uv run python scripts/backfill_user_percentiles.py --target dev --user-id 42

    # Single metric
    uv run python scripts/backfill_user_percentiles.py --target dev --metric score_gap

Safety guards (V4 Tampering / Pitfall 6 / T-94.1-16):

- ``--target dev``  refuses if the resolved URL does not contain ``:5432``.
- ``--target prod`` refuses if the resolved URL does not contain ``:15432``.
- ``--target prod`` refuses if ``localhost:15432`` has no socket listener
  (i.e. the tunnel from ``bin/prod_db_tunnel.sh`` is not up).

Idempotency: re-running produces no state drift — the UPSERT updates
``computed_at`` but leaves ``value`` / ``percentile`` unchanged when inputs
are the same.

Stage A and Stage B semantics (mirrors the steady-state hook):

- Stage A (score_gap): runs for all qualifying users.
- Stage B (achievable_score_gap, section2_score_gap_conv,
  section2_score_gap_parity): runs only for users whose
  ``count_pending_evals == 0`` (cold drain complete).

Cross-environment guard (V4):

  A backfill-local ``engine`` + ``async_sessionmaker`` is constructed
  against the resolved ``--target`` URL.  The global
  ``app.core.database.async_session_maker`` is NEVER touched by this script,
  ensuring ``--target prod`` writes only to the prod URL and ``--target dev``
  writes only to the dev URL.

  After engine construction, ``str(engine.url)`` is asserted against the
  resolved URL before any DB I/O; the script aborts if there is a mismatch.
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
from app.repositories.game_repository import count_pending_evals  # noqa: E402
from app.services.global_percentile_cdf import CdfMetricId  # noqa: E402
from app.services.user_benchmark_percentiles_service import (  # noqa: E402
    STAGE_A_METRIC,
    STAGE_B_METRICS,
    compute_stage_a,
    compute_stage_b,
)

# ---------------------------------------------------------------------------
# Constants (CLAUDE.md: no magic numbers)
# ---------------------------------------------------------------------------

_TARGET_PORT: dict[Literal["dev", "prod"], int] = {"dev": 5432, "prod": 15432}
_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})
_PROD_TUNNEL_HINT: str = "Run `bin/prod_db_tunnel.sh start` first"


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
# Summary counter type
# ---------------------------------------------------------------------------


class _MetricSummary:
    """Accumulates upserted / skipped counts for one metric."""

    def __init__(self) -> None:
        self.upserted: int = 0
        self.skipped_below_floor: int = 0
        self.skipped_no_canonical_games: int = 0
        self.skipped_no_eval: int = 0

    @property
    def total_skipped(self) -> int:
        return self.skipped_below_floor + self.skipped_no_canonical_games + self.skipped_no_eval


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(
    target: Literal["dev", "prod"],
    user_id_filter: int | None,
    metric_filter: CdfMetricId | None,
) -> None:
    """Run the full backfill (or a filtered subset) against the chosen target.

    Constructs a backfill-local engine + ``async_sessionmaker`` so the global
    ``app.core.database.async_session_maker`` is NEVER touched — this is the
    V4 cross-environment guard ensuring ``--target prod`` writes only to the
    prod URL (T-94.1-16).
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
    # any DB I/O.  SQLAlchemy's str(engine.url) masks the password — use
    # render_as_string(hide_password=False) to obtain the full URL for comparison.
    actual_url = engine.url.render_as_string(hide_password=False)
    if actual_url != url:
        await engine.dispose()
        raise SystemExit(
            f"Engine URL mismatch (V4 guard). Expected:\n  {_mask_password(url)}\n"
            f"Got:\n  {_mask_password(actual_url)}\nAborting before any DB I/O."
        )

    # Initialize per-metric summary counters.
    all_metrics: tuple[CdfMetricId, ...] = (STAGE_A_METRIC, *STAGE_B_METRICS)
    summary: dict[CdfMetricId, _MetricSummary] = {m: _MetricSummary() for m in all_metrics}

    # Track failed user_ids for exit-code reporting.
    failed_user_ids: list[int] = []

    _log(f"Starting backfill (metric_filter={metric_filter!r}, user_id_filter={user_id_filter!r})")

    # Iterate over users using a dedicated session for the user-enumeration query.
    async with backfill_session_maker() as enum_session:
        async for user_id in _iter_users(enum_session, user_id_filter=user_id_filter):
            try:
                await _backfill_user(
                    user_id=user_id,
                    target=target,
                    metric_filter=metric_filter,
                    backfill_session_maker=backfill_session_maker,
                    summary=summary,
                )
                _log(f"  user_id={user_id}: OK")
            except Exception as exc:
                # CLAUDE.md Backend Rules: variables via set_context, NEVER in message.
                sentry_sdk.set_context(
                    "backfill_user_percentiles", {"user_id": user_id, "target": target}
                )
                sentry_sdk.capture_exception(exc)
                _log(f"  user_id={user_id}: FAILED — {type(exc).__name__}")
                failed_user_ids.append(user_id)
                # Continue to next user.

    await engine.dispose()

    # Emit summary table.
    elapsed = time.monotonic() - start_epoch
    print(f"\nBackfill complete (target={target}, took {elapsed:.1f}s)")
    for metric_id in all_metrics:
        s = summary[metric_id]
        reasons: list[str] = []
        if s.skipped_below_floor:
            reasons.append(f"below_floor={s.skipped_below_floor}")
        if s.skipped_no_canonical_games:
            reasons.append(f"no_canonical_games={s.skipped_no_canonical_games}")
        if s.skipped_no_eval:
            reasons.append(f"no_eval={s.skipped_no_eval}")
        reason_str = f" ({', '.join(reasons)})" if reasons else ""
        print(f"  {metric_id:<36} upserted={s.upserted}, skipped={s.total_skipped}{reason_str}")

    if failed_user_ids:
        print(f"\nFAILED users ({len(failed_user_ids)}): {failed_user_ids}")
        sys.exit(1)


async def _backfill_user(
    *,
    user_id: int,
    target: Literal["dev", "prod"],
    metric_filter: CdfMetricId | None,
    backfill_session_maker: async_sessionmaker[AsyncSession],
    summary: dict[CdfMetricId, _MetricSummary],
) -> None:
    """Run Stage A + Stage B for a single user and update summary counters.

    Uses row-count introspection (SELECT 1 FROM user_benchmark_percentiles
    WHERE user_id=? AND metric=?) before and after each compute call to
    classify outcomes as upserted vs skipped.

    Stage B runs only if count_pending_evals == 0 (matches hook semantics).
    """
    # Check pending evals for Stage B gate (opens a fresh session).
    async with backfill_session_maker() as session:
        pending_evals = await count_pending_evals(session, user_id)

    # Stage A: score_gap
    if metric_filter is None or metric_filter == STAGE_A_METRIC:
        upserted = await _compute_and_count(
            user_id=user_id,
            metric=STAGE_A_METRIC,
            stage="A",
            backfill_session_maker=backfill_session_maker,
        )
        if upserted is None:
            summary[STAGE_A_METRIC].skipped_no_canonical_games += 1
        elif upserted:
            summary[STAGE_A_METRIC].upserted += 1
        else:
            summary[STAGE_A_METRIC].skipped_below_floor += 1

    # Stage B: eval-dependent metrics (only if no pending evals).
    for metric_id in STAGE_B_METRICS:
        if metric_filter is not None and metric_filter != metric_id:
            continue
        if pending_evals > 0:
            summary[metric_id].skipped_no_eval += 1
            continue
        upserted = await _compute_and_count(
            user_id=user_id,
            metric=metric_id,
            stage="B",
            backfill_session_maker=backfill_session_maker,
        )
        if upserted is None:
            summary[metric_id].skipped_no_canonical_games += 1
        elif upserted:
            summary[metric_id].upserted += 1
        else:
            summary[metric_id].skipped_below_floor += 1


async def _compute_and_count(
    *,
    user_id: int,
    metric: CdfMetricId,
    stage: Literal["A", "B"],
    backfill_session_maker: async_sessionmaker[AsyncSession],
) -> bool | None:
    """Call compute_stage_a or compute_stage_b and classify the outcome.

    Returns:
        True  — a row was upserted with a non-null percentile.
        False — a row exists but its percentile IS NULL (below inclusion floor).
        None  — no row written (zero canonical-slice games for this user).

    The three return values map 1:1 onto the per-metric summary counters at
    ``_backfill_user`` (lines 373-378 / 393-398): upserted / skipped_below_floor /
    skipped_no_canonical_games.
    """
    # IN-03 fix (94.1-10): the prior implementation issued a pre-compute
    # `_row_exists` probe whose result was never used — pure dead code costing
    # one round-trip per (user, metric) pair. Removed. Insert-vs-update is not
    # observable from outside the UPSERT, so we no longer distinguish them.

    # Call the appropriate stage.
    if stage == "A":
        await compute_stage_a(user_id, session_maker=backfill_session_maker)
    else:
        # Stage B computes all 3 metrics; we inspect only the specific one.
        await compute_stage_b(user_id, session_maker=backfill_session_maker)

    # Post-compute probe.
    row_after = await _row_exists(user_id, metric, backfill_session_maker)
    if not row_after:
        # No row at all — zero canonical-slice games (value_raw was None).
        return None

    # Row exists. Inspect the percentile to differentiate upserted vs below-floor.
    async with backfill_session_maker() as session:
        result = await session.execute(
            # CAST(:metric AS benchmark_metric) avoids asyncpg VARCHAR→ENUM mismatch.
            text(
                "SELECT percentile FROM user_benchmark_percentiles "
                "WHERE user_id = :uid AND metric = CAST(:metric AS benchmark_metric)"
            ).bindparams(uid=user_id, metric=metric)
        )
        pctl_row = result.fetchone()
    if pctl_row is None:
        # Defensive: row_after said True but the row vanished between probes.
        # Treat as no-row written.
        return None
    if pctl_row.percentile is None:
        # IN-03 fix (94.1-10): below-floor row reaches the skipped_below_floor
        # counter at _backfill_user:378 / :398. Previously unreachable.
        return False
    return True


async def _row_exists(
    user_id: int,
    metric: CdfMetricId,
    session_maker: async_sessionmaker[AsyncSession],
) -> bool:
    """Return True if a row exists in user_benchmark_percentiles for (user_id, metric).

    The metric column is a Postgres ENUM type (``benchmark_metric``).  Raw SQL
    bindparams are inferred as ``VARCHAR`` by asyncpg, which triggers a type
    mismatch: ``operator does not exist: benchmark_metric = character varying``.
    The explicit ``::benchmark_metric`` cast at the call site resolves this.
    """
    async with session_maker() as session:
        result = await session.execute(
            # CAST(:metric AS benchmark_metric) avoids asyncpg VARCHAR→ENUM type mismatch.
            # Note: `:metric::benchmark_metric` (PostgreSQL shorthand cast) confuses
            # SQLAlchemy's bindparam parser — use the explicit CAST() form instead.
            text(
                "SELECT 1 FROM user_benchmark_percentiles"
                " WHERE user_id = :uid AND metric = CAST(:metric AS benchmark_metric)"
            ).bindparams(uid=user_id, metric=metric)
        )
        return result.fetchone() is not None


# ---------------------------------------------------------------------------
# Argparse entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill user_benchmark_percentiles for all existing users. "
            "For --target prod, bin/prod_db_tunnel.sh must be running first."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev\n"
            "  uv run python scripts/backfill_user_percentiles.py --target prod\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --user-id 42\n"
            "  uv run python scripts/backfill_user_percentiles.py --target dev --metric score_gap\n"
            "\n"
            "For --target prod, run `bin/prod_db_tunnel.sh start` first.\n"
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
        choices=list(
            (
                "score_gap",
                "achievable_score_gap",
                "section2_score_gap_conv",
                "section2_score_gap_parity",
            )
        ),
        default=None,
        help="Process only this metric (optional; default: all metrics).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    target: Literal["dev", "prod"] = args.target  # type: ignore[assignment]
    metric: CdfMetricId | None = args.metric  # type: ignore[assignment]
    asyncio.run(
        main(
            target=target,
            user_id_filter=args.user_id,
            metric_filter=metric,
        )
    )
