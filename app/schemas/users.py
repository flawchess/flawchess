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
    chess_com_last_sync_at: datetime | None = None
    lichess_last_sync_at: datetime | None = None
    # D-22: populated when the request's JWT has is_impersonation=true.
    # Frontend uses this to render the header pill (phase 62).
    impersonation: ImpersonationContext | None = None
    # BETA-01: beta_enabled flag (e.g. Endgame Insights). Default false; flipped via direct DB op.
    beta_enabled: bool
    # MAIA-04 / D-07: rating from the user's most-recent game (across platforms),
    # read-only, index-backed. Feeds the free-play ELO-selector default. None
    # when the user has no games or their most recent game is unrated.
    current_rating: int | None = None
    # Phase 171 D-07: the caller's own blitz-bucket `user_rating_anchors.anchor_rating`
    # -- the blended lichess-equivalent median Phase 167 already trusts for bot-game
    # rating derivation. None for guests, for users with no anchor at all, and for
    # users with anchors only in non-blitz buckets (rapid/classical-only players
    # included -- deliberate, not a bug); the frontend falls back to 1500.
    # UI DEFAULT ONLY -- never fed into bot move selection (BOT-03).
    lichess_blitz_equivalent_rating: int | None = None


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/me/profile."""

    chess_com_username: str | None = None
    lichess_username: str | None = None


class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""

    count: int
