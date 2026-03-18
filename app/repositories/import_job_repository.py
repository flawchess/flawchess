"""Import job repository: CRUD for the import_jobs table."""

from sqlalchemy import select
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
    result = await session.execute(
        select(ImportJob).where(ImportJob.id == job_id)
    )
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
