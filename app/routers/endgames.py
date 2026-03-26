"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints:
- GET /api/endgames/stats: W/D/L per endgame category with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import EndgameClass, EndgameGamesResponse, EndgameStatsResponse
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
