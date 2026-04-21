"""Insights router: HTTP endpoint for LLM-generated endgame insights.

Endpoint (mounted under /api):
- POST /insights/endgame: returns EndgameInsightsResponse with the LLM report.

The router is deliberately thin per CONTEXT.md D-33 — all cache / rate-limit /
LLM-call / logging logic lives in app.services.insights_llm.generate_insights().
This router: auth + session dep + query-param-to-FilterContext + one service
call + exception-to-HTTP status mapping (D-16).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.insights import (
    EndgameInsightsResponse,
    FilterContext,
    InsightsErrorResponse,
)
from app.services import insights_llm
from app.services.insights_llm import (
    InsightsProviderError,
    InsightsRateLimitExceeded,
    InsightsValidationFailure,
)
from app.users import current_active_user

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("/endgame", response_model=EndgameInsightsResponse)
async def get_endgame_insights(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: Literal[
        "all_time", "week", "month", "3months", "6months", "year", "3years", "5years"
    ] = Query(default="all_time"),
    rated: bool | None = Query(default=None),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    color: Literal["all", "white", "black"] = Query(default="all"),
) -> EndgameInsightsResponse | JSONResponse:
    """Return the LLM-generated EndgameInsightsReport for the authenticated user.

    Query params mirror /api/endgames/overview so the Phase 66 frontend can share
    query-string builders with useEndgames.ts (D-31). `color` and `rated_only`
    flow into findings but NOT into the LLM prompt (INS-03).

    Returns:
        200: EndgameInsightsResponse with status in {fresh, cache_hit, stale_rate_limited}.
        429: InsightsErrorResponse(error='rate_limit_exceeded', retry_after_seconds=N).
        502: InsightsErrorResponse(error='provider_error' | 'validation_failure').
    """
    filter_context = FilterContext(
        recency=recency,
        opponent_strength=opponent_strength,
        color=color,
        time_controls=time_control or [],
        platforms=platform or [],
        rated_only=bool(rated) if rated is not None else False,
    )
    try:
        return await insights_llm.generate_insights(filter_context, user.id, session)
    except InsightsRateLimitExceeded as exc:
        return JSONResponse(
            status_code=429,
            content=InsightsErrorResponse(
                error="rate_limit_exceeded",
                retry_after_seconds=exc.retry_after_seconds,
            ).model_dump(),
        )
    except InsightsValidationFailure:
        return JSONResponse(
            status_code=502,
            content=InsightsErrorResponse(
                error="validation_failure",
                retry_after_seconds=None,
            ).model_dump(),
        )
    except InsightsProviderError:
        return JSONResponse(
            status_code=502,
            content=InsightsErrorResponse(
                error="provider_error",
                retry_after_seconds=None,
            ).model_dump(),
        )
