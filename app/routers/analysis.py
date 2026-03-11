"""Analysis router: POST /analysis/positions endpoint.

HTTP layer only — all business logic lives in analysis_service.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/positions", response_model=AnalysisResponse)
async def query_positions(
    request: AnalysisRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AnalysisResponse:
    """Return W/D/L stats and paginated game list for a target board position.

    The target position is identified by its Zobrist hash. match_side controls
    which hash column is queried (white pieces, black pieces, or full position).

    TODO(phase-4): Replace hardcoded user_id=1 with real authenticated user_id
    from FastAPI-Users.
    """
    # TODO(phase-4): Replace with real authenticated user_id from FastAPI-Users.
    user_id = 1

    return await analysis_service.analyze(session, user_id, request)
