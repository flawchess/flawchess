"""Pydantic v2 schemas for the openings API."""

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD


class OpeningsRequest(BaseModel):
    """Request body for POST /openings/positions."""

    target_hash: int | None = None

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        """Accept string target_hash from the JavaScript frontend.

        JavaScript BigInt cannot be safely represented as a JSON number
        (IEEE-754 double loses precision for values > 2^53).  The frontend
        sends the hash as a decimal string; this validator converts it to int
        before the field is processed.  Plain int values pass through unchanged
        for backward compatibility with existing Python callers.
        None is allowed and means "return all user games" (no position filter).
        """
        if v is None:
            return None
        if isinstance(v, str):
            return int(v)
        return v
    match_side: Literal["white", "black", "full"] = "full"

    # Optional filters
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "3years", "5years", "all"] | None = None
    color: Literal["white", "black"] | None = None

    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD

    # Pagination
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=200)] = 50


class WDLStats(BaseModel):
    """Win/draw/loss aggregate statistics."""

    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float


class GameRecord(BaseModel):
    """A single game that matched the queried position."""

    game_id: int
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    white_rating: int | None
    black_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    user_color: str
    move_count: int | None
    termination: str | None = None
    time_control_str: str | None = None
    result_fen: str | None = None


class OpeningsResponse(BaseModel):
    """Response from POST /openings/positions."""

    stats: WDLStats
    games: list[GameRecord]
    matched_count: int
    offset: int
    limit: int


class TimeSeriesBookmarkParam(BaseModel):
    """Parameters for one bookmark in a time-series request."""

    bookmark_id: int
    target_hash: int
    match_side: Literal["white", "black", "full"] = "full"
    color: Literal["white", "black"] | None = None

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        """Accept string target_hash from the JavaScript frontend (BigInt precision)."""
        if isinstance(v, str):
            return int(v)
        return v


class TimeSeriesRequest(BaseModel):
    """Request body for POST /openings/time-series."""

    bookmarks: list[TimeSeriesBookmarkParam]

    # Optional global filters applied to all bookmarks
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "3years", "5years", "all"] | None = None
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD


class TimeSeriesPoint(BaseModel):
    """Win-rate data for a single rolling-window datapoint."""

    date: str           # "2025-01-15" (ISO date of the game)
    win_rate: float     # wins / total in trailing window
    game_count: int     # total games in the window (1..window_size)
    window_size: int    # the configured window size (always ROLLING_WINDOW_SIZE)


class BookmarkTimeSeries(BaseModel):
    """Rolling-window time-series data for one bookmark."""

    bookmark_id: int
    data: list[TimeSeriesPoint]
    total_wins: int
    total_draws: int
    total_losses: int
    total_games: int


class TimeSeriesResponse(BaseModel):
    """Response from POST /openings/time-series."""

    series: list[BookmarkTimeSeries]


class NextMovesRequest(BaseModel):
    """Request body for POST /openings/next-moves."""

    target_hash: int  # required — no None allowed (unlike OpeningsRequest)

    @field_validator("target_hash", mode="before")
    @classmethod
    def coerce_target_hash(cls, v: object) -> object:
        """Accept string target_hash from the JavaScript frontend.

        JavaScript BigInt cannot be safely represented as a JSON number
        (IEEE-754 double loses precision for values > 2^53).  The frontend
        sends the hash as a decimal string; this validator converts it to int
        before the field is processed.  Plain int values pass through unchanged
        for backward compatibility with existing Python callers.
        """
        if isinstance(v, str):
            return int(v)
        return v

    # Optional filters — same as OpeningsRequest but no match_side, offset, or limit
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "3years", "5years", "all"] | None = None
    color: Literal["white", "black"] | None = None
    sort_by: Literal["frequency", "win_rate"] = "frequency"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD


class NextMoveEntry(BaseModel):
    """Statistics for a single next move from a queried position."""

    move_san: str
    game_count: int
    wins: int
    draws: int
    losses: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    result_hash: str   # BigInt as string for JS safety (full_hash of resulting position)
    result_fen: str    # board FEN of resulting position (piece placement only)
    transposition_count: int


class NextMovesResponse(BaseModel):
    """Response from POST /openings/next-moves."""

    position_stats: WDLStats
    moves: list[NextMoveEntry]
