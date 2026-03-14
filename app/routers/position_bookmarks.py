"""Position bookmarks router: CRUD + reorder endpoints for position bookmarks.

HTTP layer only — all DB operations go through position_bookmark_repository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import position_bookmark_repository
from app.schemas.position_bookmarks import (
    PositionBookmarkCreate,
    PositionBookmarkReorderRequest,
    PositionBookmarkResponse,
    PositionBookmarkUpdate,
)
from app.users import current_active_user

router = APIRouter(tags=["position-bookmarks"])


@router.get("/position-bookmarks", response_model=list[PositionBookmarkResponse])
async def list_bookmarks(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> list[PositionBookmarkResponse]:
    """Return all position bookmarks for the current user, ordered by sort_order."""
    bookmarks = await position_bookmark_repository.get_bookmarks(session, user.id)
    return [PositionBookmarkResponse.model_validate(b) for b in bookmarks]


@router.post("/position-bookmarks", response_model=PositionBookmarkResponse, status_code=201)
async def create_bookmark(
    data: PositionBookmarkCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> PositionBookmarkResponse:
    """Create a new position bookmark for the current user."""
    bookmark = await position_bookmark_repository.create_bookmark(session, user.id, data)
    return PositionBookmarkResponse.model_validate(bookmark)


# NOTE: /position-bookmarks/reorder MUST be defined BEFORE /position-bookmarks/{id} so FastAPI
# does not interpret "reorder" as an integer bookmark ID.
@router.put("/position-bookmarks/reorder", response_model=list[PositionBookmarkResponse])
async def reorder_bookmarks(
    data: PositionBookmarkReorderRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> list[PositionBookmarkResponse]:
    """Reorder position bookmarks by assigning sort_order 0..N-1 in the provided order."""
    bookmarks = await position_bookmark_repository.reorder_bookmarks(session, user.id, data.ids)
    return [PositionBookmarkResponse.model_validate(b) for b in bookmarks]


@router.put("/position-bookmarks/{bookmark_id}", response_model=PositionBookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    data: PositionBookmarkUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> PositionBookmarkResponse:
    """Update label and/or sort_order for a position bookmark owned by the current user."""
    bookmark = await position_bookmark_repository.update_bookmark(
        session, user.id, bookmark_id, data
    )
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Position bookmark not found")
    return PositionBookmarkResponse.model_validate(bookmark)


@router.delete("/position-bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    """Delete a position bookmark owned by the current user."""
    deleted = await position_bookmark_repository.delete_bookmark(session, user.id, bookmark_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Position bookmark not found")
    return Response(status_code=204)
