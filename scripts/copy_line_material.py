"""Copy the legacy line_loss_* columns into game_flaws.played_line_material, sign flipped.

Phase 254 (D-09, D-17, D-12). Release R1 added the signed 9-slot array ``played_line_material``
(slot N = net material after N plies of the played line, positive = the blunderer is up). Rows the
post-commit hook wrote before R1 only carry the old ``line_loss_1/3/5/7/9`` columns (positive =
the blunderer is down). This tool moves them across once, before the readers switch to the query
time expression (R2):

    played_line_material = [-line_loss_1, NULL, -line_loss_3, NULL, -line_loss_5, NULL,
                            -line_loss_7, NULL, -line_loss_9]

Even slots stay NULL until the post-Phase-252 line pass recomputes them (D-17). The UPDATE only
touches rows with ``played_line_material IS NULL`` and at least one line_loss_* value, so rows
without line values and rows the hook already wrote are left alone, and a re-run updates 0 rows
(the predicate is the checkpoint; ``--start-after`` only skips the already-finished prefix).

It is deliberately NOT part of the Alembic migration: an in-migration UPDATE of the ~2.17M scored
rows would block backend startup. It is batched by game id (``ix_game_flaws_game_id``), throttled,
single-connection (T-254-10) and stops cleanly after the current batch on SIGTERM / SIGINT.

Read-only checks (the connection is opened with default_transaction_read_only = on):
    --status   copy_pending_rows (rows still to copy) and copied_rows (rows holding an array).
    --parity   D-01 / D-12 check before R2 and before the drop: over user-side blunders, how many
               carry a stored facepalm_score, how many an expression score, the largest absolute
               difference between facepalm_expr(FACEPALM_DRILL_LAMBDA) and the stored score, and
               how many rows fall on different sides of FACEPALM_SCORE_MIN. Exits non-zero when
               the largest difference exceeds PARITY_MAX_ABS_DIFF.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

The URL for each target comes from the DATABASE_URL_{DEV,BENCHMARK,PROD} env vars (.env),
resolved via app.core.config.db_url_for_target. It is never printed.

Usage:
    uv run python scripts/copy_line_material.py --db dev --dry-run --limit-batches 1
    uv run python scripts/copy_line_material.py --db prod --status
    PYTHONUNBUFFERED=1 uv run python scripts/copy_line_material.py --db prod --throttle-ms 50
    uv run python scripts/copy_line_material.py --db prod --start-after 123456   # resume
    uv run python scripts/copy_line_material.py --db prod --parity
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast

from sqlalchemy import ColumnElement, Select, func, not_, select, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: E402
from app.repositories.query_utils import is_opponent_expr  # noqa: E402
from app.services.blunder_check_rules import (  # noqa: E402
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_SCORE_MIN,
)
from app.services.facepalm_score import facepalm_expr  # noqa: E402
from scripts.backfill_maia_flaws import (  # noqa: E402
    BACKFILL_DB_CHOICES,
    DEFAULT_REPORT_DIR,
    MS_PER_SECOND,
    RUN_STAMP_FORMAT,
)
from scripts.blunder_check.sample import readonly_connect_args  # noqa: E402

# No magic numbers (CLAUDE.md rule).
DEFAULT_COPY_BATCH_GAMES: int = 2000
DEFAULT_COPY_THROTTLE_MS: int = 50
# The expression is computed in double precision from the stored REAL / SMALLINT facts, the stored
# score was computed from the unrounded facts and then stored as REAL: a difference above float4
# precision means a real divergence between the two (D-01, D-12).
PARITY_MAX_ABS_DIFF: float = 1e-6
EXIT_OK: int = 0
EXIT_PARITY_FAILED: int = 5
REPORT_FILE_PREFIX: str = "copy-line-material"

# Rows still to copy: no array yet and some legacy line value to move. Shared by the UPDATE, the
# dry-run count and --status so the three can never disagree. A constant, never user input.
_COPY_PENDING_PREDICATE: str = (
    "played_line_material IS NULL"
    " AND (line_loss_1 IS NOT NULL OR line_loss_3 IS NOT NULL OR line_loss_5 IS NOT NULL"
    " OR line_loss_7 IS NOT NULL OR line_loss_9 IS NOT NULL)"
)

# The sign flip (D-09, D-17): odd slots (depths 1, 3, 5, 7, 9) take -line_loss_N (a NULL stays
# NULL), even slots stay NULL. Bound parameter only: the game id array.
COPY_SQL: str = f"""
UPDATE game_flaws
SET played_line_material = ARRAY[-line_loss_1, NULL, -line_loss_3, NULL, -line_loss_5,
                                 NULL, -line_loss_7, NULL, -line_loss_9]::smallint[]
WHERE game_id = ANY(CAST(:game_ids AS integer[]))
  AND {_COPY_PENDING_PREDICATE}
"""
COUNT_PENDING_IN_BATCH_SQL: str = f"""
SELECT count(*) FROM game_flaws
WHERE game_id = ANY(CAST(:game_ids AS integer[]))
  AND {_COPY_PENDING_PREDICATE}
"""
NEXT_GAME_IDS_SQL: str = "SELECT id FROM games WHERE id > :cursor ORDER BY id LIMIT :batch"
STATUS_QUERIES: dict[str, str] = {
    "copy_pending_rows": f"SELECT count(*) FROM game_flaws WHERE {_COPY_PENDING_PREDICATE}",
    "copied_rows": "SELECT count(*) FROM game_flaws WHERE played_line_material IS NOT NULL",
}

# Set by the SIGTERM/SIGINT handler; run_copy stops after the current batch.
_stop_requested: bool = False


def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Copy
# ---------------------------------------------------------------------------


async def copy_batch(session: AsyncSession, game_ids: list[int]) -> int:
    """Copy the legacy line values of these games into played_line_material; the rows updated.

    One UPDATE; the caller owns the transaction. Rows that already hold an array, or have no
    line_loss_* value, do not match the predicate and are not touched.
    """
    if not game_ids:
        return 0
    result = await session.execute(text(COPY_SQL), {"game_ids": game_ids})
    return int(cast("CursorResult[Any]", result).rowcount)


async def _count_pending_in_batch(session: AsyncSession, game_ids: list[int]) -> int:
    """Dry run: the rows copy_batch WOULD update."""
    if not game_ids:
        return 0
    result = await session.execute(text(COUNT_PENDING_IN_BATCH_SQL), {"game_ids": game_ids})
    return int(result.scalar_one())


@dataclass
class CopyReport:
    db: str
    run_stamp: str
    dry_run: bool
    start_after: int
    # The last game id processed: re-run with --start-after <cursor> to resume (restarting from 0
    # is also safe, the predicate skips finished rows).
    cursor: int = 0
    batches: int = 0
    games_scanned: int = 0
    # Rows updated (rows that WOULD be updated in a dry run).
    rows_copied: int = 0
    stopped_early: bool = False
    elapsed_s: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _write_report(report: CopyReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{REPORT_FILE_PREFIX}-{report.run_stamp}.json"
    path.write_text(report.to_json() + "\n")
    return path


async def _next_game_ids(session: AsyncSession, cursor: int, batch_games: int) -> list[int]:
    result = await session.execute(
        text(NEXT_GAME_IDS_SQL), {"cursor": cursor, "batch": batch_games}
    )
    return [int(row[0]) for row in result.all()]


async def _copy_one_batch(
    session_maker: async_sessionmaker[AsyncSession],
    report: CopyReport,
    batch_games: int,
) -> bool:
    """Process the next batch of games in ONE transaction; False when no games are left."""
    async with session_maker() as session:
        game_ids = await _next_game_ids(session, report.cursor, batch_games)
        if not game_ids:
            return False
        if report.dry_run:
            copied = await _count_pending_in_batch(session, game_ids)
        else:
            copied = await copy_batch(session, game_ids)
            await session.commit()
    report.cursor = game_ids[-1]
    report.batches += 1
    report.games_scanned += len(game_ids)
    report.rows_copied += copied
    _log(
        f"batch {report.batches}: cursor={report.cursor} games={len(game_ids)} "
        f"rows_copied={copied} total_rows_copied={report.rows_copied}"
        + (" (dry run)" if report.dry_run else "")
    )
    return True


async def run_copy(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    db: str,
    batch_games: int = DEFAULT_COPY_BATCH_GAMES,
    throttle_ms: int = DEFAULT_COPY_THROTTLE_MS,
    start_after: int = 0,
    limit_batches: int | None = None,
    dry_run: bool = False,
    report_dir: Path = DEFAULT_REPORT_DIR,
    run_stamp: str | None = None,
) -> CopyReport:
    """Walk the games by id from `start_after`, one transaction per batch. Always writes the report."""
    report = CopyReport(
        db=db,
        run_stamp=run_stamp or datetime.now(timezone.utc).strftime(RUN_STAMP_FORMAT),
        dry_run=dry_run,
        start_after=start_after,
        cursor=start_after,
    )
    started = time.monotonic()
    try:
        while limit_batches is None or report.batches < limit_batches:
            if _stop_requested:
                report.stopped_early = True
                _log(f"stop requested, ending after cursor={report.cursor}")
                break
            if not await _copy_one_batch(session_maker, report, batch_games):
                break
            if throttle_ms > 0:
                await asyncio.sleep(throttle_ms / MS_PER_SECOND)
    finally:
        report.elapsed_s = round(time.monotonic() - started, 2)
        path = _write_report(report, report_dir)
        _log(f"report written to {path}")
    return report


# ---------------------------------------------------------------------------
# Status and parity (read-only)
# ---------------------------------------------------------------------------


async def _begin_read_only(session: AsyncSession) -> None:
    """Make this session's transaction read-only (must be its first statement), so the check
    cannot write even through an engine that was not opened read-only."""
    await session.execute(text("SET TRANSACTION READ ONLY"))


async def fetch_copy_status(session: AsyncSession) -> dict[str, int]:
    """copy_pending_rows and copied_rows, SELECT-only."""
    await _begin_read_only(session)
    return {
        key: int((await session.execute(text(sql))).scalar_one())
        for key, sql in STATUS_QUERIES.items()
    }


class ParityResult(TypedDict):
    stored_scored: int
    expression_scored: int
    both_scored: int
    max_abs_diff: float | None
    cut_side_mismatches: int


def _parity_stmt() -> Select[Any]:
    """Counts and the largest stored-vs-expression difference over user-side blunders (D-03)."""
    stored = GameFlaw.facepalm_score
    expr = facepalm_expr(FACEPALM_DRILL_LAMBDA)
    both: ColumnElement[bool] = stored.is_not(None) & expr.is_not(None)
    different_side = (stored >= FACEPALM_SCORE_MIN) != (expr >= FACEPALM_SCORE_MIN)
    return (
        select(
            func.count().filter(stored.is_not(None)),
            func.count().filter(expr.is_not(None)),
            func.count().filter(both),
            func.max(func.abs(expr - stored)),
            func.count().filter(both & different_side),
        )
        .select_from(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.severity == _SEVERITY_INT["blunder"],
            not_(is_opponent_expr(GameFlaw.ply, Game.user_color)),
        )
    )


async def fetch_parity(session: AsyncSession) -> ParityResult:
    """Compare facepalm_expr(FACEPALM_DRILL_LAMBDA) with the stored score (D-01, D-12), SELECT-only."""
    await _begin_read_only(session)
    stored, expression, both, max_diff, mismatches = (await session.execute(_parity_stmt())).one()
    return ParityResult(
        stored_scored=int(stored),
        expression_scored=int(expression),
        both_scored=int(both),
        max_abs_diff=None if max_diff is None else float(max_diff),
        cut_side_mismatches=int(mismatches),
    )


def parity_ok(result: ParityResult) -> bool:
    """True when no row differs by more than PARITY_MAX_ABS_DIFF (no overlap counts as ok)."""
    max_diff = result["max_abs_diff"]
    return max_diff is None or max_diff <= PARITY_MAX_ABS_DIFF


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _install_signal_handlers() -> None:
    """Cooperative SIGINT/SIGTERM: finish the current batch, write the report, exit."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        _log(f"signal {signum} received, stopping after this batch")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batched, resumable sign-flipped copy of line_loss_* into played_line_material"
    )
    parser.add_argument(
        "--db",
        choices=list(BACKFILL_DB_CHOICES),
        required=True,
        help="DB target: dev (5432), benchmark (5433), prod (via bin/prod_db_tunnel.sh).",
    )
    parser.add_argument(
        "--batch-games",
        type=int,
        default=DEFAULT_COPY_BATCH_GAMES,
        dest="batch_games",
        help="Games per transaction (keyset over games.id).",
    )
    parser.add_argument(
        "--throttle-ms",
        type=int,
        default=DEFAULT_COPY_THROTTLE_MS,
        dest="throttle_ms",
        help="Sleep between batches.",
    )
    parser.add_argument(
        "--start-after",
        type=int,
        default=0,
        dest="start_after",
        help="Resume after this game id (the cursor of an earlier run; 0 starts over, which is "
        "safe because finished rows no longer match).",
    )
    parser.add_argument(
        "--limit-batches",
        type=int,
        default=None,
        dest="limit_batches",
        help="Stop after this many batches (a slice).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help="Count rows only, write nothing."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--status",
        action="store_true",
        help="Print copy_pending_rows and copied_rows (read-only) and exit.",
    )
    mode.add_argument(
        "--parity",
        action="store_true",
        help="Read-only D-01 / D-12 check: expression vs stored facepalm_score on user blunders. "
        "Exits non-zero when the largest difference exceeds PARITY_MAX_ABS_DIFF.",
    )
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, dest="report_dir")
    args = parser.parse_args(argv)
    if args.batch_games < 1:
        parser.error("--batch-games must be at least 1")
    if args.throttle_ms < 0:
        parser.error("--throttle-ms must not be negative")
    if args.start_after < 0:
        parser.error("--start-after must not be negative")
    if args.limit_batches is not None and args.limit_batches < 1:
        parser.error("--limit-batches must be at least 1")
    return args


async def _print_banner(db: str) -> None:
    """Show which database this run targets, never its URL."""
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT current_database(), inet_server_addr(), inet_server_port()")
                )
            ).one()
    finally:
        await engine.dispose()
    _log(f"target: --db {db} -> database={row[0]} server={row[1]}:{row[2]}")


async def _run_read_only_check(args: argparse.Namespace) -> int:
    """--status / --parity on a one-connection engine opened with default_transaction_read_only."""
    engine = create_async_engine(
        db_url_for_target(args.db),
        pool_size=1,
        max_overflow=0,
        connect_args=readonly_connect_args(),
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            if args.status:
                counts: dict[str, Any] = dict(await fetch_copy_status(session))
                print(" ".join(f"{k}={v}" for k, v in counts.items()), flush=True)
                return EXIT_OK
            result = await fetch_parity(session)
    finally:
        await engine.dispose()
    print(" ".join(f"{k}={v}" for k, v in result.items()), flush=True)
    if parity_ok(result):
        return EXIT_OK
    _log(f"parity FAILED: max_abs_diff exceeds {PARITY_MAX_ABS_DIFF}")
    return EXIT_PARITY_FAILED


async def _run_copy_cli(args: argparse.Namespace) -> int:
    # One connection (T-254-10): the copy shares the prod DB with the Phase 252 repair.
    engine = create_async_engine(
        db_url_for_target(args.db), pool_size=1, max_overflow=0, pool_pre_ping=True
    )
    try:
        report = await run_copy(
            async_sessionmaker(engine, expire_on_commit=False),
            db=args.db,
            batch_games=args.batch_games,
            throttle_ms=args.throttle_ms,
            start_after=args.start_after,
            limit_batches=args.limit_batches,
            dry_run=args.dry_run,
            report_dir=args.report_dir,
        )
    finally:
        await engine.dispose()
    print(
        f"total: batches={report.batches} games_scanned={report.games_scanned} "
        f"rows_copied={report.rows_copied} cursor={report.cursor} "
        f"stopped_early={report.stopped_early} dry_run={report.dry_run}",
        flush=True,
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    asyncio.run(_print_banner(args.db))
    if args.status or args.parity:
        return asyncio.run(_run_read_only_check(args))
    _install_signal_handlers()
    return asyncio.run(_run_copy_cli(args))


if __name__ == "__main__":
    raise SystemExit(main())
