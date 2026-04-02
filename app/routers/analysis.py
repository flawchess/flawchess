"""Analysis router: POST /analysis/positions, /analysis/time-series, /analysis/next-moves.

HTTP layer only — all business logic lives in analysis_service / repositories.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    NextMovesRequest,
    NextMovesResponse,
    TimeSeriesRequest,
    TimeSeriesResponse,
)
from app.services import analysis_service
from app.users import current_active_user

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/positions", response_model=AnalysisResponse)
async def query_positions(
    request: AnalysisRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> AnalysisResponse:
    """Return W/D/L stats and paginated game list for a target board position.

    The target position is identified by its Zobrist hash. match_side controls
    which hash column is queried (white pieces, black pieces, or full position).
    """
    return await analysis_service.analyze(session, user.id, request)


@router.post("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    request: TimeSeriesRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> TimeSeriesResponse:
    """Return monthly win-rate time series for a list of bookmark positions."""
    return await analysis_service.get_time_series(session, user.id, request)


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
    return await analysis_service.get_next_moves(session, user.id, request)
