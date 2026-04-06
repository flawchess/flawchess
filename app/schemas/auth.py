"""Pydantic v2 schemas for auth API endpoints."""

from pydantic import BaseModel, EmailStr


class GoogleOAuthAvailableResponse(BaseModel):
    """Response for GET /auth/google/available."""

    available: bool


class GoogleOAuthAuthorizeResponse(BaseModel):
    """Response for GET /auth/google/authorize."""

    authorization_url: str


class GuestCreateResponse(BaseModel):
    """Response for POST /auth/guest/create."""

    access_token: str
    token_type: str
    is_guest: bool


class GuestRefreshResponse(BaseModel):
    """Response for POST /auth/guest/refresh."""

    access_token: str
    token_type: str


class GuestPromoteEmailRequest(BaseModel):
    """Request body for POST /auth/guest/promote/email."""

    email: EmailStr
    password: str


class GuestPromoteResponse(BaseModel):
    """Response for POST /auth/guest/promote/email."""

    access_token: str
    token_type: str
