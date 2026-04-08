"""Stats router: GET /stats/rating-history and GET /stats/global endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.stats import GlobalStatsResponse, MostPlayedOpeningsResponse, RatingHistoryResponse
from app.services import stats_service
from app.users import current_active_user

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/rating-history", response_model=RatingHistoryResponse)
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


@router.get("/global", response_model=GlobalStatsResponse)
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


@router.get("/most-played-openings", response_model=MostPlayedOpeningsResponse)
async def get_most_played_openings(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    recency: str | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
) -> MostPlayedOpeningsResponse:
    """Return top 10 most played openings per color with SQL-side WDL stats.

    Optionally filtered by recency, time_control, platform, rated, opponent_type.
    """
    return await stats_service.get_most_played_openings(
        session,
        user.id,
        recency=recency,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
