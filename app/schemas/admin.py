"""Pydantic v2 schemas for admin API (user search + impersonation).

Phase 62.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ImpersonateResponse(BaseModel):
    """Response for POST /admin/impersonate/{user_id}."""

    access_token: str
    token_type: Literal["bearer"]
    target_email: str
    target_id: int


class ImpersonationContext(BaseModel):
    """Populated on /users/me/profile when the request carries an impersonation token.

    Mirrors the JWT claims; the frontend uses this to render the pill (D-22).
    """

    admin_id: int
    target_email: str


class UserSearchResult(BaseModel):
    """Row returned by GET /admin/users/search."""

    id: int
    email: str
    chess_com_username: str | None
    lichess_username: str | None
    is_guest: bool
    last_login: datetime | None


class EnqueueTier1Response(BaseModel):
    """Response for POST /admin/eval/enqueue-tier1/{game_id}.

    Phase 117 D-117-05: internal/admin trigger for QUEUE-03 fan-out verification.
    NOT the user-facing endpoint (Phase 118).
    """

    status: Literal["enqueued", "skipped_guest", "already_queued"]
    game_id: int
