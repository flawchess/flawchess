"""Import router: POST /imports and GET /imports/{job_id} endpoints.

HTTP layer only — all orchestration logic lives in import_service.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.import_job import ImportJob
from app.models.user import User
from app.models.user_benchmark_percentile import UserBenchmarkPercentile
from app.models.user_rating_anchors import UserRatingAnchor
from app.repositories import (
    game_repository,
    import_job_repository,
    user_benchmark_percentiles_repository,
    user_repository,
)
from app.schemas.imports import (
    DeleteGamesResponse,
    EvalCoverageResponse,
    ImportRequest,
    ImportStartedResponse,
    ImportStatusResponse,
    ReadinessResponse,
)
from app.services import import_service, percentile_compute_registry
from app.users import current_active_user

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportStartedResponse, status_code=201)
async def start_import(
    request: ImportRequest,
    response: Response,
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImportStartedResponse:
    """Trigger a background import from chess.com or lichess.

    Returns immediately with a job_id that can be polled via GET /imports/{job_id}.

    If an import for this user+platform is already PENDING or IN_PROGRESS,
    the existing job is returned with HTTP 200 instead of creating a duplicate.

    Platform username is saved to user profile immediately at import start (not
    at completion), so that after a server restart the Import page pre-populates
    the username field and the Sync button is enabled even if the import failed.
    """
    # Extract user_id before asyncio.create_task — Depends only works in request scope
    user_id = user.id

    # Return existing active job instead of starting a duplicate
    existing = import_service.find_active_job(user_id, request.platform)
    if existing is not None:
        response.status_code = 200
        return ImportStartedResponse(
            job_id=existing.job_id,
            status=existing.status.value,
        )

    # Save platform username to user profile immediately — ensures the username
    # persists even if the import fails mid-way or the server restarts, so the
    # Import page can pre-populate the username field for immediate re-sync.
    await user_repository.update_platform_username(
        session, user_id, request.platform, request.username
    )
    await session.commit()

    job_id = import_service.create_job(user_id, request.platform, request.username)
    asyncio.create_task(import_service.run_import(job_id))

    return ImportStartedResponse(job_id=job_id, status="pending")


@router.get("/active", response_model=list[ImportStatusResponse])
async def get_active_imports(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ImportStatusResponse]:
    """Return import jobs the frontend should display for the authenticated user.

    Includes:
    - In-memory active jobs (PENDING/IN_PROGRESS) — live imports in this session
    - Recently failed DB jobs (last 24h) — surfaces errors from server restarts
      that the user hasn't seen yet (in-memory registry is empty after restart)
    """
    results: list[ImportStatusResponse] = []
    seen_job_ids: set[str] = set()

    # In-memory active jobs
    for job in import_service.find_active_jobs_for_user(user.id):
        seen_job_ids.add(job.job_id)
        results.append(
            ImportStatusResponse(
                job_id=job.job_id,
                platform=job.platform,
                username=job.username,
                status=job.status.value,
                games_fetched=job.games_fetched,
                games_imported=job.games_imported,
                error=job.error,
                other_importers=import_service.count_active_platform_jobs(
                    job.platform, job.user_id
                ),
            )
        )

    # Recently failed DB jobs (e.g. orphaned after server restart)
    failed_jobs = await import_job_repository.get_unseen_failed_jobs_for_user(session, user.id)
    for db_job in failed_jobs:
        if db_job.id in seen_job_ids:
            continue
        results.append(
            ImportStatusResponse(
                job_id=db_job.id,
                platform=db_job.platform,
                username=db_job.username,
                status=db_job.status,
                games_fetched=db_job.games_fetched,
                games_imported=db_job.games_imported,
                error=db_job.error_message,
            )
        )

    return results


@router.get("/readiness", response_model=ReadinessResponse)
async def get_readiness(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReadinessResponse:
    """Return two-tier readiness for the authenticated user.

    Locked by D-01/D-04: dedicated endpoint; keys tier1, tier2, pending_count,
    total_count.

    Tier 1 (tier1=True): no active import job in-flight for this user.
        Derived from the in-memory import registry only — orphaned DB jobs
        after server restart are not detected here (RESEARCH Open Question 1 /
        A3, out of scope).

    Tier 2 (tier2=True): tier1=True AND pending evals == 0 AND
        (total_count == 0 OR at least one user_benchmark_percentiles row exists)
        AND the user is not mid-Stage-B percentile compute (in-memory registry).
        The ``total_count == 0`` branch is the below-floor escape: a user with
        no games is vacuously Stage-B ready and must not be locked out forever
        (RESEARCH Pitfall 1). The Stage-B-computing clause (Quick 260529-015)
        closes the race where pending==0 is observed before the eval-dependent
        percentile rows are written, so the page would otherwise unlock with
        missing (first import) or stale (re-import) badges.

    Reads are strictly sequential on one AsyncSession per CLAUDE.md constraint
    (no asyncio.gather on a single AsyncSession). Short-circuits skip downstream
    queries when not needed, bounding the query count to at most 3. The
    is_computing check is a sync in-memory set lookup (no query), so it does not
    affect that bound.
    """
    # Tier 1: no active import job for this user (in-memory check only)
    has_active = bool(import_service.find_active_jobs_for_user(user.id))
    tier1 = not has_active

    # Quick 260529-015: in-memory Stage-B-in-progress gate (sync set lookup).
    stage_b_computing = percentile_compute_registry.is_computing(user.id)

    # Total games (needed for tier2 and pending_count)
    total = await game_repository.count_games_for_user(session, user.id)

    # Skip pending eval count when tier1=False (no point during active import)
    pending = 0 if not tier1 else await game_repository.count_pending_evals(session, user.id)

    # Skip has_any_rows when total==0 (vacuously ready) or tier1=False
    percentile_ready = total == 0 or (
        tier1 and await user_benchmark_percentiles_repository.has_any_rows(session, user_id=user.id)
    )

    tier2 = tier1 and pending == 0 and percentile_ready and not stage_b_computing

    return ReadinessResponse(
        tier1=tier1,
        tier2=tier2,
        pending_count=pending,
        total_count=total,
    )


@router.get("/eval-coverage", response_model=EvalCoverageResponse)
async def get_eval_coverage(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EvalCoverageResponse:
    """Return Stockfish eval coverage for the authenticated user.

    Returns pending_count, total_count, and pct_complete (0-100).
    Returns pct_complete=100 when the user has no games (avoids division-by-zero).

    Locked by D-01: dedicated endpoint, NOT extending GET /imports/active.
    Locked by D-04: response keys are pending_count, total_count, pct_complete.
    """
    total = await game_repository.count_games_for_user(session, user.id)
    if total == 0:
        return EvalCoverageResponse(pending_count=0, total_count=0, pct_complete=100)
    pending = await game_repository.count_pending_evals(session, user.id)
    pct = round(100 * (total - pending) / total)
    return EvalCoverageResponse(pending_count=pending, total_count=total, pct_complete=pct)


@router.get("/{job_id}", response_model=ImportStatusResponse)
async def get_import_status(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImportStatusResponse:
    """Return the current progress of an import job.

    Checks in-memory registry first (live jobs), then falls back to the database
    (for completed/failed jobs that may have been evicted from memory after restart).
    """
    # Try in-memory registry first (live progress)
    job = import_service.get_job(job_id)
    if job is not None:
        return ImportStatusResponse(
            job_id=job.job_id,
            platform=job.platform,
            username=job.username,
            status=job.status.value,
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
            error=job.error,
            other_importers=import_service.count_active_platform_jobs(job.platform, job.user_id),
        )

    # Fall back to DB for historical jobs
    db_job = await import_job_repository.get_import_job(session, job_id)
    if db_job is not None:
        # other_importers=0 is correct for completed/failed jobs — count is irrelevant
        return ImportStatusResponse(
            job_id=db_job.id,
            platform=db_job.platform,
            username=db_job.username,
            status=db_job.status,
            games_fetched=db_job.games_fetched,
            games_imported=db_job.games_imported,
            error=db_job.error_message,
        )

    raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/games", response_model=DeleteGamesResponse)
async def delete_all_games(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DeleteGamesResponse:
    """Delete all games, positions, import jobs, benchmark percentiles, and
    rating anchors for the authenticated user.

    Returns the count of deleted games.
    """
    deleted_count = await game_repository.delete_all_games_for_user(session, user.id)
    await session.execute(delete(ImportJob).where(ImportJob.user_id == user.id))
    await session.execute(
        delete(UserBenchmarkPercentile).where(UserBenchmarkPercentile.user_id == user.id)
    )
    await session.execute(delete(UserRatingAnchor).where(UserRatingAnchor.user_id == user.id))
    await session.commit()
    return DeleteGamesResponse(deleted_count=deleted_count)
