"""Pydantic v2 schemas for the analysis API."""

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request body for POST /analysis/positions."""

    target_hash: int
    match_side: Literal["white", "black", "full"] = "full"

    # Optional filters
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    rated: bool | None = None
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


class AnalysisResponse(BaseModel):
    """Response from POST /analysis/positions."""

    stats: WDLStats
    games: list[GameRecord]
    matched_count: int
    offset: int
    limit: int
