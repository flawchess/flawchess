"""Bookmarks router: CRUD + reorder endpoints for position bookmarks.

HTTP layer only — all DB operations go through bookmark_repository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.user import User
from app.repositories import bookmark_repository
from app.schemas.bookmarks import (
    BookmarkCreate,
    BookmarkReorderRequest,
    BookmarkResponse,
    BookmarkUpdate,
)
from app.users import current_active_user

router = APIRouter(tags=["bookmarks"])


@router.get("/bookmarks", response_model=list[BookmarkResponse])
async def list_bookmarks(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> list[BookmarkResponse]:
    """Return all bookmarks for the current user, ordered by sort_order."""
    bookmarks = await bookmark_repository.get_bookmarks(session, user.id)
    return [BookmarkResponse.model_validate(b) for b in bookmarks]


@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
async def create_bookmark(
    data: BookmarkCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> BookmarkResponse:
    """Create a new bookmark for the current user."""
    bookmark = await bookmark_repository.create_bookmark(session, user.id, data)
    return BookmarkResponse.model_validate(bookmark)


# NOTE: /bookmarks/reorder MUST be defined BEFORE /bookmarks/{id} so FastAPI
# does not interpret "reorder" as an integer bookmark ID.
@router.put("/bookmarks/reorder", response_model=list[BookmarkResponse])
async def reorder_bookmarks(
    data: BookmarkReorderRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> list[BookmarkResponse]:
    """Reorder bookmarks by assigning sort_order 0..N-1 in the provided order."""
    bookmarks = await bookmark_repository.reorder_bookmarks(session, user.id, data.ids)
    return [BookmarkResponse.model_validate(b) for b in bookmarks]


@router.put("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    data: BookmarkUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> BookmarkResponse:
    """Update label and/or sort_order for a bookmark owned by the current user."""
    bookmark = await bookmark_repository.update_bookmark(
        session, user.id, bookmark_id, data
    )
    if bookmark is None:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return BookmarkResponse.model_validate(bookmark)


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    """Delete a bookmark owned by the current user."""
    deleted = await bookmark_repository.delete_bookmark(session, user.id, bookmark_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return Response(status_code=204)
