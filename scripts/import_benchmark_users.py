"""Benchmark ingestion orchestrator: import games for selected Lichess users.

Reads benchmark_selected_users (populated by scripts/select_benchmark_users.py),
computes the per-cell deficit (N - already_completed), creates a stub User row
per username in the benchmark DB, pre-seeds an import_jobs row with
last_synced_at = (snapshot_month_end - 36 months) so that run_import derives
the correct since_ms window, then calls the existing run_import pipeline and
records per-user checkpoint state in benchmark_ingest_checkpoints.

Design decisions (Phase 69 context):
  - Centipawn convention: signed from White's POV. [%eval 2.35] = +235 cp;
    [%eval -0.50] = -50 cp. python-chess uses this convention for node.eval().
    Stored in game_positions.eval_cp (INGEST-06).
  - 36-month game window (D-13): last_synced_at is set to
    (snapshot_month_end - 36 months) so run_import's since_ms fetches exactly
    the 36-month window of games for each benchmark user.
  - 20k hard-skip rule (D-14): users with >= 20,000 games imported in the
    36-month window are flagged as outliers. Checkpoint is written as
    status='skipped', skip_reason='over_20k_games'. The games are retained
    in the DB but the user is excluded from per-user-rate analytics in Phase 73.
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
        --snapshot-month-end 2026-02-28

    # Dry-run to preview deficit without importing:
    DATABASE_URL=postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark \
      uv run python scripts/import_benchmark_users.py \
        --per-cell 100 \
        --snapshot-month-end 2026-02-28 \
        --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sentry_sdk
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from app.core.config import settings
from app.core.database import async_session_maker, engine
from app.models.benchmark_ingest_checkpoint import BenchmarkIngestCheckpoint
from app.models.benchmark_selected_user import BenchmarkSelectedUser
from app.models.import_job import ImportJob
from app.models.oauth_account import OAuthAccount  # noqa: F401 -- required for User relationship
from app.models.user import User
from app.services.import_service import create_job, get_job, run_import

# --------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------

HARD_SKIP_THRESHOLD = 20_000  # D-14: users with >= this many games are flagged as outliers
STUB_PASSWORD = "!BENCHMARK_NO_AUTH"  # not a valid bcrypt hash -> cannot auth
STUB_EMAIL_DOMAIN = "@benchmark.flawchess.local"
WINDOW_MONTHS = 36  # D-13: import games from the 36 months before snapshot_month_end

# Terminal statuses: skip on resume
_TERMINAL_STATUSES = {"completed", "skipped", "failed"}

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


def _should_hard_skip(games_count: int) -> bool:
    """D-14: hard-skip users with >= HARD_SKIP_THRESHOLD window-bounded games."""
    return games_count >= HARD_SKIP_THRESHOLD


def compute_deficit_users(pool: list[str], completed: set[str], target_n: int) -> list[str]:
    """Return the next (target_n - completed_in_pool) usernames from pool, in order.

    Skips usernames already in completed. Returns an empty list if target is already
    met. Returns up to len(pool) usernames if the pool is exhausted before the target.

    Args:
        pool: Ordered list of all candidate usernames for the cell.
        completed: Set of usernames that already have a terminal checkpoint status.
        target_n: Target number of users to have in terminal status for this cell.

    Returns:
        List of usernames to import, in pool order.
    """
    completed_in_pool = sum(1 for u in pool if u in completed)
    deficit = target_n - completed_in_pool
    if deficit <= 0:
        return []
    out: list[str] = []
    for u in pool:
        if len(out) >= deficit:
            break
        if u not in completed:
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
    """Insert a 'pending' checkpoint row for a user (idempotent by unique username)."""
    result = await session.execute(
        select(BenchmarkIngestCheckpoint).where(
            BenchmarkIngestCheckpoint.lichess_username == lichess_username
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
    status: str,
    games_imported: int = 0,
    skip_reason: str | None = None,
    benchmark_user_id: int | None = None,
) -> None:
    """Update checkpoint row to a terminal status."""
    result = await session.execute(
        select(BenchmarkIngestCheckpoint).where(
            BenchmarkIngestCheckpoint.lichess_username == lichess_username
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


# --------------------------------------------------------------------------------------
# Per-user import
# --------------------------------------------------------------------------------------


async def _import_one_user(
    lichess_username: str,
    rating_bucket: int,
    tc_bucket: str,
    snapshot_month_end: date,
    dry_run: bool,
) -> tuple[str, int]:
    """Import games for one benchmark user.

    Returns:
        Tuple of (final_status, games_imported).
        final_status: "completed" | "skipped" | "failed"
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

            # Pre-seed a synthetic "previous" import_jobs row so run_import picks up
            # since_ms = window_start. This is the row that get_latest_for_user_platform
            # will return as previous_job, driving since_ms through the existing pipeline.
            # We set last_synced_at = window_start (= snapshot_month_end - 36 months).
            synthetic_job_id = str(uuid.uuid4())
            synthetic_job = ImportJob(
                id=synthetic_job_id,
                user_id=user_id,
                platform="lichess",
                username=lichess_username,
                status="completed",
                games_fetched=0,
                games_imported=0,
                last_synced_at=window_start,
                completed_at=window_start,
            )
            session.add(synthetic_job)
            await session.commit()

        # Create real import job and run it. run_import opens its own session internally.
        job_id = create_job(user_id=user_id, platform="lichess", username=lichess_username)
        await run_import(job_id)

        job_state = get_job(job_id)
        if job_state is None:
            # run_import never re-raises; if job vanished something is very wrong
            raise RuntimeError("Import job state missing after run_import")

        games_imported = job_state.games_imported
        final_status: str

        if _should_hard_skip(games_imported):
            final_status = "skipped"
            _log(
                f"  HARD-SKIP {lichess_username}: {games_imported} games >= {HARD_SKIP_THRESHOLD}"
                f" -- flagging as outlier (D-14)"
            )
            async with async_session_maker() as session:
                await _update_checkpoint(
                    session,
                    lichess_username,
                    status="skipped",
                    games_imported=games_imported,
                    skip_reason="over_20k_games",
                    benchmark_user_id=user_id,
                )
                await session.commit()
        elif job_state.status == "completed":
            final_status = "completed"
            async with async_session_maker() as session:
                await _update_checkpoint(
                    session,
                    lichess_username,
                    status="completed",
                    games_imported=games_imported,
                    benchmark_user_id=user_id,
                )
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
                await _update_checkpoint(session, lichess_username, status="failed")
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
) -> tuple[list[str], set[str]]:
    """Load (pool, completed) for a given cell from the benchmark DB.

    Returns:
        pool: All usernames for this cell (ordered by id).
        completed: Usernames with terminal checkpoint status.
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

    completed_result = await session.execute(
        select(BenchmarkIngestCheckpoint.lichess_username).where(
            BenchmarkIngestCheckpoint.rating_bucket == rating_bucket,
            BenchmarkIngestCheckpoint.tc_bucket == tc_bucket,
            BenchmarkIngestCheckpoint.status.in_(list(_TERMINAL_STATUSES)),
        )
    )
    completed = set(completed_result.scalars().all())

    return pool, completed


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

    # Load per-cell deficit
    cell_plans: list[
        tuple[int, str, list[str], int]
    ] = []  # (rating_bucket, tc_bucket, to_import, completed_count)
    async with async_session_maker() as session:
        for rating_bucket, tc_bucket in sorted(cells):
            pool, completed = await _load_cell_data(session, rating_bucket, tc_bucket)
            to_import = compute_deficit_users(
                pool=pool, completed=completed, target_n=args.per_cell
            )
            cell_plans.append((rating_bucket, tc_bucket, to_import, len(completed)))

    # Print plan
    _log()
    _log(f"Benchmark ingest plan (--per-cell {args.per_cell}):")
    total_to_import = 0
    for rating_bucket, tc_bucket, to_import, completed_count in cell_plans:
        _log(
            f"  cell ({rating_bucket}, {tc_bucket}): "
            f"{completed_count} completed, would import {len(to_import)} more"
        )
        total_to_import += len(to_import)
    _log(f"Total users to import: {total_to_import}")
    _log()

    if args.dry_run:
        _log("Dry-run mode -- no imports performed.")
        return

    # Confirmation prompt (unless --yes)
    if not args.yes:
        response = input(f"Import games for {total_to_import} benchmark users? Proceed? [y/N] ")
        if response.strip().lower() not in ("y", "yes"):
            _log("Aborted.")
            return

    # Execute per-cell import
    total_completed = 0
    total_skipped = 0
    total_failed = 0
    total_pending = 0

    for rating_bucket, tc_bucket, to_import, _completed_count in cell_plans:
        if _stop_requested:
            _log("Stop requested -- exiting after current cell.")
            break

        _log(f"Cell ({rating_bucket}, {tc_bucket}): importing {len(to_import)} users...")

        for username in to_import:
            if _stop_requested:
                _log("  Stop requested -- skipping remaining users in cell.")
                total_pending += 1
                continue

            _log(f"  Importing {username}...")
            final_status, games_imported = await _import_one_user(
                lichess_username=username,
                rating_bucket=rating_bucket,
                tc_bucket=tc_bucket,
                snapshot_month_end=args.snapshot_month_end,
                dry_run=False,
            )
            if final_status == "completed":
                total_completed += 1
                _log(f"  Done: {username} -- {games_imported} games imported.")
            elif final_status == "skipped":
                total_skipped += 1
            else:
                total_failed += 1

    elapsed = time.time() - start_time
    _log()
    _log("Benchmark ingest complete:")
    _log(f"  Completed: {total_completed}")
    _log(f"  Skipped (outlier): {total_skipped}")
    _log(f"  Failed: {total_failed}")
    _log(f"  Pending (interrupted): {total_pending}")
    _log(f"  Duration: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
