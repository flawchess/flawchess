"""Pydantic v2 schemas for user profile API."""

from datetime import datetime

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    """Response for GET/PUT /users/me/profile."""

    chess_com_username: str | None
    lichess_username: str | None
    created_at: datetime
    last_login: datetime | None


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/me/profile."""

    chess_com_username: str | None = None
    lichess_username: str | None = None
