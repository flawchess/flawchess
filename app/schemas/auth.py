"""Pydantic v2 schemas for auth API endpoints."""

from pydantic import BaseModel


class GoogleOAuthAvailableResponse(BaseModel):
    """Response for GET /auth/google/available."""

    available: bool


class GoogleOAuthAuthorizeResponse(BaseModel):
    """Response for GET /auth/google/authorize."""

    authorization_url: str
