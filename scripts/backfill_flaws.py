"""Backfill game_flaws materialization for all users (or --user-id).

Recomputes game_flaws for games that have been Stockfish-analyzed. This is
the threshold-change recompute tool (D-09): run it after a severity threshold
change to rebuild all rows, or at rollout to populate game_flaws for existing
users whose games were imported before Phase 108.

All three write paths (import hook in eval_drain.py, reclassify_positions.py,
and this script) call the SAME classify_game_flaws + flaw_record_to_row
functions so the materialized table never drifts (D-10).

Batching is MANDATORY given the project's OOM history (CLAUDE.md). Commit
every BACKFILL_GAMES_PER_BATCH games; no asyncio.gather on the same session.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

The URL for each target comes from the DATABASE_URL_{DEV,BENCHMARK,PROD} env
vars (.env), resolved via app.core.config.db_url_for_target.

Usage:
    uv run python scripts/backfill_flaws.py --db dev --user-id 28 --dry-run
    uv run python scripts/backfill_flaws.py --db dev --user-id 28
    uv run python scripts/backfill_flaws.py --db benchmark
    uv run python scripts/backfill_flaws.py --db prod
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402
from app.models.game import Game  # noqa: E402

# Game.user_id has a FK to users.id; importing only Game leaves the users table
# unregistered and select(Game...) raises NoReferencedTableError at compile time.
# User in turn declares a relationship to OAuthAccount, so both must be imported.
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.flaws_repository import fetch_game_positions_ordered  # noqa: E402
from app.repositories.game_flaws_repository import (  # noqa: E402
    bulk_insert_game_flaws,
    delete_flaws_for_game,
    flaw_record_to_row,
)
from app.services.flaws_service import classify_game_flaws  # noqa: E402

# No magic numbers (CLAUDE.md rule).
# Commit every N games to keep memory bounded (OOM history — see CLAUDE.md).
BACKFILL_GAMES_PER_BATCH = 100


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(description="Backfill game_flaws materialization table")
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        help="Backfill only this user's games (omit to backfill all users).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Classify and count rows without writing to the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many games (useful for smoke tests).",
    )
    parser.add_argument(
        "--full-evald-only",
        action="store_true",
        dest="full_evald_only",
        help=(
            "Only scan games with full_evals_completed_at set. Targets the flaw-eligible "
            "set directly instead of loading every game's positions (the coverage gate "
            "skips the rest). Use for prod backfills to avoid reading all positions."
        ),
    )
    return parser.parse_args()


async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    dry_run: bool,
    limit: int | None,
    full_evald_only: bool = False,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Run the game_flaws backfill.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        user_id: Scope backfill to this user's games (None = all users).
        dry_run: If True, classify and count but do NOT write or commit.
        limit: Maximum number of games to process (None = no limit).
        full_evald_only: If True, scan only games with full_evals_completed_at
            set — the flaw-eligible set. Avoids loading positions for the ~95%
            of games that lack full-game evals (prod-load-friendly).
        session_maker: Injectable session factory for testing. When None,
            a real engine is created from db_url_for_target(db).
    """
    # Initialize Sentry for error tracking in scripts
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    target_label = f"user {user_id}" if user_id is not None else "all users"
    _log(f"Backfill target: {target_label}")
    _log(f"Mode: {'--dry-run (no writes)' if dry_run else 'write'}")
    _log(f"Batch size: {BACKFILL_GAMES_PER_BATCH} games per commit")
    if full_evald_only:
        _log("Scope: full-eval'd games only (full_evals_completed_at IS NOT NULL)")
    if limit:
        _log(f"Limit: {limit} games")

    # ------------------------------------------------------------------
    # Phase 1: Load all candidate game IDs (analyzed games with eval_cp
    # coverage sufficient for classify_game_flaws to work).
    # We rely on classify_game_flaws's own EVAL_COVERAGE_MIN gate —
    # games with insufficient coverage return GameNotAnalyzed and are skipped.
    # ------------------------------------------------------------------
    async with session_maker() as session:
        stmt = select(Game.id, Game.user_id)
        if user_id is not None:
            stmt = stmt.where(Game.user_id == user_id)
        if full_evald_only:
            # Restrict to flaw-eligible games (full-game evals present). The
            # classify coverage gate still skips any below EVAL_COVERAGE_MIN.
            stmt = stmt.where(Game.full_evals_completed_at.isnot(None))
        # Order deterministically for resumability and progress logging
        stmt = stmt.order_by(Game.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        game_rows = list(result.all())

    total_games = len(game_rows)
    _log(f"Games to process: {total_games}")

    if total_games == 0:
        _log("Nothing to do.")
        return

    # ------------------------------------------------------------------
    # Phase 2: Process in batches of BACKFILL_GAMES_PER_BATCH.
    # Each game: delete existing rows → classify → insert new rows.
    # Commit per chunk (OOM-safe, idempotent for threshold-change reruns).
    # ------------------------------------------------------------------
    total_flaws_written = 0
    total_skipped = 0
    total_errors = 0

    for batch_start in range(0, total_games, BACKFILL_GAMES_PER_BATCH):
        batch = game_rows[batch_start : batch_start + BACKFILL_GAMES_PER_BATCH]
        batch_num = batch_start // BACKFILL_GAMES_PER_BATCH + 1
        total_batches = (total_games + BACKFILL_GAMES_PER_BATCH - 1) // BACKFILL_GAMES_PER_BATCH

        async with session_maker() as session:
            batch_flaws = 0

            for game_id_val, game_user_id in batch:
                # Load game ORM object + ordered positions (sequential — no asyncio.gather)
                game_result = await session.execute(select(Game).where(Game.id == game_id_val))
                game_obj = game_result.scalar_one_or_none()
                if game_obj is None:
                    total_errors += 1
                    continue

                positions = await fetch_game_positions_ordered(
                    session, game_id=game_id_val, user_id=game_user_id
                )

                try:
                    result_val = classify_game_flaws(game_obj, positions)
                except Exception as exc:
                    # Per-game errors must not abort the run (T-108-15 mitigation).
                    # No variables in the message — Sentry context carries the IDs.
                    sentry_sdk.set_context(
                        "game_flaws_backfill",
                        {"game_id": game_id_val, "user_id": game_user_id},
                    )
                    sentry_sdk.capture_exception(exc)
                    _log(
                        f"  ERROR: classify failed for game_id={game_id_val} "
                        f"user_id={game_user_id}: {exc}"
                    )
                    total_errors += 1
                    continue

                # GameNotAnalyzed: skip silently (no eval coverage).
                # TypedDict is a plain dict at runtime; discriminate on "reason" key
                # (isinstance(result_val, GameNotAnalyzed) raises TypeError at runtime).
                if "reason" in result_val:
                    total_skipped += 1
                    continue

                # After the "reason" guard, result_val is narrowed to list[FlawRecord].
                flaw_list = result_val

                if dry_run:
                    batch_flaws += len(flaw_list)
                    total_flaws_written += len(flaw_list)
                    continue

                try:
                    # Delete-then-insert = idempotent recompute (threshold-change safe).
                    # T-108-13 mitigation: delete scoped to (game_id, user_id).
                    await delete_flaws_for_game(session, game_id=game_id_val, user_id=game_user_id)
                    rows = [
                        flaw_record_to_row(
                            user_id=game_user_id,
                            game_id=game_id_val,
                            flaw=flaw,
                        )
                        for flaw in flaw_list
                    ]
                    await bulk_insert_game_flaws(session, rows)
                    batch_flaws += len(rows)
                    total_flaws_written += len(rows)
                except Exception as exc:
                    # Write errors: capture, skip this game, continue batch.
                    sentry_sdk.set_context(
                        "game_flaws_backfill_write",
                        {"game_id": game_id_val, "user_id": game_user_id},
                    )
                    sentry_sdk.capture_exception(exc)
                    _log(
                        f"  ERROR: write failed for game_id={game_id_val} "
                        f"user_id={game_user_id}: {exc}"
                    )
                    total_errors += 1
                    continue

            if not dry_run:
                await session.commit()

        _log(
            f"Batch {batch_num}/{total_batches}: "
            f"{len(batch)} games, {batch_flaws} flaw rows "
            f"({'dry-run' if dry_run else 'written'})"
        )

    _log("")
    _log("Backfill complete:")
    _log(f"  Games processed: {total_games - total_errors}")
    _log(f"  Games skipped (no analysis): {total_skipped}")
    _log(f"  Errors: {total_errors}")
    _log(f"  Flaw rows {'counted' if dry_run else 'written'}: {total_flaws_written}")


if __name__ == "__main__":
    asyncio.run(run_backfill(**vars(_parse_args())))
