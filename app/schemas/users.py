"""Pydantic v2 schemas for user profile API."""

from datetime import datetime

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    """Response for GET/PUT /users/me/profile."""

    email: str
    is_superuser: bool
    chess_com_username: str | None
    lichess_username: str | None
    created_at: datetime
    last_login: datetime | None
    chess_com_game_count: int
    lichess_game_count: int


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/me/profile."""

    chess_com_username: str | None = None
    lichess_username: str | None = None


class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""

    count: int
