"""Insights router: HTTP endpoint for LLM-generated endgame insights.

Endpoint (mounted under /api):
- POST /insights/endgame: returns EndgameInsightsResponse with the LLM report.

The router is deliberately thin per CONTEXT.md D-33 — all cache / rate-limit /
LLM-call / logging logic lives in app.services.insights_llm.generate_insights().
This router: auth + session dep + query-param-to-FilterContext + one service
call + exception-to-HTTP status mapping (D-16).

v8: reject requests with any non-default filter other than opponent_strength
(400) so a report is only generated over the user's full history. Frontend
already disables the button in these cases; the server-side check is a
defensive safety net against callers that bypass the UI.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.insights import (
    EndgameInsightsResponse,
    FilterContext,
    InsightsErrorResponse,
)
from app.schemas.opening_insights import (
    OpeningInsightsRequest,
    OpeningInsightsResponse,
)
from app.services import insights_llm
from app.services.insights_llm import (
    InsightsProviderError,
    InsightsRateLimitExceeded,
    InsightsValidationFailure,
)
from app.core.opponent_strength import derive_preset
from app.services.opening_insights_service import compute_insights
from app.users import current_active_user

router = APIRouter(prefix="/insights", tags=["insights"])


def _validate_full_history_filters(filters: FilterContext) -> None:
    """Raise 400 when any filter other than opponent_strength is non-default.

    v8 allows only opponent_strength to vary — it genuinely changes which
    games feed the findings, so it's a legitimate cross-section. All other
    filters (recency, time controls, platforms, rated) truncate the dataset
    and would produce a partial report that doesn't match the system
    prompt's "your full history" framing.

    `color` is intentionally NOT gated here — it's ignored by the findings
    pipeline (compute_findings doesn't forward it), so the frontend's
    `color='white'` default has no effect on the report.
    """
    blocking: list[str] = []
    if filters.recency != "all_time":
        blocking.append("Switch Recency to All time")
    if filters.time_controls:
        blocking.append("Remove Time control filter")
    if filters.platforms:
        blocking.append("Remove Platform filter")
    if filters.rated_only:
        blocking.append("Remove Rated filter")
    if blocking:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "filters_not_supported",
                "message": (
                    "Insights can only be generated for your full game history. "
                    + blocking[0]
                    + "."
                ),
                "blocking": blocking,
            },
        )


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
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: Literal["all", "white", "black"] = Query(default="all"),
) -> EndgameInsightsResponse | JSONResponse:
    """Return the LLM-generated EndgameInsightsReport for the authenticated user.

    Query params mirror /api/endgames/overview so the Phase 66 frontend can share
    query-string builders with useEndgames.ts (D-31). `color` and `rated_only`
    flow into findings but NOT into the LLM prompt (INS-03). v8: all filters
    other than opponent_strength must be at defaults — see
    `_validate_full_history_filters`.

    Opponent strength is accepted as a (gap_min, gap_max) pair to mirror the
    range slider. Only the four preset ranges (any/stronger/similar/weaker) are
    permitted here so the LLM cache key (keyed on preset name) stays stable —
    custom ranges return 400.

    Returns:
        200: EndgameInsightsResponse with status in {fresh, cache_hit, stale_rate_limited}.
        400: filters_not_supported (any non-default filter other than opponent_strength,
             or custom (non-preset) opponent gap range).
        429: InsightsErrorResponse(error='rate_limit_exceeded', retry_after_seconds=N).
        502: InsightsErrorResponse(error='provider_error' | 'validation_failure').
    """
    preset = derive_preset(opponent_gap_min, opponent_gap_max)
    if preset == "custom":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "filters_not_supported",
                "message": (
                    "Insights only support the preset opponent strength buckets "
                    "(Any / Stronger / Similar / Weaker). Snap the slider to a "
                    "preset to generate a report."
                ),
                "blocking": ["Snap opponent strength to a preset"],
            },
        )
    filter_context = FilterContext(
        recency=recency,
        opponent_strength=preset,
        color=color,
        time_controls=time_control or [],
        platforms=platform or [],
        rated_only=bool(rated) if rated is not None else False,
    )
    _validate_full_history_filters(filter_context)
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


@router.post("/openings", response_model=OpeningInsightsResponse)
async def get_opening_insights(
    request: OpeningInsightsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OpeningInsightsResponse:
    """Phase 70 (v1.13) opening insights — POST /api/insights/openings.

    Authenticated, user-scoped. Returns a four-section
    OpeningInsightsResponse under the active filter set.

    Per CONTEXT.md D-14, this route does NOT inherit
    _validate_full_history_filters — every filter reshapes findings.
    """
    return await compute_insights(
        session=session,
        user_id=user.id,
        request=request,
    )
