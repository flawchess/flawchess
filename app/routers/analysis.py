"""Analysis router: POST /analysis/positions and GET /games/count endpoints.

HTTP layer only — all business logic lives in analysis_service / repositories.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import game_repository
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services import analysis_service
from app.users import current_active_user

router = APIRouter(tags=["analysis"])


@router.post("/analysis/positions", response_model=AnalysisResponse)
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


@router.get("/games/count")
async def get_game_count(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> dict[str, int]:
    """Return the total number of games imported by the current user."""
    count = await game_repository.count_games_for_user(session, user.id)
    return {"count": count}
