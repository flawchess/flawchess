"""Backfill Stockfish eval into endgame span-entry rows (Phase 78 FILL-01/02/03).

Row-level idempotency only (skip rows where eval_cp OR eval_mate is already
populated). No cross-row hash dedup — endgame span entries are effectively
unique across games and a hash cache lookup costs more than re-evaluating
the rare collision (FILL-02 relaxed, locked per CONTEXT.md D-10).

Three-round runbook (D-07, executed by Plan 78-06):
    Round 1 (dev):       --db dev --user-id <test-user-id> --limit 50  # smoke
    Round 2 (benchmark): --db benchmark                                  # full
                         then operator runs /conv-recov-validation (VAL-01 gate)
    Round 3 (prod):      --db prod                                       # via bin/prod_db_tunnel.sh
                         must complete BEFORE phase merge + deploy

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

DB URL is derived from settings.DATABASE_URL by swapping the port.  To override,
set BACKFILL_DEV_DB_URL, BACKFILL_BENCHMARK_DB_URL, or BACKFILL_PROD_DB_URL.

Stockfish binary:
    The script invokes app.services.engine, which reads STOCKFISH_PATH (default
    /usr/local/bin/stockfish — the path baked into the prod Docker image).
    Locally that binary does not exist; bin/run_local.sh exports
    STOCKFISH_PATH=$HOME/.local/stockfish/sf, but standalone script runs do not
    inherit that, so you must set it yourself:

        export STOCKFISH_PATH=$HOME/.local/stockfish/sf
        uv run python scripts/backfill_eval.py --db dev --user-id 13

    See .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-06-SUMMARY.md
    for install steps if the binary is missing.

Usage:
    uv run python scripts/backfill_eval.py --db dev --limit 50
    uv run python scripts/backfill_eval.py --db benchmark
    uv run python scripts/backfill_eval.py --db prod --user-id 1
    uv run python scripts/backfill_eval.py --db prod --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import chess
import chess.pgn
import sentry_sdk
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.services.engine import evaluate, start_engine, stop_engine  # noqa: E402

# D-09: COMMIT every 100 evals — progress visible at ~7s granularity at 70ms/eval.
EVAL_BATCH_SIZE = 100

# Port map for --db targets per CLAUDE.md.
_TARGET_PORT: dict[str, int] = {
    "dev": 5432,
    "benchmark": 5433,
    "prod": 15432,
}


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _db_url(target: str) -> str:
    """Build the asyncpg URL for the chosen --db target.

    Derives the URL from settings.DATABASE_URL by replacing the host:port
    with localhost:<target-port>.  The target-specific BACKFILL_{TARGET}_DB_URL
    env var overrides this for operators who use non-default credentials.

    Ports:
        dev:       localhost:5432  (flawchess-dev Docker compose)
        benchmark: localhost:5433  (flawchess-benchmark Docker compose)
        prod:      localhost:15432 (SSH tunnel via bin/prod_db_tunnel.sh)
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --db target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

    override = os.environ.get(f"BACKFILL_{target.upper()}_DB_URL")
    if override:
        return override

    port = _TARGET_PORT[target]
    parsed = urlparse(settings.DATABASE_URL)
    # Replace host and port; keep scheme, path (DB name), user, password.
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
    """Replay PGN to target_ply (0-indexed, pre-push).

    Returns the board state BEFORE the move at that ply — this is the
    state that was classified as the endgame span entry.  Mirrors the
    replay loop in scripts/reclassify_positions.py.

    Returns None if the PGN cannot be parsed or if target_ply is out of range.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    for i, node in enumerate(game.mainline()):
        if i == target_ply:
            return board
        board.push(node.move)
    # target_ply >= number of moves → return final position
    return board


def _build_span_entry_stmt(
    user_id: int | None,
    limit: int | None,
) -> Select[tuple[int, int, int, str]]:
    """Build the span-entry SELECT statement.

    Selects GamePosition rows where:
    1. eval_cp IS NULL AND eval_mate IS NULL  (row-level idempotency, FILL-02)
    2. endgame_class IS NOT NULL              (endgame row)
    3. ply == MIN(ply) for its contiguous-run group (user_id, game_id,
       endgame_class, island_id)

    Each contiguous run of the same endgame_class within a game is treated as
    its own span. If a game enters class=1, switches to class=2, then
    re-enters class=1, both class=1 stretches get an entry eval — not just
    the earliest. Spans of any length (including 1-ply) are included; the
    repository's ENDGAME_PLY_THRESHOLD is intentionally not enforced here.

    Island detection uses the gaps-and-islands trick: within a partition of
    (user_id, game_id, endgame_class), `ply - row_number()` is constant for
    consecutive plies and changes whenever a non-class row breaks the run,
    so it serves as a stable per-run group key.

    Optional filters:
    - user_id: scopes to a single user (--user-id flag)
    - limit: caps result set (--limit flag)
    """
    # Per-class row number, ordered by ply. ply - rn is constant within a
    # contiguous run of the same endgame_class in the same game.
    island_rn = func.row_number().over(
        partition_by=(
            GamePosition.user_id,
            GamePosition.game_id,
            GamePosition.endgame_class,
        ),
        order_by=GamePosition.ply,
    )

    classified = (
        select(
            GamePosition.user_id.label("uid"),
            GamePosition.game_id.label("gid"),
            GamePosition.endgame_class.label("ec"),
            GamePosition.ply.label("ply"),
            (GamePosition.ply - island_rn).label("island_id"),
        )
        .where(GamePosition.endgame_class.isnot(None))
        .subquery("classified")
    )

    span_min = (
        select(
            classified.c.uid,
            classified.c.gid,
            classified.c.ec,
            func.min(classified.c.ply).label("min_ply"),
        )
        .group_by(
            classified.c.uid,
            classified.c.gid,
            classified.c.ec,
            classified.c.island_id,
        )
        .subquery("span_min")
    )

    stmt = (
        select(
            GamePosition.id,
            GamePosition.game_id,
            GamePosition.ply,
            Game.pgn,
        )
        .join(Game, Game.id == GamePosition.game_id)
        .join(
            span_min,
            (GamePosition.user_id == span_min.c.uid)
            & (GamePosition.game_id == span_min.c.gid)
            & (GamePosition.endgame_class == span_min.c.ec)
            & (GamePosition.ply == span_min.c.min_ply),
        )
        .where(
            GamePosition.eval_cp.is_(None),
            GamePosition.eval_mate.is_(None),
        )
    )

    if user_id is not None:
        stmt = stmt.where(GamePosition.user_id == user_id)

    stmt = stmt.order_by(GamePosition.game_id, GamePosition.ply)

    if limit is not None:
        stmt = stmt.limit(limit)

    return stmt


async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    dry_run: bool,
    limit: int | None,
    _session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """FILL-01/02/03 backfill driver. Public callable for testability.

    Idempotency (FILL-02 relaxed per D-10): row-level WHERE eval_cp IS NULL
    AND eval_mate IS NULL.  No cross-row hash dedup.

    Resume: same WHERE clause naturally picks up uncommitted rows on the
    next run after a mid-run kill (D-09 COMMIT-every-100 bounds data loss).

    main() parses argv and calls this function with keyword-only args.

    _session_maker: internal test hook to inject a pre-configured session maker
    (e.g. bound to the test DB).  Production callers omit this; the production
    path builds its own engine from _db_url(db).
    """
    dispose_engine = _session_maker is None
    if _session_maker is None:
        url = _db_url(db)
        async_engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    else:
        async_engine = None  # type: ignore[assignment]  # not created here; nothing to dispose
        session_maker = _session_maker

    # Count / fetch phase: a single SELECT, then close the session.
    async with session_maker() as count_session:
        stmt = _build_span_entry_stmt(user_id, limit)
        rows = (await count_session.execute(stmt)).all()

    _log(
        f"Found {len(rows)} span-entry rows with NULL eval "
        f"(db={db}, user_id={user_id}, limit={limit})"
    )

    if dry_run:
        _log("--dry-run: exiting without starting engine or writing")
        if dispose_engine and async_engine is not None:
            await async_engine.dispose()
        return

    if not rows:
        _log("Nothing to do.")
        if dispose_engine and async_engine is not None:
            await async_engine.dispose()
        return

    # Eval + write phase: start engine, process rows, COMMIT every 100.
    await start_engine()
    try:
        async with session_maker() as session:
            evaluated = 0
            skipped_no_board = 0
            skipped_engine_err = 0

            for i, row in enumerate(rows):
                board = _board_at_ply(row.pgn, row.ply)
                if board is None:
                    skipped_no_board += 1
                    _log(f"WARNING: could not replay PGN for game_id={row.game_id} ply={row.ply}; skipping")
                    continue

                eval_cp, eval_mate = await evaluate(board)

                if eval_cp is None and eval_mate is None:
                    # Engine timeout or crash; wrapper already restarted it.
                    # Capture to Sentry with bounded context (T-78-13: no PGN, no user_id).
                    skipped_engine_err += 1
                    sentry_sdk.set_context(
                        "backfill_eval",
                        {
                            "game_position_id": row.id,
                            "game_id": row.game_id,
                            "ply": row.ply,
                            "db_target": db,
                        },
                    )
                    sentry_sdk.set_tag("source", "backfill")
                    sentry_sdk.capture_message(
                        "backfill engine returned (None, None) tuple", level="warning"
                    )
                    continue

                # Row-level UPDATE (FILL-01).  All DB writes are sequential within
                # the same session (CLAUDE.md hard constraint: no concurrent session use).
                await session.execute(
                    update(GamePosition)
                    .where(GamePosition.id == row.id)
                    .values(eval_cp=eval_cp, eval_mate=eval_mate)
                )
                evaluated += 1

                # D-09: COMMIT every 100 evals so a mid-run kill loses at most 100 rows.
                if (i + 1) % EVAL_BATCH_SIZE == 0:
                    await session.commit()
                    _log(
                        f"Committed {i + 1}/{len(rows)} rows "
                        f"(evaluated={evaluated}, "
                        f"skipped_no_board={skipped_no_board}, "
                        f"skipped_engine_err={skipped_engine_err})"
                    )

            # Final commit for remainder.
            await session.commit()
            _log(
                f"Final commit. "
                f"Total evaluated={evaluated}, "
                f"skipped_no_board={skipped_no_board}, "
                f"skipped_engine_err={skipped_engine_err}"
            )
    finally:
        await stop_engine()

    # VACUUM ANALYZE outside a transaction (cannot run inside transaction block).
    # Skipped when using an injected session maker (test mode: VACUUM not meaningful
    # inside a rolled-back transaction and the engine reference is not available).
    if dispose_engine and async_engine is not None:
        _log("Running VACUUM ANALYZE game_positions...")
        async with async_engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("VACUUM ANALYZE game_positions"))
        _log("VACUUM ANALYZE complete.")
        await async_engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments (D-08)."""
    parser = argparse.ArgumentParser(
        description="Backfill Stockfish eval into endgame span-entry rows (Phase 78 FILL-01/02/03)."
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help=(
            "Database target.  dev=localhost:5432, benchmark=localhost:5433, "
            "prod=localhost:15432 (via bin/prod_db_tunnel.sh).  REQUIRED (T-78-12)."
        ),
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        metavar="N",
        help="Limit backfill to a single user ID.  Default: all users.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Count rows and print count; do not start engine or write anything.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap evaluations at N rows.  Useful for smoke checks and staging rounds.",
    )
    return parser.parse_args()


async def main() -> None:
    """Entry point: parse CLI args, init Sentry, run backfill."""
    args = parse_args()

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    _log(
        f"Starting backfill: db={args.db} user_id={args.user_id} "
        f"dry_run={args.dry_run} limit={args.limit}"
    )
    await run_backfill(
        db=args.db,
        user_id=args.user_id,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
