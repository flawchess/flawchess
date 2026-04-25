"""Import job repository: CRUD for the import_jobs table."""

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob


async def create_import_job(
    session: AsyncSession,
    job_id: str,
    user_id: int,
    platform: str,
    username: str,
) -> ImportJob:
    """Create a new ImportJob row with status='pending'.

    Args:
        session: AsyncSession to use.
        job_id: UUID string for the job (caller generates this).
        user_id: Internal user ID.
        platform: 'chess.com' or 'lichess'.
        username: Platform username to import from.

    Returns:
        The newly created ImportJob instance.
    """
    job = ImportJob(
        id=job_id,
        user_id=user_id,
        platform=platform,
        username=username,
        status="pending",
        games_fetched=0,
        games_imported=0,
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


async def update_import_job(session: AsyncSession, job_id: str, **kwargs) -> None:
    """Update specified fields on an existing ImportJob row.

    Args:
        session: AsyncSession to use.
        job_id: The UUID of the job to update.
        **kwargs: Field names and values to update (e.g., status='completed').
    """
    job = await get_import_job(session, job_id)
    if job is None:
        return
    for key, value in kwargs.items():
        setattr(job, key, value)
    await session.flush()


async def get_import_job(session: AsyncSession, job_id: str) -> ImportJob | None:
    """Fetch an ImportJob by its ID.

    Args:
        session: AsyncSession to use.
        job_id: The UUID of the job.

    Returns:
        ImportJob instance or None if not found.
    """
    result = await session.execute(select(ImportJob).where(ImportJob.id == job_id))
    return result.scalar_one_or_none()


async def get_latest_for_user_platform(
    session: AsyncSession,
    user_id: int,
    platform: str,
    username: str,
) -> ImportJob | None:
    """Return the most recent completed ImportJob for a user+platform+username combination.

    Used for incremental sync: the returned job's last_synced_at provides
    the 'since' timestamp for fetching only new games. Scoped to username so
    that importing a second username on the same platform starts a full fetch
    independently.

    Args:
        session: AsyncSession to use.
        user_id: Internal user ID.
        platform: 'chess.com' or 'lichess'.
        username: Platform username (case-sensitive as stored in ImportJob).

    Returns:
        The most recent completed ImportJob or None if no completed jobs exist.
    """
    result = await session.execute(
        select(ImportJob)
        .where(
            ImportJob.user_id == user_id,
            ImportJob.platform == platform,
            ImportJob.username == username,
            ImportJob.status == "completed",
        )
        .order_by(ImportJob.completed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_unseen_failed_jobs_for_user(
    session: AsyncSession,
    user_id: int,
) -> list[ImportJob]:
    """Return recently failed jobs that the user hasn't resolved yet.

    Only returns a failed job if it's the most recent job for that platform —
    i.e., no newer completed (or other) job exists. Once the user successfully
    re-syncs, the failed job is superseded and no longer shown.

    Also filtered to the last 24 hours to avoid surfacing ancient failures.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func as sa_func

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    # Subquery: the most recent job (any status) per platform for this user
    latest_per_platform = (
        select(
            ImportJob.platform,
            sa_func.max(ImportJob.started_at).label("max_started"),
        )
        .where(ImportJob.user_id == user_id)
        .group_by(ImportJob.platform)
        .subquery()
    )

    # Join: only return the job if it's both the latest AND failed
    result = await session.execute(
        select(ImportJob)
        .join(
            latest_per_platform,
            (ImportJob.platform == latest_per_platform.c.platform)
            & (ImportJob.started_at == latest_per_platform.c.max_started),
        )
        .where(
            ImportJob.user_id == user_id,
            ImportJob.status == "failed",
            ImportJob.completed_at >= cutoff,
        )
    )
    return list(result.scalars().all())


async def fail_orphaned_jobs(session: AsyncSession) -> int:
    """Mark any pending/in_progress jobs as failed (orphaned after server restart).

    Returns:
        Number of jobs marked as failed.
    """
    result = await session.execute(
        update(ImportJob)
        .where(ImportJob.status.in_(["pending", "in_progress"]))
        .values(
            status="failed",
            error_message="Server restarted while import was in progress",
            completed_at=datetime.now(timezone.utc),
        )
    )
    await session.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]  # SQLAlchemy async execute returns Result; rowcount is available on DML results


async def get_last_completed_at_by_platform(
    session: AsyncSession, user_id: int
) -> dict[str, datetime]:
    """Return MAX(completed_at) per platform for the user's completed imports.

    Used by the profile endpoint to render "last sync: X ago" labels in the
    Import tab. Returns a dict keyed by platform ('chess.com', 'lichess');
    platforms with no completed import are absent from the result.
    """
    result = await session.execute(
        select(ImportJob.platform, func.max(ImportJob.completed_at))
        .where(
            ImportJob.user_id == user_id,
            ImportJob.status == "completed",
        )
        .group_by(ImportJob.platform)
    )
    return {platform: ts for platform, ts in result.all() if ts is not None}


async def get_latest_completed_import_with_games_at(
    session: AsyncSession, user_id: int
) -> datetime | None:
    """Return MAX(completed_at) for the user's completed imports that fetched
    new games (games_imported > 0), or None if none exist.

    Used as the cache-invalidation timestamp for the structural insights cache
    (260425-dxh): a cached LLM log row is invalid iff its created_at is older
    than this timestamp. No-op resyncs (games_imported = 0) are intentionally
    excluded so daily syncs that fetch zero games do NOT bust the cache.
    """
    result = await session.execute(
        select(func.max(ImportJob.completed_at)).where(
            ImportJob.user_id == user_id,
            ImportJob.status == "completed",
            ImportJob.games_imported > 0,
        )
    )
    return result.scalar_one_or_none()
