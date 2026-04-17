"""Pydantic v2 schemas for user profile API."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.admin import ImpersonationContext


class UserProfileResponse(BaseModel):
    """Response for GET/PUT /users/me/profile."""

    email: str
    is_superuser: bool
    is_guest: bool
    chess_com_username: str | None
    lichess_username: str | None
    created_at: datetime
    last_login: datetime | None
    chess_com_game_count: int
    lichess_game_count: int
    # D-22: populated when the request's JWT has is_impersonation=true.
    # Frontend uses this to render the header pill (phase 62).
    impersonation: ImpersonationContext | None = None


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/me/profile."""

    chess_com_username: str | None = None
    lichess_username: str | None = None


class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""

    count: int
