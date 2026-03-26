"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints:
- GET /api/endgames/stats: W/D/L per endgame category with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
- GET /api/endgames/performance: WDL comparison + gauge values for endgame vs non-endgame
- GET /api/endgames/timeline: rolling-window win-rate time series
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import (
    EndgameClass,
    EndgameGamesResponse,
    EndgamePerformanceResponse,
    EndgameStatsResponse,
    EndgameTimelineResponse,
)
from app.services import endgame_service
from app.users import current_active_user

router = APIRouter(tags=["endgames"])


@router.get("/endgames/stats", response_model=EndgameStatsResponse)
async def get_endgame_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # NO color parameter — per D-02 (no color filter on endgame endpoints)
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
) -> EndgameStatsResponse:
    """Return W/D/L per endgame category with inline conversion/recovery stats.

    Categories are sorted by total game count descending (D-05).
    Returns an empty categories list for users with no endgame data.

    No color filter is applied — stats cover both white and black games (D-02).
    """
    return await endgame_service.get_endgame_stats(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
    )


@router.get("/endgames/games", response_model=EndgameGamesResponse)
async def get_endgame_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    endgame_class: EndgameClass = Query(...),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> EndgameGamesResponse:
    """Return paginated games filtered by endgame class (D-12, D-14).

    endgame_class must be one of: rook, minor_piece, pawn, queen, mixed, pawnless.
    Returns empty results (not an error) for unknown classes or users with no matching games.

    Games are reused with the GameRecord schema consistent with the analysis endpoints.
    """
    return await endgame_service.get_endgame_games(
        session,
        user_id=user.id,
        endgame_class=endgame_class,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
        offset=offset,
        limit=limit,
    )


@router.get("/endgames/performance", response_model=EndgamePerformanceResponse)
async def get_endgame_performance(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
) -> EndgamePerformanceResponse:
    """Return WDL comparison and gauge values for endgame vs non-endgame games.

    Compares win/draw/loss rates for games reaching an endgame (>= ENDGAME_PLY_THRESHOLD plies)
    against games that did not reach any endgame. Also returns aggregate conversion/recovery
    rates and composite gauge values (relative_strength, endgame_skill).

    No color filter is applied per D-02.
    """
    return await endgame_service.get_endgame_performance(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        recency=recency,
        rated=rated,
        opponent_type=opponent_type,
    )


@router.get("/endgames/timeline", response_model=EndgameTimelineResponse)
async def get_endgame_timeline(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    window: int = Query(default=50, ge=5, le=200),
) -> EndgameTimelineResponse:
    """Return rolling-window win-rate time series for endgame performance.

    overall: merged series for endgame games vs non-endgame games, aligned by date.
    per_type: per-endgame-class rolling win-rate series (rook, minor_piece, pawn, etc.).
    window: configurable rolling window size (5–200, default 50).

    Partial windows (fewer games than window size) are included from the start of each series.
    """
    return await endgame_service.get_endgame_timeline(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        recency=recency,
        rated=rated,
        opponent_type=opponent_type,
        window=window,
    )
