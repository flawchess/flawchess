"""Pydantic v2 schemas for the analysis API."""

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    """Request body for POST /analysis/positions."""

    target_hash: int

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
    match_side: Literal["white", "black", "full"] = "full"

    # Optional filters
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None
    color: Literal["white", "black"] | None = None

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
    opponent_username: str | None
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    user_rating: int | None
    opponent_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    user_color: str
    move_count: int | None


class AnalysisResponse(BaseModel):
    """Response from POST /analysis/positions."""

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
    """Request body for POST /analysis/time-series."""

    bookmarks: list[TimeSeriesBookmarkParam]

    # Optional global filters applied to all bookmarks
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    recency: Literal["week", "month", "3months", "6months", "year", "all"] | None = None


class TimeSeriesPoint(BaseModel):
    """Win-rate data for a single calendar month."""

    month: str       # "2025-01"
    win_rate: float  # wins / (wins + draws + losses); 0.0 if only draws/losses
    game_count: int
    wins: int
    draws: int
    losses: int


class BookmarkTimeSeries(BaseModel):
    """Monthly time-series data for one bookmark."""

    bookmark_id: int
    data: list[TimeSeriesPoint]


class TimeSeriesResponse(BaseModel):
    """Response from POST /analysis/time-series."""

    series: list[BookmarkTimeSeries]
