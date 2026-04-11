"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints (all mounted under /api/endgames):
- GET /overview: all four endgame dashboard payloads in a single request
- GET /games: paginated game list filtered by endgame class
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import (
    EndgameClass,
    EndgameGamesResponse,
    EndgameOverviewResponse,
)
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD
from app.services import endgame_service
from app.users import current_active_user

router = APIRouter(prefix="/endgames", tags=["endgames"])


@router.get("/overview", response_model=EndgameOverviewResponse)
async def get_endgame_overview(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # NO color parameter — per D-02 (no color filter on endgame endpoints)
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    recency: str | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    window: int = Query(default=50, ge=5, le=200),
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = Query(default="any"),
    elo_threshold: int = Query(default=DEFAULT_ELO_THRESHOLD),
) -> EndgameOverviewResponse:
    """Return all four endgame dashboard payloads in a single response.

    Combines stats, performance, timeline, and conv-recov-timeline into one
    HTTP request. All internal queries execute sequentially on one AsyncSession
    (no asyncio.gather), reducing the Endgames tab from 4 parallel requests
    down to 1 (Phase 52).

    No color filter is applied — per D-02 endgame stats cover both colors.
    """
    return await endgame_service.get_endgame_overview(
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
    elo_threshold: int = Query(default=DEFAULT_ELO_THRESHOLD),
) -> EndgameGamesResponse:
    """Return paginated games filtered by endgame class (D-12, D-14).

    endgame_class must be one of: rook, minor_piece, pawn, queen, mixed, pawnless.
    Returns empty results (not an error) for unknown classes or users with no matching games.

    Games are reused with the GameRecord schema consistent with the openings endpoints.
    Kept as a standalone endpoint because endgame_class changes independently of the
    overview filters (user picks a class from a selector, not a sidebar filter).
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
