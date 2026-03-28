"""Pydantic v2 schemas for stats endpoints."""

from pydantic import BaseModel


class RatingDataPoint(BaseModel):
    """A single rating data point for one game."""

    date: str
    rating: int
    time_control_bucket: str


class RatingHistoryResponse(BaseModel):
    """Rating history grouped by platform."""

    chess_com: list[RatingDataPoint]
    lichess: list[RatingDataPoint]


class WDLByCategory(BaseModel):
    """Win/draw/loss counts and percentages for a category label."""

    label: str
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float


class GlobalStatsResponse(BaseModel):
    """Global game statistics broken down by time control and color."""

    by_time_control: list[WDLByCategory]
    by_color: list[WDLByCategory]


class OpeningWDL(BaseModel):
    """WDL stats for a single opening, with ECO code and display label."""

    opening_eco: str
    opening_name: str
    label: str          # "Opening Name (ECO)" — precomputed for UI
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float


class MostPlayedOpeningsResponse(BaseModel):
    """Top openings by game count, separated by color."""

    white: list[OpeningWDL]
    black: list[OpeningWDL]
