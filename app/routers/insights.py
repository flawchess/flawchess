"""Insights router: LLM endgame insights and filter-scoped opening insights.

Endpoints (mounted under /api):
- POST /insights/endgame: returns EndgameInsightsResponse with the LLM report.
- GET /insights/endgame/cached: the user's latest stored report (never
  invalidated; a 404 means no report exists yet, which triggers the frontend's
  one-time auto-generate).
- POST /insights/openings: filter-scoped opening insights (no LLM).

The router is deliberately thin: all cache / LLM-call / logging logic lives in
app.services.insights_llm.generate_insights(). This router: auth + session dep + one service
call + exception-to-HTTP status mapping.

The endgame insights are filter-independent. Both endpoints declare NO filter parameters
(FastAPI ignores undeclared query parameters, so a client that still sends the page filters
gets the same one-per-user report), and the former v8 filter gate (400
filters_not_supported) is gone. The report narrates the ranked sample that the Stats tab
shows, so there is nothing for a filter to scope.
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
from app.services import insights_llm
from app.services.insights_llm import (
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

    Takes no filter parameters: one report per user, built from
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
    """Return the user's latest stored report, without invoking the LLM.

    Unlike the POST path, the report is never invalidated by a newer import or by
    age: the frontend auto-generates only when this returns 404,
    so only the first report is generated automatically and every later refresh is
    an explicit "Update Insights" click. Consumes no rate-limit budget.

    Takes no filter parameters; the lookup key is (user_id, prompt_version, model,
    INSIGHTS_CACHE_OPPONENT_STRENGTH).

    Returns:
        200: EndgameInsightsResponse(status='cache_hit') with the latest report.
        404: when the user has no report for the current prompt version and model.
    """
    response = await insights_llm.get_latest_insights_response(session, user.id)
    if response is None:
        raise HTTPException(status_code=404, detail="no_cached_report")
    return response


@router.post("/openings", response_model=OpeningInsightsResponse)
async def get_opening_insights(
    request: OpeningInsightsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OpeningInsightsResponse:
    """Opening insights — POST /api/insights/openings.

    Authenticated, user-scoped. Returns a four-section
    OpeningInsightsResponse under the active filter set.

    Every filter reshapes findings (unlike the filter-free endgame insights
    routes above).
    """
    return await compute_insights(
        session=session,
        user_id=user.id,
        request=request,
    )
