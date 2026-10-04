"""Pydantic v2 schemas for user profile API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.core.platform_usernames import extract_platform_username
from app.repositories.query_utils import AnalyticsPlatform
from app.schemas.admin import ImpersonationContext
from app.schemas.normalization import TimeControlBucket


class CurrentStrengthRung(BaseModel):
    """Provenance of a recent-games-derived current-strength estimate.

    Quick 260811-u11 (SEED-147). ``converted`` is False only for a native
    Lichess blitz rung; every other rung was mapped onto the Lichess blitz
    scale by ``normalize_to_lichess_blitz`` before comparison, so it always
    carries some conversion error.
    """

    platform: AnalyticsPlatform
    time_control_bucket: TimeControlBucket
    n_games: int
    window_days: int
    converted: bool


class CurrentStrengthResponse(BaseModel):
    """The opponent-matching current-strength estimate (Quick 260811-u11, SEED-147).

    Separate from the ``user_rating_anchors`` career-median anchor the
    percentile chip reads -- this value answers "who should I play right
    now", not "how do I compare over the long run". ``rung`` is non-None
    exactly when ``source == "recent_games"``; when no rung passes the
    90-day/20-game activity floor, ``source`` is "rating_anchor" and ``rung``
    is None.

    UI DEFAULT ONLY -- never fed into bot move selection (BOT-03). This
    value seeds the Bots page's PersonaGrid rating line, the custom-bot ELO
    default, and the analysis board's free-play ELO default; it must never
    reach the bot's move-selection budget.
    """

    rating: int
    source: Literal["recent_games", "rating_anchor"]
    rung: CurrentStrengthRung | None


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
    # Phase 230 D-16: weekly Train leaderboard opt-out. Written only via the
    # profile PUT (UserProfileUpdate.leaderboard_hidden).
    leaderboard_hidden: bool
    # Quick 260811-u11 (SEED-147): the opponent-matching current-strength
    # estimate, replacing `lichess_blitz_equivalent_rating` (P-01) -- that
    # field had zero readers left once all three opponent-matching surfaces
    # repointed here, and the anchor fallback (D-07) now happens server-side
    # inside this field's resolution instead of at each call site. None for
    # guests, for users with no anchor at all, and for users with anchors
    # only in non-blitz buckets and no qualifying recent games (deliberate,
    # not a bug); the frontend falls back to 1500. UI DEFAULT ONLY -- never
    # fed into bot move selection (BOT-03).
    current_strength: CurrentStrengthResponse | None = None


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/me/profile."""

    chess_com_username: str | None = None
    lichess_username: str | None = None
    # Phase 230 D-16: None means unchanged (the repository drops None values),
    # an explicit False un-hides. beta_enabled stays absent from this schema.
    leaderboard_hidden: bool | None = None

    # D-03: per-field validators pinned to that field's own platform, so a
    # chess.com URL pasted into lichess_username (or vice versa) is not
    # silently rewritten -- it is left unchanged and rejected downstream by
    # the platform API instead.
    @field_validator("chess_com_username", mode="before")
    @classmethod
    def _extract_chess_com_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return extract_platform_username(value, "chess.com")

    @field_validator("lichess_username", mode="before")
    @classmethod
    def _extract_lichess_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return extract_platform_username(value, "lichess")


# Length caps for the values stored in the users.first_touch JSONB object.
FIRST_TOUCH_HOST_MAX_LEN = 255
FIRST_TOUCH_UTM_MAX_LEN = 100
FIRST_TOUCH_PATH_MAX_LEN = 255


def _clip(value: object, max_len: int) -> str | None:
    """Strip, blank-to-None and truncate a client-supplied attribution string.

    Truncates instead of rejecting: the values come from arbitrary inbound URLs
    (utm_campaign can be anything), and a 422 would lose the whole record.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped[:max_len] or None


class FirstTouchRequest(BaseModel):
    """Request body for POST /users/me/first-touch (growth report item 16)."""

    referrer_host: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    landing_path: str | None = None

    @field_validator("referrer_host", mode="before")
    @classmethod
    def _clip_host(cls, value: object) -> str | None:
        clipped = _clip(value, FIRST_TOUCH_HOST_MAX_LEN)
        return clipped.lower() if clipped else None

    @field_validator("utm_source", "utm_medium", "utm_campaign", mode="before")
    @classmethod
    def _clip_utm(cls, value: object) -> str | None:
        return _clip(value, FIRST_TOUCH_UTM_MAX_LEN)

    @field_validator("landing_path", mode="before")
    @classmethod
    def _clip_path(cls, value: object) -> str | None:
        # Pathname only: drop any query or fragment so a token-bearing URL can
        # never be stored (cf. the OAuth #token leak into Umami, 2026-09-26).
        if not isinstance(value, str) or not value.startswith("/"):
            return None
        return _clip(value.split("?", 1)[0].split("#", 1)[0], FIRST_TOUCH_PATH_MAX_LEN)


class GameCountResponse(BaseModel):
    """Response for GET /users/games/count."""

    count: int


class ImportSettingsResponse(BaseModel):
    """Response for GET/PATCH /users/me/import-settings.

    Phase 186 Plan 01 (IMPORT-01/IMPORT-04). `game_cap` is a `Literal`, never
    a bare `int` (CLAUDE.md V5 rule) -- mirrors the DB
    `ck_user_import_settings_cap` CHECK constraint at the schema boundary.
    """

    tc_bullet: bool
    tc_blitz: bool
    tc_rapid: bool
    tc_classical: bool
    game_cap: Literal[1000, 3000, 5000]
    # Per-(platform, TC) count of ALL imported games (not just the pre-anchor
    # backlog), e.g. {"chess.com": {"blitz": 2705, "rapid": 1643}}. Populated by
    # count_imported_by_platform_and_tc so the per-TC chips read as an honest
    # breakdown of the header's total game count (UAT follow-up to Plan 03).
    # NULL-bucket games are omitted (no TC chip); empty dict is a valid "no
    # games yet" response, not a sentinel for "not computed".
    imported_counts: dict[str, dict[str, int]]


class ImportSettingsUpdate(BaseModel):
    """Request body for PATCH /users/me/import-settings."""

    tc_bullet: bool
    tc_blitz: bool
    tc_rapid: bool
    tc_classical: bool
    game_cap: Literal[1000, 3000, 5000]
