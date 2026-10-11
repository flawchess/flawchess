"""Insights router: HTTP endpoints for LLM-generated endgame insights.

Endpoints (mounted under /api):
- POST /insights/endgame: returns EndgameInsightsResponse with the LLM report.
- GET /insights/endgame/cached: cache-only lookup of the stored report.

The router is deliberately thin per CONTEXT.md D-33: all cache /
LLM-call / logging logic lives in app.services.insights_llm.generate_insights().
This router: auth + session dep + one service call + exception-to-HTTP status
mapping (D-16).

Phase 238 (D-04): the endgame insights are filter-independent. Both endpoints
declare NO filter parameters (FastAPI ignores undeclared query parameters, so a
client that still sends the page filters gets the same one-per-user report), and
the former v8 filter gate (400 filters_not_supported) is gone. The report narrates
the ranked sample that the Stats tab shows, so there is nothing for a filter to
scope.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.insights import (
    EndgameInsightsResponse,
    InsightsErrorResponse,
)
from app.schemas.opening_insights import (
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.core.config import settings
from app.repositories.import_job_repository import (
    get_latest_completed_import_with_games_at,
)
from app.repositories.llm_log_repository import get_latest_successful_log_for_user
from app.schemas.insights import EndgameInsightsReport
from app.services import insights_llm
from app.services.insights_llm import (
    INSIGHTS_CACHE_MAX_AGE,
    INSIGHTS_CACHE_OPPONENT_STRENGTH,
    InsightsProviderError,
    InsightsValidationFailure,
)
from app.services.opening_insights_service import compute_insights
from app.users import current_active_user

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/endgame", response_model=EndgameInsightsResponse)
async def get_endgame_insights(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> EndgameInsightsResponse | JSONResponse:
    """Return the LLM-generated EndgameInsightsReport for the authenticated user.

    Takes no filter parameters (Phase 238 D-04): one report per user, built from
    the same ranked sample the Stats tab shows. Undeclared query parameters are
    ignored by FastAPI, so a client that still sends the page filters receives
    the identical response.

    Returns:
        200: EndgameInsightsResponse with status in {fresh, cache_hit}.
        502: InsightsErrorResponse(error='provider_error' | 'validation_failure').
    """
    try:
        return await insights_llm.generate_insights(user.id, session)
    except InsightsValidationFailure:
        return JSONResponse(
            status_code=502,
            content=InsightsErrorResponse(
                error="validation_failure",
            ).model_dump(),
        )
    except InsightsProviderError:
        return JSONResponse(
            status_code=502,
            content=InsightsErrorResponse(
                error="provider_error",
            ).model_dump(),
        )


@router.get("/endgame/cached", response_model=EndgameInsightsResponse)
async def get_cached_endgame_insights(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> EndgameInsightsResponse:
    """Cache-only lookup of the Tier-1 structural insights cache.

    Mirrors the Tier-1 logic from `app.services.insights_llm.generate_insights`
    without invoking compute_findings or the LLM, and without consuming any
    rate-limit budget. Used by the frontend to auto-render a previously-generated
    report when the Endgames page mounts.

    Takes no filter parameters (Phase 238 D-04); the cache key is
    (user_id, prompt_version, model, INSIGHTS_CACHE_OPPONENT_STRENGTH).

    Returns:
        200: EndgameInsightsResponse(status='cache_hit') when a fresh,
             non-stale (no qualifying import since written) cache row exists.
        404: when no qualifying cache row exists.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS
    cached = await get_latest_successful_log_for_user(
        session,
        user_id=user.id,
        prompt_version=insights_llm._PROMPT_VERSION,
        model=model,
        opponent_strength=INSIGHTS_CACHE_OPPONENT_STRENGTH,
        max_age=INSIGHTS_CACHE_MAX_AGE,
    )
    if cached is None:
        raise HTTPException(status_code=404, detail="no_cached_report")

    last_import_at = await get_latest_completed_import_with_games_at(session, user.id)
    if last_import_at is not None and last_import_at > cached.created_at:
        raise HTTPException(status_code=404, detail="no_cached_report")

    report = EndgameInsightsReport.model_validate(cached.response_json)
    return EndgameInsightsResponse(
        report=insights_llm._maybe_strip_overview(report),
        status="cache_hit",
    )


@router.post("/openings", response_model=OpeningInsightsResponse)
async def get_opening_insights(
    request: OpeningInsightsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OpeningInsightsResponse:
    """Phase 70 (v1.13) opening insights — POST /api/insights/openings.

    Authenticated, user-scoped. Returns a four-section
    OpeningInsightsResponse under the active filter set.

    Per CONTEXT.md D-14, every filter reshapes findings (unlike the filter-free
    endgame insights routes above, Phase 238 D-04).
    """
    return await compute_insights(
        session=session,
        user_id=user.id,
        request=request,
    )
