"""Openings router: POST /openings/positions, /openings/time-series, /openings/next-moves.

HTTP layer only — all business logic lives in openings_service / repositories.
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dev_clock import dev_now_utc
from app.models.user import User
from app.schemas.openings import (
    OpeningsRequest,
    OpeningsResponse,
    NextMovesRequest,
    NextMovesResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
)
from app.services import openings_service
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
