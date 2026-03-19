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
from app.repositories import game_repository, import_job_repository
from app.schemas.imports import ImportRequest, ImportStartedResponse, ImportStatusResponse
from app.services import import_service
from app.users import current_active_user

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportStartedResponse, status_code=201)
async def start_import(
    request: ImportRequest,
    response: Response,
    user: Annotated[User, Depends(current_active_user)],
) -> ImportStartedResponse:
    """Trigger a background import from chess.com or lichess.

    Returns immediately with a job_id that can be polled via GET /imports/{job_id}.

    If an import for this user+platform is already PENDING or IN_PROGRESS,
    the existing job is returned with HTTP 200 instead of creating a duplicate.
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

    job_id = import_service.create_job(user_id, request.platform, request.username)
    asyncio.create_task(import_service.run_import(job_id))

    return ImportStartedResponse(job_id=job_id, status="pending")


@router.get("/active", response_model=list[ImportStatusResponse])
async def get_active_imports(
    user: Annotated[User, Depends(current_active_user)],
) -> list[ImportStatusResponse]:
    """Return all active (PENDING or IN_PROGRESS) import jobs for the authenticated user.

    Only checks in-memory registry — completed/failed jobs are not returned.
    After a server restart in-memory jobs are gone, which is correct (background
    tasks are also gone at that point).
    """
    jobs = import_service.find_active_jobs_for_user(user.id)
    return [
        ImportStatusResponse(
            job_id=job.job_id,
            platform=job.platform,
            username=job.username,
            status=job.status.value,
            games_fetched=job.games_fetched,
            games_imported=job.games_imported,
            error=job.error,
        )
        for job in jobs
    ]


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
        )

    # Fall back to DB for historical jobs
    db_job = await import_job_repository.get_import_job(session, job_id)
    if db_job is not None:
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


@router.delete("/games")
async def delete_all_games(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    """Delete all games, positions, and import jobs for the authenticated user.

    Returns the count of deleted games.
    """
    deleted_count = await game_repository.delete_all_games_for_user(session, user.id)
    await session.execute(delete(ImportJob).where(ImportJob.user_id == user.id))
    await session.commit()
    return {"deleted_count": deleted_count}
