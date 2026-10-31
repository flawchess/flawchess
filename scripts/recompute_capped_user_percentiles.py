"""Recompute persisted per-user percentiles and rating anchors after the ranked-sample cap change.

WHY THIS EXISTS (quick task 261031-sly)
    RECENT_GAMES_PER_TC_CAP was lowered from 3000 to 1000 games per time control on
    2026-10-31 so the user side of every peer-ranked metric matches the benchmark
    peers (the benchmark ingest stops at 1000 games per user per TC). The on-read
    ranked sample picks the new cap up immediately, but the persisted rows
    (``user_rating_anchors`` and ``user_benchmark_percentiles``) were computed on the
    old basis. Stage A (anchors + ``score_gap``) and Stage B (the eval-dependent
    families + per-colour opening rows) only rerun at import completion and at the
    eval-drain zero-pending crossing, so a heavy user keeps old-basis rows until
    their next import. Both stages are also upsert-only: a cell that falls below its
    30-game floor on the new basis is never deleted. This script reruns both stages
    for every affected user and prunes the rows the new run did not rewrite.

WHEN
    On prod, run it AFTER the deploy that ships the new cap: the pre-deploy app would
    overwrite rows on the old cap at the next import or eval drain. Re-running is safe
    (upserts plus prune). Afterwards the script can move to scripts/archive/.

SAFETY
    Stage A/B swallow every exception after ``sentry_sdk.capture_exception``. Sentry
    is not initialised in a script, so ``capture_failures`` hooks that call. A stage
    that recorded a failure never prunes (a transient error must not delete a user's
    percentiles), and Stage B does not run after a failed Stage A.

    Default is a dry run (lists the affected users, writes nothing). ``--execute``
    against prod asks for confirmation (or pass --yes).

Usage:
    uv run python scripts/recompute_capped_user_percentiles.py --db dev
    uv run python scripts/recompute_capped_user_percentiles.py --db dev --execute

    bin/prod_db_tunnel.sh
    uv run python scripts/recompute_capped_user_percentiles.py --db prod
    uv run python scripts/recompute_capped_user_percentiles.py --db prod --execute
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import datetime
import sys
import traceback
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict
from unittest import mock

import sentry_sdk
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402

# Register every ORM model so the mapper registry configures: User.oauth_accounts needs
# OAuthAccount, which the app registers via FastAPI-Users startup; a bare script must do it.
import app.models  # noqa: E402, F401
import app.models.oauth_account  # noqa: E402, F401
import app.models.user  # noqa: E402, F401
from app.models.user_benchmark_percentile import UserBenchmarkPercentile  # noqa: E402
from app.models.user_rating_anchors import UserRatingAnchor  # noqa: E402
from app.services.canonical_slice_sql import (  # noqa: E402
    RECENCY_WINDOW_MONTHS,
    RECENT_GAMES_PER_TC_CAP,
    equal_footing_filter_sql,
)
from app.services.user_benchmark_percentiles_service import (  # noqa: E402
    STAGE_A_METRIC,
    compute_stage_a,
    compute_stage_b,
)

DbTarget = Literal["dev", "prod"]
ALLOWED_DB_TARGETS: tuple[DbTarget, ...] = ("dev", "prod")

SessionMaker = async_sessionmaker[AsyncSession]


class Failure(TypedDict):
    """One swallowed exception recorded by ``capture_failures``."""

    type: str
    message: str


@dataclass
class UserOutcome:
    user_id: int
    stage_a_ok: bool = False
    stage_b_ok: bool = False
    pruned_a: int = 0
    pruned_b: int = 0


async def select_affected_users(
    session: AsyncSession, *, cap: int = RECENT_GAMES_PER_TC_CAP
) -> list[int]:
    """User ids whose persisted rows may rest on the old (larger) ranked sample.

    (a) users with more than ``cap`` games in some TC under the canonical slice
    predicate (copied from ``_recent_capped_per_tc_cte``), and (b) users whose
    persisted anchor pools more than ``cap`` games. Guests are included: their rows
    are persisted the same way.
    """
    # Only the int constant and equal_footing_filter_sql() output are interpolated;
    # the cap is a bind parameter.
    sql = text(
        f"""
        SELECT user_id FROM (
          SELECT g.user_id
          FROM games g
          WHERE g.rated AND NOT g.is_computer_game
            AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
            AND g.time_control_bucket IS NOT NULL
            AND g.played_at >= NOW() - INTERVAL '{RECENCY_WINDOW_MONTHS} months'
            AND {equal_footing_filter_sql()}
          GROUP BY g.user_id, g.time_control_bucket
          HAVING count(*) > :cap
          UNION
          SELECT a.user_id
          FROM user_rating_anchors a
          WHERE a.n_chesscom_games + a.n_lichess_games > :cap
        ) affected
        ORDER BY user_id
        """
    )
    result = await session.execute(sql, {"cap": cap})
    return [int(row[0]) for row in result]


async def prune_stale_stage_a(
    session: AsyncSession, *, user_id: int, since: datetime.datetime
) -> int:
    """Delete the user's anchors and ``score_gap`` rows Stage A did not rewrite since ``since``."""
    anchors = await session.execute(
        delete(UserRatingAnchor).where(
            UserRatingAnchor.user_id == user_id, UserRatingAnchor.computed_at < since
        )
    )
    pcts = await session.execute(
        delete(UserBenchmarkPercentile).where(
            UserBenchmarkPercentile.user_id == user_id,
            UserBenchmarkPercentile.metric == STAGE_A_METRIC,
            UserBenchmarkPercentile.computed_at < since,
        )
    )
    return int(getattr(anchors, "rowcount", 0) or 0) + int(getattr(pcts, "rowcount", 0) or 0)


async def prune_stale_stage_b(
    session: AsyncSession, *, user_id: int, since: datetime.datetime
) -> int:
    """Delete the user's non-``score_gap`` percentile rows (incl. opening rows) older than ``since``."""
    result = await session.execute(
        delete(UserBenchmarkPercentile).where(
            UserBenchmarkPercentile.user_id == user_id,
            UserBenchmarkPercentile.metric != STAGE_A_METRIC,
            UserBenchmarkPercentile.computed_at < since,
        )
    )
    return int(getattr(result, "rowcount", 0) or 0)


@contextlib.contextmanager
def capture_failures() -> Iterator[list[Failure]]:
    """Record every ``sentry_sdk.capture_exception`` call made while the block is active.

    Sentry is not initialised in a script, and Stage A/B swallow every exception after
    calling ``sentry_sdk.capture_exception``, so without this hook a failed recompute
    would be invisible (and would look like a success to the prune step).
    """
    failures: list[Failure] = []

    def recorder(error: BaseException | None = None, *args: object, **kwargs: object) -> None:
        if error is None:
            error = sys.exc_info()[1]
        failures.append(
            {
                "type": type(error).__name__,
                "message": str(error),
            }
        )
        if error is not None:
            traceback.print_exception(error, file=sys.stderr)

    with mock.patch.object(sentry_sdk, "capture_exception", new=recorder):
        yield failures


async def _read_db_now(maker: SessionMaker) -> datetime.datetime:
    """DB clock, read in its own transaction so every later upsert gets a later computed_at."""
    async with maker() as session:
        value = await session.scalar(text("SELECT now()"))
    assert isinstance(value, datetime.datetime)
    return value


async def recompute_user(maker: SessionMaker, user_id: int, failures: list[Failure]) -> UserOutcome:
    """Rerun Stage A, prune, Stage B, prune for one user; never prune after a failed stage."""
    outcome = UserOutcome(user_id=user_id)
    since = await _read_db_now(maker)

    failures_before = len(failures)
    await compute_stage_a(user_id, session_maker=maker)
    if len(failures) > failures_before:
        # A failed Stage A may have left stale rows in place; deleting them (or ranking
        # Stage B against stale anchors) would turn a transient error into data loss.
        return outcome
    outcome.stage_a_ok = True

    # Prune stale anchors BEFORE Stage B: Stage B reads anchors via fetch_anchors_for_user.
    async with maker() as session:
        outcome.pruned_a = await prune_stale_stage_a(session, user_id=user_id, since=since)
        await session.commit()

    failures_before = len(failures)
    await compute_stage_b(user_id, session_maker=maker)
    if len(failures) > failures_before:
        return outcome
    outcome.stage_b_ok = True

    async with maker() as session:
        outcome.pruned_b = await prune_stale_stage_b(session, user_id=user_id, since=since)
        await session.commit()
    return outcome


def _confirm_prod(args: argparse.Namespace, n: int) -> None:
    if args.db != "prod" or args.yes:
        return
    answer = input(f"Recompute percentiles for {n:,} users on PROD. Type 'prod' to continue: ")
    if answer.strip() != "prod":
        raise SystemExit("Aborted.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", choices=ALLOWED_DB_TARGETS, required=True)
    parser.add_argument(
        "--execute", action="store_true", help="Recompute and prune (default: dry run)."
    )
    parser.add_argument("--yes", action="store_true", help="Skip the prod confirmation.")
    return parser.parse_args()


async def _execute(maker: SessionMaker, user_ids: list[int]) -> int:
    """Run every user sequentially; return the process exit status."""
    outcomes: list[UserOutcome] = []
    with capture_failures() as failures:
        for i, user_id in enumerate(user_ids, start=1):
            outcome = await recompute_user(maker, user_id, failures)
            outcomes.append(outcome)
            print(
                f"[{i}/{len(user_ids)}] user {user_id}: stage_a_ok={outcome.stage_a_ok} "
                f"stage_b_ok={outcome.stage_b_ok} pruned_a={outcome.pruned_a} "
                f"pruned_b={outcome.pruned_b}",
                flush=True,
            )
    failed = [o.user_id for o in outcomes if not (o.stage_a_ok and o.stage_b_ok)]
    pruned = sum(o.pruned_a + o.pruned_b for o in outcomes)
    print(
        f"Summary: {len(outcomes):,} users processed, {pruned:,} stale rows pruned, "
        f"{len(failed)} failed {failed}",
        flush=True,
    )
    return 1 if failed else 0


async def _run(args: argparse.Namespace) -> int:
    engine = create_async_engine(db_url_for_target(args.db))
    maker: SessionMaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            user_ids = await select_affected_users(session)
        print(f"{len(user_ids):,} affected users (cap {RECENT_GAMES_PER_TC_CAP}): {user_ids}")
        if not args.execute:
            print("DRY RUN: nothing written. Re-run with --execute to recompute.")
            return 0
        _confirm_prod(args, len(user_ids))
        return await _execute(maker, user_ids)
    finally:
        await engine.dispose()


def main() -> None:
    sys.exit(asyncio.run(_run(_parse_args())))


if __name__ == "__main__":
    main()
