"""Pydantic v2 schemas for the bot-game store endpoint (Phase 167, STORE-01..07).

Boundary schemas only — the server derives result/termination/clocks/rating from
the PGN and user_rating_anchors; the client never supplies those (D-05/D-08/D-14).
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.normalization import Color

# quick-260714-qaj (F-5): relocated from store_bot_game_service.py to break a
# circular import (app.services.bot_game_pgn needs it too). This is the closed
# vocabulary the BotGameSettings.rating_source column CHECKs.
RatingSource = Literal["lichess", "chesscom", "blended"]

# Named constants (no magic numbers per CLAUDE.md)
MAX_BOT_PGN_LENGTH = 100_000  # bounds the DoS surface of a client-POSTed PGN (RESEARCH Security)
_MIN_BOT_ELO = 600  # BOTX-01: 200-ELO-step bot cards span 600-2600
_MAX_BOT_ELO = 2600
_MIN_PLAY_STYLE_BLEND = 0.0  # b in [0, 1] blend from Phase 166 D-01
_MAX_PLAY_STYLE_BLEND = 1.0
# CR-01: must never overflow games.time_control_str String(50) (app/models/game.py).
# tc_preset flows unmodified through normalize_flawchess_game -> NormalizedGame.time_control_str
# -> _flush_batch's INSERT; an unbounded value raises an unhandled 500 (Postgres DataError),
# not the intended 422.
_MAX_TC_PRESET_LENGTH = 50


class StoreBotGameRequest(BaseModel):
    """Request body for POST /bots/games.

    No rating/platform/user_id/username/is_computer_game field — the server
    derives all of those authoritatively (D-05/D-08/D-14, T-167-01).
    """

    game_uuid: str  # client-minted UUID (D-14); validated below
    pgn: str = Field(max_length=MAX_BOT_PGN_LENGTH)
    user_color: Color
    bot_elo: int = Field(ge=_MIN_BOT_ELO, le=_MAX_BOT_ELO)
    play_style_blend: float = Field(ge=_MIN_PLAY_STYLE_BLEND, le=_MAX_PLAY_STYLE_BLEND)
    tc_preset: str = Field(max_length=_MAX_TC_PRESET_LENGTH)

    @field_validator("game_uuid")
    @classmethod
    def validate_game_uuid(cls, value: str) -> str:
        """Reject a malformed game_uuid with a 422 (T-167-02).

        Expected: a Pydantic ValidationError, not an unexpected exception — do
        NOT capture_exception on this per RESEARCH/PATTERNS guidance.

        WR-01: canonicalize to str(uuid.UUID(value)) rather than returning the
        original string. uuid.UUID() accepts several textual variants of the
        same UUID (no hyphens, urn:uuid: prefix, braces, mixed case); without
        canonicalization, two differently-formatted representations of the same
        UUID become distinct platform_game_id values, silently breaking the
        D-11 "re-submitting the same game_uuid is a no-op" idempotency guarantee.
        """
        try:
            return str(uuid.UUID(value))
        except ValueError as exc:
            raise ValueError("game_uuid must be a valid UUID") from exc


class StoreBotGameResponse(BaseModel):
    """Response body for POST /bots/games."""

    game_id: int
    created: bool
