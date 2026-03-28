"""Stats router: GET /stats/rating-history and GET /stats/global endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.stats import GlobalStatsResponse, MostPlayedOpeningsResponse, RatingHistoryResponse
from app.services import stats_service
from app.users import current_active_user

router = APIRouter(tags=["stats"])


@router.get("/stats/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    recency: str | None = Query(default=None),
    platform: str | None = Query(default=None),
) -> RatingHistoryResponse:
    """Return per-platform per-game rating data points.

    Optionally filtered by recency (week, month, 3months, 6months, year)
    and by platform (chess.com or lichess).
    """
    return await stats_service.get_rating_history(session, user.id, recency, platform)


@router.get("/stats/global", response_model=GlobalStatsResponse)
async def get_global_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    recency: str | None = Query(default=None),
    platform: str | None = Query(default=None),
) -> GlobalStatsResponse:
    """Return global W/D/L breakdowns by time control and by color.

    Optionally filtered by recency (week, month, 3months, 6months, year)
    and by platform (chess.com or lichess).
    """
    return await stats_service.get_global_stats(session, user.id, recency, platform)


@router.get("/stats/most-played-openings", response_model=MostPlayedOpeningsResponse)
async def get_most_played_openings(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> MostPlayedOpeningsResponse:
    """Return top 5 most played openings per color with WDL stats."""
    return await stats_service.get_most_played_openings(session, user.id)
