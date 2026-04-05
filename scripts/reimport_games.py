"""Re-import games for user(s) to populate engine analysis data.

Processes users sequentially: for each user, deletes their existing games
and positions, then re-imports from scratch before moving on to the next
user. Uses the updated pipeline (which now extracts lichess per-move evals
and chess.com accuracy scores).

If the script fails or is interrupted mid-run, earlier users are fully
re-imported, the current user may be partially done, and later users are
left untouched.

Usage (local dev):
    uv run python scripts/reimport_games.py --user-id 42
    uv run python scripts/reimport_games.py --all --yes

Usage (production):
    The runtime image has no `uv` on the host — run inside the backend
    container using the venv's Python directly:

        ssh flawchess "cd /opt/flawchess && docker compose exec backend /app/.venv/bin/python scripts/reimport_games.py --user-id 42"
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sentry_sdk
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.import_job import ImportJob
from app.models.oauth_account import OAuthAccount  # noqa: F401 — required for User relationship resolution
from app.models.user import User
from app.repositories import game_repository
from app.services.import_service import create_job, get_job, run_import

_BATCH_SIZE = 10  # games per DB commit — OOM-safe (STATE.md critical constraint)


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments.

    Returns:
        Parsed args namespace with user_id, all, and yes fields.
    """
    parser = argparse.ArgumentParser(
        description="Re-import games for user(s) to backfill engine analysis data."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--user-id",
        type=int,
        metavar="N",
        help="Re-import games for a single user with this ID.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        dest="all_users",
        help="Re-import games for all users.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately.",
    )
    return parser.parse_args()


async def get_all_user_ids(session) -> list[int]:
    """Return all user IDs in the database."""
    result = await session.execute(select(User.id))
    return list(result.scalars().all())


async def get_platform_jobs_for_user(
    session, user_id: int
) -> list[tuple[str, str]]:
    """Return (platform, username) pairs for all completed import jobs for the user.

    Returns unique (platform, username) pairs — uses the most recent completed job
    per platform to avoid re-importing the same username twice.

    Args:
        session: AsyncSession to use.
        user_id: Internal user ID.

    Returns:
        List of (platform, username) tuples, e.g. [("chess.com", "alice"), ("lichess", "alice")]
    """
    result = await session.execute(
        select(ImportJob.platform, ImportJob.username)
        .where(
            ImportJob.user_id == user_id,
            ImportJob.status == "completed",
        )
        .distinct()
    )
    return list(result.fetchall())


async def reimport_user(session, user_id: int) -> tuple[bool, int]:
    """Delete and re-import all games for a single user.

    Args:
        session: AsyncSession to use.
        user_id: Internal user ID to re-import.

    Returns:
        (success, games_imported) tuple. success=False if an error occurred.
    """
    # Find which platforms the user has imported from
    platform_jobs = await get_platform_jobs_for_user(session, user_id)
    if not platform_jobs:
        _log(f"  User {user_id}: no completed import jobs found — skipping.")
        return True, 0

    # Count current games before deletion
    game_count = await game_repository.count_games_for_user(session, user_id)
    platform_list = ", ".join(f"{p} ({u})" for p, u in platform_jobs)
    _log(
        f"  User {user_id}: {game_count} games across: {platform_list}. "
        f"This will DELETE all games and re-import from scratch."
    )

    # Delete all games for the user
    _log(f"  Deleting {game_count} games for user {user_id}...")
    deleted_count = await game_repository.delete_all_games_for_user(session, user_id)

    # Delete all completed import jobs for this user. The (platform, username)
    # pairs have already been read into platform_jobs above, and create_job()
    # below will create fresh rows for each re-import. Without this, each run
    # leaves stale completed jobs behind (verified in prod: a single user had
    # 3 jobs per platform after one reimport + one regular sync). This also
    # fixes an older bug where lichess re-imports returned 0 games because the
    # old last_synced_at told the client nothing was new since last import.
    await session.execute(
        delete(ImportJob)
        .where(ImportJob.user_id == user_id, ImportJob.status == "completed")
    )

    await session.commit()
    _log(f"  Deleted {deleted_count} games.")

    # Re-import from each platform
    total_imported = 0
    any_platform_failed = False
    for platform, username in platform_jobs:
        _log(f"  Re-importing from {platform} ({username})...")
        try:
            job_id = create_job(user_id=user_id, platform=platform, username=username)
            await run_import(job_id)

            # Check the import result from in-memory job state
            job_state = get_job(job_id)
            if job_state is not None:
                if job_state.status == "completed":
                    total_imported += job_state.games_imported
                    _log(
                        f"  Done: {job_state.games_imported} games imported from {platform}."
                    )
                else:
                    any_platform_failed = True
                    error_msg = job_state.error or "Unknown error"
                    _log(f"  FAILED: Import from {platform} failed: {error_msg}")
        except Exception as e:
            any_platform_failed = True
            _log(f"  FAILED: Re-import from {platform} failed with exception: {e}")

    return not any_platform_failed, total_imported


async def main() -> None:
    """Run the re-import script: delete games for user(s) and re-import via updated pipeline."""
    # Initialize Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    args = parse_args()
    start_time = time.time()

    # Determine target user IDs
    async with async_session_maker() as session:
        if args.all_users:
            user_ids = await get_all_user_ids(session)
            target_label = f"all {len(user_ids)} users"
        else:
            user_ids = [args.user_id]
            target_label = f"user {args.user_id}"

    if not user_ids:
        _log("No users found. Exiting.")
        return

    _log(f"Re-import script: targeting {target_label}")
    _log(f"Batch size: {_BATCH_SIZE} games per commit")
    _log()

    # Confirm before proceeding (unless --yes flag given)
    if not args.yes:
        response = input(
            f"This will DELETE all games for {target_label} and re-import from scratch. "
            f"Proceed? [y/N] "
        )
        if response.strip().lower() not in ("y", "yes"):
            _log("Aborted.")
            return

    # Process each user
    total_success = 0
    total_failed = 0
    total_games_imported = 0

    for user_id in user_ids:
        try:
            async with async_session_maker() as session:
                success, games_imported = await reimport_user(session, user_id)
                if success:
                    total_success += 1
                    total_games_imported += games_imported
                else:
                    total_failed += 1
        except Exception as e:
            sentry_sdk.capture_exception(e)
            _log(f"  ERROR: User {user_id} failed: {e}")
            total_failed += 1

    elapsed = time.time() - start_time
    _log()
    _log("Re-import complete:")
    _log(f"  Users processed successfully: {total_success}")
    _log(f"  Users failed: {total_failed}")
    _log(f"  Total games imported: {total_games_imported}")
    _log(f"  Duration: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
