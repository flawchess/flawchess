"""Endgames router: HTTP endpoints for endgame analytics.

Endpoints (all mounted under /api/endgames):
- GET /ranked-stats: filter-free per-TC ranked-sample payload for the percentile-first
  Stats tab
- GET /stats: filtered per-category endgame stats for the Games tab
- GET /games: paginated game list filtered by endgame class
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.endgames import (
    EndgameClass,
    EndgameGamesResponse,
    EndgameRankedStatsResponse,
    EndgameStatsResponse,
)
from app.services import endgame_ranked_service, endgame_service
from app.users import current_active_user

router = APIRouter(prefix="/endgames", tags=["endgames"])


@router.get("/ranked-stats", response_model=EndgameRankedStatsResponse)
async def get_endgame_ranked_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> EndgameRankedStatsResponse:
    """Return the per-time-control ranked-sample Endgame Stats.

    Takes NO filter parameters: the Stats tab always describes the canonical
    ranked sample (rated, human opponents, within 100 Elo, last 36 months, at most
    3000 games per time control), so any query string produces the same body.
    ``user_id`` comes only from the authenticated user, never from the request.

    Dev-clock exception: the ranked window uses SQL ``NOW()`` rather than the
    ``dev_now_utc`` dependency (CLAUDE.md). The window must match the persisted
    Stage A/B percentile basis byte for byte, and those SQL builders anchor
    the 36-month bound to ``NOW()``. The 36-month edge therefore cannot be dev-clock
    tested; this is a deliberate trade-off.

    Time controls with no ranked game are omitted; an empty ranked sample returns
    ``{"tcs": []}``. All internal queries run sequentially on one AsyncSession.
    """
    return await endgame_ranked_service.get_ranked_stats(session, user_id=user.id)


@router.get("/stats", response_model=EndgameStatsResponse)
async def get_endgame_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # NO color parameter (no color filter on endgame endpoints)
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> EndgameStatsResponse:
    """Return the filtered per-category endgame stats the Games tab needs.

    Unlike /ranked-stats this honours every sidebar filter, so the Games tab keeps
    working with filters after the Stats tab moves to the ranked sample.
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await endgame_service.get_endgame_stats(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )


@router.get("/games", response_model=EndgameGamesResponse)
async def get_endgame_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    endgame_class: EndgameClass = Query(...),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
) -> EndgameGamesResponse:
    """Return paginated games filtered by endgame class.

    endgame_class must be one of: rook, minor_piece, pawn, queen, mixed, pawnless.
    Returns empty results (not an error) for unknown classes or users with no matching games.

    Games are reused with the GameRecord schema consistent with the openings endpoints.
    Kept as a standalone endpoint because endgame_class changes independently of the
    sidebar filters (user picks a class from a selector, not a sidebar filter).
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await endgame_service.get_endgame_games(
        session,
        user_id=user.id,
        endgame_class=endgame_class,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
