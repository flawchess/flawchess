"""Openings router: POST /openings/positions, /openings/time-series, /openings/next-moves;
GET /openings/out-of-opening-stats.

HTTP layer only — all business logic lives in openings_service / repositories.
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dev_clock import dev_now_utc
from app.models.user import User
from app.schemas.opening_out import OutOfOpeningStatsResponse
from app.schemas.openings import (
    OpeningsRequest,
    OpeningsResponse,
    NextMovesRequest,
    NextMovesResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
)
from app.services import opening_out_stats_service, openings_service
from app.users import current_active_user

router = APIRouter(prefix="/openings", tags=["openings"])

#: The current UTC instant, dev-clock-shiftable. Real clock outside development.
NowUtc = Annotated[datetime.datetime, Depends(dev_now_utc)]


@router.post("/positions", response_model=OpeningsResponse)
async def query_positions(
    request: OpeningsRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OpeningsResponse:
    """Return W/D/L stats and paginated game list for a target board position.

    The target position is identified by its Zobrist hash. match_side controls
    which hash column is queried (white pieces, black pieces, or full position).
    """
    return await openings_service.analyze(session, user.id, request)


@router.post("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    request: TimeSeriesRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
) -> TimeSeriesResponse:
    """Return the weekly rolling-score time series for a list of bookmark positions."""
    return await openings_service.get_time_series(session, user.id, request, now_utc=now_utc)


@router.post("/next-moves", response_model=NextMovesResponse)
async def get_next_moves(
    request: NextMovesRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> NextMovesResponse:
    """Return next moves with W/D/L stats for a target board position.

    Each move entry includes game count, win/draw/loss counts and percentages,
    the resulting position's hash and FEN, and a transposition count.
    """
    return await openings_service.get_next_moves(session, user.id, request)


@router.get("/out-of-opening-stats", response_model=OutOfOpeningStatsResponse)
async def get_out_of_opening_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> OutOfOpeningStatsResponse:
    """Return both colours' peer-ranked "out of the opening" worse/better stats.

    Takes NO filter parameters: the section always describes the canonical ranked
    sample (rated, opponents within 100 Elo, last 36 months, at most 1000 games per time
    control), so any query string produces the same body. ``user_id`` comes only from the
    authenticated user, never from the request.

    Dev-clock exception: the window uses SQL ``NOW()`` rather than the ``dev_now_utc``
    dependency (CLAUDE.md), like ``/endgames/ranked-stats``. The on-read counts must match
    the persisted Stage B basis byte for byte, and those SQL builders anchor the 36-month
    bound to ``NOW()``.

    All internal queries run sequentially on one AsyncSession.
    """
    return await opening_out_stats_service.get_out_of_opening_stats(session, user_id=user.id)
