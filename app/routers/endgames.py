"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints (all mounted under /api/endgames):
- GET /stats: W/D/L per endgame category with inline conversion/recovery stats
- GET /games: paginated game list filtered by endgame class
- GET /performance: WDL comparison + gauge values for endgame vs non-endgame
- GET /timeline: rolling-window win-rate time series
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import (
    ConvRecovTimelineResponse,
    EndgameClass,
    EndgameGamesResponse,
    EndgamePerformanceResponse,
    EndgameStatsResponse,
    EndgameTimelineResponse,
)
from app.services import endgame_service
from app.users import current_active_user

router = APIRouter(prefix="/endgames", tags=["endgames"])


@router.get("/stats", response_model=EndgameStatsResponse)
async def get_endgame_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # NO color parameter — per D-02 (no color filter on endgame endpoints)
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )


@router.get("/games", response_model=EndgameGamesResponse)
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
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
) -> EndgameGamesResponse:
    """Return paginated games filtered by endgame class (D-12, D-14).

    endgame_class must be one of: rook, minor_piece, pawn, queen, mixed, pawnless.
    Returns empty results (not an error) for unknown classes or users with no matching games.

    Games are reused with the GameRecord schema consistent with the openings endpoints.
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )


@router.get("/performance", response_model=EndgamePerformanceResponse)
async def get_endgame_performance(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )


@router.get("/timeline", response_model=EndgameTimelineResponse)
async def get_endgame_timeline(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    window: int = Query(default=50, ge=5, le=200),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
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
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )


@router.get("/conv-recov-timeline", response_model=ConvRecovTimelineResponse)
async def get_conv_recov_timeline(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    window: int = Query(default=50, ge=5, le=200),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=100),
) -> ConvRecovTimelineResponse:
    """Return conversion and recovery rolling-window timelines.

    Conversion: win rate over trailing `window` games where user entered endgame
    with significant material advantage (>=3 pawns).
    Recovery: save rate (win+draw) over trailing `window` games where user entered
    endgame with significant material disadvantage (>=3 pawns down).
    """
    return await endgame_service.get_conv_recov_timeline(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        recency=recency,
        window=window,
        opponent_strength=opponent_strength,
        elo_threshold=elo_threshold,
    )
