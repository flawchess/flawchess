"""Benchmark ingestion orchestrator: import games for selected Lichess users.

Reads benchmark_selected_users (populated by scripts/select_benchmark_users.py),
computes the per-cell deficit (N - already_filled), creates a stub User row
per username in the benchmark DB, then calls the existing run_import pipeline
with a per-(user, TC) since_ms_override + perf_type + max_games — recording
per-(user, TC) checkpoint state in benchmark_ingest_checkpoints.

Slot-filling rule: only users with status='completed' AND games_imported >=
--min-games count toward --per-cell. Users with fewer games are checkpointed
as 'skipped'; 404'd or errored users as 'failed'. Both are skipped on resume
but don't fill a slot — the orchestrator pulls a replacement from the pool
until the cell hits its target or the unattempted candidates run out.

Design decisions (Phase 69 context):
  - Centipawn convention: signed from White's POV. [%eval 2.35] = +235 cp;
    [%eval -0.50] = -50 cp. python-chess uses this convention for node.eval().
    Stored in game_positions.eval_cp (INGEST-06).
  - 36-month game window (D-13): since_ms is set to
    (snapshot_month_end - 36 months) and passed to create_job() as
    since_ms_override. The lichess client receives this directly — bypassing
    get_latest_for_user_platform — so the same lichess username can be
    imported once per TC without the second run inheriting the first run's
    last_synced_at cursor.
  - Per-(user, TC) volume cap: lichess `max=MAX_GAMES_PER_USER_TC` truncates
    server-side. Replaces the prior post-hoc 20k skip path: the long tail is
    never downloaded, so per-user-rate analytics in Phase 73 are no longer
    contaminated by users with massive game histories.
  - perfType filter: passed as `perf_type=tc_bucket` so lichess returns only
    games for the cell's TC. The perfType silent-truncation behavior
    (excludes correspondence/chess960/fromPosition) is exactly what the
    benchmark wants.
  - Cheat contamination (D-01): accepted without mitigation at this phase.
    Lichess's own anti-cheat bans are relied upon; no additional filtering.
  - Batch size: import_service._BATCH_SIZE = 28 (verified in codebase).
    The benchmark orchestrator does NOT override it.

Safety: this script refuses to run unless DATABASE_URL contains 'flawchess_benchmark'
and port '5433', preventing accidental writes to dev/prod.

Usage (benchmark DB must be running via bin/benchmark_db.sh start):
    DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark \
      uv run python scripts/import_benchmark_users.py \
        --per-cell 100 \
        --snapshot-month-end 2026-03-31 \
        2>&1 | tee logs/benchmark-ingest-percell100-$(date +%Y-%m-%d).log

    # Dry-run to preview deficit without importing:
    DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark \
      uv run python scripts/import_benchmark_users.py \
        --per-cell 100 \
        --snapshot-month-end 2026-03-31 \
        --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sentry_sdk
from sqlalchemy import Table, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.models.benchmark_ingest_checkpoint import BenchmarkIngestCheckpoint
from app.models.benchmark_selected_user import BenchmarkSelectedUser
from app.models.game import Game
from app.models.oauth_account import OAuthAccount  # noqa: F401 -- required for User relationship
from app.models.user import User
from app.services.import_service import create_job, get_job, run_import

# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------

# Per-(user, TC) lichess volume cap. Passed as the `max=` parameter so the long
# tail is truncated server-side and never downloaded. Supersedes the prior
# post-hoc 20k skip path. 1000 is the locked default — bumpable later by
# re-running with a higher cap (bulk_insert_games dedups, so it extends history
# rather than re-fetching).
MAX_GAMES_PER_USER_TC = 1000
STUB_PASSWORD = "!BENCHMARK_NO_AUTH"  # not a valid bcrypt hash -> cannot auth
STUB_EMAIL_DOMAIN = "@benchmark.flawchess.local"
WINDOW_MONTHS = 36  # D-13: import games from the 36 months before snapshot_month_end

# Minimum games per (user, TC) to count toward the --per-cell target. Users
# with fewer than this many imported games are checkpointed as 'skipped' so
# they aren't re-attempted, but don't fill a benchmark slot — the orchestrator
# pulls a replacement from the pool. Default 100; tunable via --min-games.
DEFAULT_MIN_USEFUL_GAMES = 100

# Statuses that count toward the --per-cell target (fill a slot).
_FILLED_STATUSES = {"completed"}
# Statuses that block re-attempt on resume but don't necessarily fill a slot.
# Includes legacy 'skipped' rows from older runs (D-14 20k-cap path).
_ATTEMPTED_STATUSES = {"completed", "skipped", "failed"}

# --------------------------------------------------------------------------------------
# Stop flag for SIGINT handling
# --------------------------------------------------------------------------------------

_stop_requested: bool = False


def _install_signal_handler() -> None:
    """Install SIGINT handler that sets _stop_requested flag for clean shutdown."""

    def _handle_sigint(signum: int, frame: object) -> None:
        global _stop_requested
        _stop_requested = True
        _log("SIGINT received -- will stop after current user completes.")

    signal.signal(signal.SIGINT, _handle_sigint)


# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# --------------------------------------------------------------------------------------
# Pure helper functions (exported for unit tests)
# --------------------------------------------------------------------------------------


def compute_deficit_users(
    pool: list[str], filled: set[str], attempted: set[str], target_n: int
) -> list[str]:
    """Return the next (target_n - filled_in_pool) usernames to attempt, in pool order.

    Two-set semantics separates "fills a slot" from "skip on resume":
      - filled: usernames that count toward target_n (status='completed' with
        enough games). 404'd users and low-yield users do NOT fill slots.
      - attempted: usernames already attempted (any terminal checkpoint). The
        orchestrator excludes these from the next pull regardless of whether
        they filled a slot — a 404 on a previous run shouldn't trigger another
        404 on this run.

    Returns an empty list if the target is already met. Returns fewer than the
    deficit when the pool runs out of unattempted candidates.

    Args:
        pool: Ordered list of all candidate usernames for the cell.
        filled: Subset of pool that has filled a slot (counts toward target).
        attempted: Superset of filled — usernames already tried (any outcome).
        target_n: Target number of useful users for this cell.

    Returns:
        List of usernames to import, in pool order, capped at the deficit.
    """
    filled_in_pool = sum(1 for u in pool if u in filled)
    deficit = target_n - filled_in_pool
    if deficit <= 0:
        return []
    out: list[str] = []
    for u in pool:
        if len(out) >= deficit:
            break
        if u not in attempted:
            out.append(u)
    return out


# --------------------------------------------------------------------------------------
# Table bootstrap (INFRA-02: benchmark-only tables are not in the canonical Alembic chain)
# --------------------------------------------------------------------------------------


async def _ensure_checkpoint_table() -> None:
    """Create benchmark_ingest_checkpoints on first invocation (idempotent).

    INFRA-02: benchmark-only tables are not in the canonical Alembic chain. The
    sibling table benchmark_selected_users is created the same way by
    select_benchmark_users.py. We pass the specific Table object via
    metadata.create_all(tables=[...]) so unrelated canonical tables (already
    created by Alembic) are not touched.
    """
    bench_table = cast(Table, BenchmarkIngestCheckpoint.__table__)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: BenchmarkIngestCheckpoint.metadata.create_all(
                sync_conn, tables=[bench_table], checkfirst=True
            )
        )


# --------------------------------------------------------------------------------------
# Stub user creation
# --------------------------------------------------------------------------------------


async def create_stub_user(session: AsyncSession, lichess_username: str) -> int:
    """Idempotently create a benchmark stub User row and return its id.

    If a User with this lichess_username already exists, returns the existing id
    without inserting. Email is sentinel-formatted so it cannot collide with real
    users. is_active=False means the row cannot serve auth even if the benchmark
    DB were exposed to a login surface (it is not).

    Args:
        session: AsyncSession pointing at the benchmark DB.
        lichess_username: Lichess username to create a stub for.

    Returns:
        The User.id of the stub row (new or existing).
    """
    result = await session.execute(select(User).where(User.lichess_username == lichess_username))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        return existing_user.id

    stub = User(
        email=f"lichess-{lichess_username.lower()}{STUB_EMAIL_DOMAIN}",
        hashed_password=STUB_PASSWORD,
        is_active=False,
        is_superuser=False,
        is_verified=False,
        lichess_username=lichess_username,
        is_guest=False,
        beta_enabled=False,
    )
    session.add(stub)
    await session.flush()
    return stub.id


# --------------------------------------------------------------------------------------
# Checkpoint helpers
# --------------------------------------------------------------------------------------


async def _upsert_checkpoint_pending(
    session: AsyncSession,
    lichess_username: str,
    rating_bucket: int,
    tc_bucket: str,
) -> None:
    """Insert a 'pending' checkpoint row for (user, TC) (idempotent by compound unique)."""
    result = await session.execute(
        select(BenchmarkIngestCheckpoint).where(
            BenchmarkIngestCheckpoint.lichess_username == lichess_username,
            BenchmarkIngestCheckpoint.tc_bucket == tc_bucket,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        checkpoint = BenchmarkIngestCheckpoint(
            lichess_username=lichess_username,
            rating_bucket=rating_bucket,
            tc_bucket=tc_bucket,
            status="pending",
            games_imported=0,
            started_at=datetime.now(timezone.utc),
        )
        session.add(checkpoint)
    else:
        existing.status = "pending"
        existing.started_at = datetime.now(timezone.utc)
    await session.flush()


async def _update_checkpoint(
    session: AsyncSession,
    lichess_username: str,
    tc_bucket: str,
    status: str,
    games_imported: int = 0,
    skip_reason: str | None = None,
    benchmark_user_id: int | None = None,
) -> None:
    """Update (user, TC) checkpoint row to a terminal status."""
    result = await session.execute(
        select(BenchmarkIngestCheckpoint).where(
            BenchmarkIngestCheckpoint.lichess_username == lichess_username,
            BenchmarkIngestCheckpoint.tc_bucket == tc_bucket,
        )
    )
    checkpoint = result.scalar_one_or_none()
    if checkpoint is None:
        return
    checkpoint.status = status
    checkpoint.games_imported = games_imported
    checkpoint.skip_reason = skip_reason
    checkpoint.completed_at = datetime.now(timezone.utc)
    if benchmark_user_id is not None:
        checkpoint.benchmark_user_id = benchmark_user_id
    await session.flush()


async def _purge_low_yield_user(session: AsyncSession, user_id: int, tc_bucket: str) -> None:
    """Delete games for a (user, TC) cell that fell below the useful-games floor.

    Removes the games at this TC bucket (game_positions cascades via FK). If the
    user has no games left across any TC, also deletes the stub User row — every
    descendant table (games, game_positions, import_jobs) cascades on user_id, and
    benchmark_ingest_checkpoints.benchmark_user_id is SET NULL on user delete, so
    the checkpoint audit row is preserved.

    Multi-TC safety: if the same lichess_username qualified for another TC and
    that import already filled the cell, those games remain — only the low-yield
    TC's data is purged and the User survives.
    """
    await session.execute(
        delete(Game).where(Game.user_id == user_id, Game.time_control_bucket == tc_bucket)
    )
    remaining = await session.execute(select(func.count(Game.id)).where(Game.user_id == user_id))
    if (remaining.scalar() or 0) == 0:
        await session.execute(delete(User).where(User.id == user_id))


# --------------------------------------------------------------------------------------
# Per-user import
# --------------------------------------------------------------------------------------


async def _import_one_user(
    lichess_username: str,
    rating_bucket: int,
    tc_bucket: str,
    snapshot_month_end: date,
    dry_run: bool,
    min_useful_games: int,
) -> tuple[str, int]:
    """Import games for one (benchmark user, TC) cell.

    Returns:
        Tuple of (final_status, games_imported).
        final_status: "completed" — useful (games_imported >= min_useful_games)
                      "skipped"   — too few games for benchmark use
                      "failed"    — 404 or other error
    """
    if dry_run:
        _log(f"  [dry-run] Would import {lichess_username}")
        return "completed", 0

    # Compute since_ms: 36 months before snapshot_month_end (D-13).
    # Subtract months manually to avoid a dateutil dependency: decrement year by
    # (WINDOW_MONTHS // 12) and month by (WINDOW_MONTHS % 12), rolling over year
    # if needed. Day stays the same -- snapshot_month_end is always the last day
    # of a month, so the corresponding day 36 months earlier is also valid.
    raw_month = snapshot_month_end.month - (WINDOW_MONTHS % 12)
    year_offset = WINDOW_MONTHS // 12 + (1 if raw_month <= 0 else 0)
    month = raw_month + 12 if raw_month <= 0 else raw_month
    window_start = datetime(
        snapshot_month_end.year - year_offset,
        month,
        snapshot_month_end.day,
        tzinfo=timezone.utc,
    )

    try:
        async with async_session_maker() as session:
            # Mark checkpoint as pending
            await _upsert_checkpoint_pending(session, lichess_username, rating_bucket, tc_bucket)
            await session.commit()

            # Create stub user (idempotent)
            user_id = await create_stub_user(session, lichess_username)
            await session.commit()

        # Create real import job and run it. run_import opens its own session internally.
        # since_ms_override bypasses get_latest_for_user_platform so the second TC
        # for the same lichess username is not contaminated by the first TC's
        # last_synced_at cursor; perf_type filters at the lichess API; max_games
        # caps server-side volume per (user, TC).
        since_ms = int(window_start.timestamp() * 1000)
        job_id = create_job(
            user_id=user_id,
            platform="lichess",
            username=lichess_username,
            since_ms_override=since_ms,
            max_games=MAX_GAMES_PER_USER_TC,
            perf_type=tc_bucket,
        )
        await run_import(job_id)

        job_state = get_job(job_id)
        if job_state is None:
            # run_import never re-raises; if job vanished something is very wrong
            raise RuntimeError("Import job state missing after run_import")

        games_imported = job_state.games_imported
        final_status: str

        if job_state.status == "completed":
            # Successful import. Route to 'skipped' if yield is below the
            # benchmark-usefulness floor — those rows still block re-attempt
            # (skip on resume) but don't fill a per-cell slot, so the
            # orchestrator pulls a replacement from the pool.
            if games_imported < min_useful_games:
                final_status = "skipped"
                skip_reason = "too_few_games"
            else:
                final_status = "completed"
                skip_reason = None
            async with async_session_maker() as session:
                # Update checkpoint FIRST while the User still exists, so the
                # benchmark_user_id FK lands cleanly. The subsequent purge may
                # delete the User; ondelete=SET NULL on the checkpoint's FK
                # then auto-NULLs benchmark_user_id at commit time.
                await _update_checkpoint(
                    session,
                    lichess_username,
                    tc_bucket,
                    status=final_status,
                    games_imported=games_imported,
                    skip_reason=skip_reason,
                    benchmark_user_id=user_id,
                )
                # Purge low-yield data so skipped users don't pollute downstream
                # benchmark queries. _purge_low_yield_user keeps multi-TC users
                # whose other TC imports filled cells; only the skipped TC's
                # data is removed.
                if final_status == "skipped":
                    await _purge_low_yield_user(session, user_id, tc_bucket)
                await session.commit()
        else:
            # Import failed (but run_import never re-raises -- it sets status=failed)
            final_status = "failed"
            error_msg = job_state.error or "Unknown import failure"
            _log(f"  FAILED {lichess_username}: {error_msg}")
            async with async_session_maker() as session:
                await _update_checkpoint(
                    session,
                    lichess_username,
                    tc_bucket,
                    status="failed",
                    games_imported=games_imported,
                    benchmark_user_id=user_id,
                )
                await session.commit()

        return final_status, games_imported

    except Exception as exc:
        sentry_sdk.set_context(
            "benchmark_ingest",
            {"username": lichess_username, "cell": f"{rating_bucket}/{tc_bucket}"},
        )
        sentry_sdk.capture_exception(exc)
        _log(f"  ERROR {lichess_username}: {exc}")
        # Best-effort: mark checkpoint failed
        try:
            async with async_session_maker() as session:
                await _update_checkpoint(session, lichess_username, tc_bucket, status="failed")
                await session.commit()
        except Exception:
            pass
        return "failed", 0


# --------------------------------------------------------------------------------------
# Cell deficit query
# --------------------------------------------------------------------------------------


async def _load_cell_data(
    session: AsyncSession,
    rating_bucket: int,
    tc_bucket: str,
) -> tuple[list[str], set[str], set[str]]:
    """Load (pool, filled, attempted) for a given cell from the benchmark DB.

    Returns:
        pool: All usernames for this cell (ordered by id).
        filled: Usernames with status in _FILLED_STATUSES (count toward target).
        attempted: Usernames with status in _ATTEMPTED_STATUSES (skip on resume).
    """
    pool_result = await session.execute(
        select(BenchmarkSelectedUser.lichess_username)
        .where(
            BenchmarkSelectedUser.rating_bucket == rating_bucket,
            BenchmarkSelectedUser.tc_bucket == tc_bucket,
        )
        .order_by(BenchmarkSelectedUser.id)
    )
    pool = list(pool_result.scalars().all())

    checkpoint_result = await session.execute(
        select(
            BenchmarkIngestCheckpoint.lichess_username,
            BenchmarkIngestCheckpoint.status,
        ).where(
            BenchmarkIngestCheckpoint.rating_bucket == rating_bucket,
            BenchmarkIngestCheckpoint.tc_bucket == tc_bucket,
            BenchmarkIngestCheckpoint.status.in_(list(_ATTEMPTED_STATUSES)),
        )
    )
    filled: set[str] = set()
    attempted: set[str] = set()
    for username, status in checkpoint_result.all():
        attempted.add(username)
        if status in _FILLED_STATUSES:
            filled.add(username)

    return pool, filled, attempted


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Import Lichess games for selected benchmark users."
    )
    parser.add_argument(
        "--per-cell",
        type=int,
        default=100,
        metavar="N",
        help="Target number of users to import per (rating_bucket, tc_bucket) cell (default: 100).",
    )
    parser.add_argument(
        "--snapshot-month-end",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="End date of the snapshot month (e.g. 2026-02-28). Required for non-dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan deficit and print the plan without importing anything.",
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=DEFAULT_MIN_USEFUL_GAMES,
        metavar="N",
        help=(
            f"Minimum imported games per (user, TC) to fill a benchmark slot "
            f"(default: {DEFAULT_MIN_USEFUL_GAMES}). Users below this are "
            f"checkpointed as 'skipped' (won't retry) but don't count toward "
            f"--per-cell, so the orchestrator pulls a replacement from the pool."
        ),
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately.",
    )
    args = parser.parse_args()
    if not args.dry_run and args.snapshot_month_end is None:
        parser.error("--snapshot-month-end is required unless --dry-run is set")
    return args


async def main() -> None:
    """Run the benchmark user ingestion orchestrator."""
    # Parse args first so --help works without triggering the safety check.
    args = parse_args()

    # Safety check: refuse to run unless DATABASE_URL points at the benchmark DB.
    # This prevents accidental writes to dev/prod (T-69-01).
    if "5433" not in settings.DATABASE_URL or "flawchess_benchmark" not in settings.DATABASE_URL:
        raise RuntimeError(
            f"Refusing to run benchmark ingest against non-benchmark DB. "
            f"DATABASE_URL must contain 'flawchess_benchmark' and port 5433. "
            f"Got: {settings.DATABASE_URL}"
        )

    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    _install_signal_handler()
    start_time = time.time()

    # Ensure benchmark_ingest_checkpoints exists (INFRA-02: not in Alembic chain)
    await _ensure_checkpoint_table()

    # Discover all (rating_bucket, tc_bucket) cells present in selected users
    async with async_session_maker() as session:
        cell_result = await session.execute(
            select(
                BenchmarkSelectedUser.rating_bucket,
                BenchmarkSelectedUser.tc_bucket,
            ).distinct()
        )
        cells = [(row[0], row[1]) for row in cell_result.all()]

    if not cells:
        _log("No benchmark_selected_users found. Run select_benchmark_users.py first.")
        return

    # Load per-cell plan: (rating_bucket, tc_bucket, unattempted_pool, filled_count, deficit)
    cell_plans: list[tuple[int, str, list[str], int, int]] = []
    async with async_session_maker() as session:
        for rating_bucket, tc_bucket in sorted(cells):
            pool, filled, attempted = await _load_cell_data(session, rating_bucket, tc_bucket)
            unattempted = [u for u in pool if u not in attempted]
            filled_count = sum(1 for u in pool if u in filled)
            deficit = max(0, args.per_cell - filled_count)
            cell_plans.append((rating_bucket, tc_bucket, unattempted, filled_count, deficit))

    # Print plan
    _log()
    _log(f"Benchmark ingest plan (--per-cell {args.per_cell}, --min-games {args.min_games}):")
    total_deficit = 0
    total_unattempted = 0
    for rating_bucket, tc_bucket, unattempted, filled_count, deficit in cell_plans:
        _log(
            f"  cell ({rating_bucket}, {tc_bucket}): "
            f"{filled_count} filled, deficit {deficit}, {len(unattempted)} unattempted "
            f"(will attempt up to deficit; more if low-yield/failed)"
        )
        total_deficit += deficit
        total_unattempted += len(unattempted)
    _log(f"Total deficit: {total_deficit} useful users needed across all cells")
    _log(f"Total unattempted candidates available: {total_unattempted}")
    _log()

    if args.dry_run:
        _log("Dry-run mode -- no imports performed.")
        return

    # Confirmation prompt (unless --yes)
    if not args.yes:
        response = input(
            f"Attempt up to {total_unattempted} users to fill {total_deficit} useful slots? "
            f"Proceed? [y/N] "
        )
        if response.strip().lower() not in ("y", "yes"):
            _log("Aborted.")
            return

    # Execute per-cell import. Walk the unattempted pool in order; stop when the
    # cell hits its deficit of useful users (status='completed') or the pool runs out.
    total_completed = 0
    total_skipped = 0
    total_failed = 0

    for rating_bucket, tc_bucket, unattempted, _filled_count, deficit in cell_plans:
        if _stop_requested:
            _log("Stop requested -- exiting after current cell.")
            break
        if deficit == 0:
            continue

        _log(
            f"Cell ({rating_bucket}, {tc_bucket}): need {deficit} useful users "
            f"(pool of {len(unattempted)} unattempted candidates)..."
        )

        cell_filled = 0
        cell_skipped = 0
        cell_failed = 0

        for username in unattempted:
            if _stop_requested:
                _log("  Stop requested -- skipping remaining users in cell.")
                break
            if cell_filled >= deficit:
                break  # target met for this cell

            _log(f"  Importing {username}...")
            final_status, games_imported = await _import_one_user(
                lichess_username=username,
                rating_bucket=rating_bucket,
                tc_bucket=tc_bucket,
                snapshot_month_end=args.snapshot_month_end,
                dry_run=False,
                min_useful_games=args.min_games,
            )
            if final_status == "completed":
                cell_filled += 1
                total_completed += 1
                _log(f"  Done: {username} -- {games_imported} games imported.")
            elif final_status == "skipped":
                cell_skipped += 1
                total_skipped += 1
                _log(f"  Skipped: {username} -- only {games_imported} games (< {args.min_games}).")
            else:  # failed
                cell_failed += 1
                total_failed += 1

        if cell_filled < deficit:
            _log(
                f"  Cell ({rating_bucket}, {tc_bucket}) pool exhausted: "
                f"{cell_filled}/{deficit} useful (skipped {cell_skipped}, failed {cell_failed})."
            )

    elapsed = time.time() - start_time
    _log()
    _log("Benchmark ingest complete:")
    _log(f"  Completed (>={args.min_games} games): {total_completed}")
    _log(f"  Skipped (low yield):                  {total_skipped}")
    _log(f"  Failed (404/error):                   {total_failed}")
    _log(f"  Duration: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
