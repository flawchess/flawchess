"""Import router: POST /imports and GET /imports/{job_id} endpoints.

HTTP layer only — all orchestration logic lives in import_service.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories import import_job_repository
from app.schemas.imports import ImportRequest, ImportStartedResponse, ImportStatusResponse
from app.services import import_service

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportStartedResponse, status_code=201)
async def start_import(
    request: ImportRequest,
    response: Response,
) -> ImportStartedResponse:
    """Trigger a background import from chess.com or lichess.

    Returns immediately with a job_id that can be polled via GET /imports/{job_id}.

    If an import for this user+platform is already PENDING or IN_PROGRESS,
    the existing job is returned with HTTP 200 instead of creating a duplicate.

    TODO: Replace hardcoded user_id=1 with real authenticated user once Phase 4
    FastAPI-Users auth is wired up.
    """
    # TODO(phase-4): Replace with real authenticated user_id from FastAPI-Users.
    user_id = 1

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
