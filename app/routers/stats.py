"""Stats router: GET /stats/rating-history and GET /stats/global endpoints."""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.stats import (
    BookmarkPhaseEntryRequest,
    BookmarkPhaseEntryResponse,
    GlobalStatsResponse,
    MostPlayedOpeningsResponse,
    RatingHistoryResponse,
)
from app.services import stats_service
from app.users import current_active_user

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    platform: str | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> RatingHistoryResponse:
    """Return per-platform per-game rating data points.

    Optionally filtered by from_date, to_date, platform, opponent_type, and opponent gap.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await stats_service.get_rating_history(
        session,
        user.id,
        from_date=from_date,
        to_date=to_date,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )


@router.get("/global", response_model=GlobalStatsResponse)
async def get_global_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    platform: str | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: str | None = Query(default=None),
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Optionally filtered by from_date, to_date, platform, opponent_type, opponent gap,
    and color ("white" or "black"). Rating-history endpoint is intentionally excluded.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await stats_service.get_global_stats(
        session,
        user.id,
        from_date=from_date,
        to_date=to_date,
        platform=platform,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )


@router.get("/most-played-openings", response_model=MostPlayedOpeningsResponse)
async def get_most_played_openings(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> MostPlayedOpeningsResponse:
    """Return top 10 most played openings per color with SQL-side WDL stats.

    Optionally filtered by from_date, to_date, time_control, platform, rated, opponent_type.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await stats_service.get_most_played_openings(
        session,
        user.id,
        from_date=from_date,
        to_date=to_date,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )


@router.post("/bookmark-phase-entry-metrics", response_model=BookmarkPhaseEntryResponse)
async def get_bookmark_phase_entry_metrics(
    request: BookmarkPhaseEntryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> BookmarkPhaseEntryResponse:
    """Phase 80 fields (avg eval, confidence, clock-diff at MG/EG entry) for arbitrary
    bookmark target_hashes. Body shape allows variable-length hash lists without URL length limits.
    """
    return await stats_service.get_bookmark_phase_entry_metrics(
        session,
        user.id,
        request.bookmarks,
        from_date=request.from_date,
        to_date=request.to_date,
        time_control=request.time_control,
        platform=request.platform,
        rated=request.rated,
        opponent_type=request.opponent_type,
        opponent_gap_min=request.opponent_gap_min,
        opponent_gap_max=request.opponent_gap_max,
    )
