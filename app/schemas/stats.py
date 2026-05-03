"""Pydantic v2 schemas for stats endpoints."""

from typing import Literal

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
    """WDL stats for a single opening, with ECO code, PGN, FEN, and display label."""

    opening_eco: str
    opening_name: str  # canonical name, used for FEN/bookmark lookups
    display_name: str  # canonical name with "vs. " prefix when off-color (PRE-01)
    label: str  # "Opening Name (ECO)" — precomputed for UI
    pgn: str  # PGN move sequence for display
    fen: str  # Full FEN (with side-to-move/castling) for miniboard and bookmark creation
    full_hash: str  # String form of 64-bit Zobrist full hash, for synthetic bookmark construction
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float

    # Phase 80 additions — middlegame-entry Stockfish eval (D-01, D-04, D-08)
    # All optional with defaults so existing callers/tests keep working.
    # Trim |eval_cp| >= 2000 happens upstream in SQL (Plan 02) per D-08.
    avg_eval_pawns: float | None = None  # signed, user-perspective; None when eval_n == 0
    eval_ci_low_pawns: float | None = None  # 95% CI lower bound; None when eval_n < 2
    eval_ci_high_pawns: float | None = None  # 95% CI upper bound; None when eval_n < 2
    eval_n: int = 0  # games used in the mean (mate-excluded, NULL-excluded, outlier-trimmed)
    eval_p_value: float | None = None  # two-sided p-value vs zero
    eval_confidence: Literal["low", "medium", "high"] = "low"

    # Phase 80 additions — clock-diff at middlegame entry (D-05)
    # No endgame-entry parallel (Endgame page already shows EG clock metrics).
    avg_clock_diff_pct: float | None = None  # signed % of base time; None when clock_diff_n == 0
    avg_clock_diff_seconds: float | None = None  # signed seconds; None when clock_diff_n == 0
    clock_diff_n: int = 0  # games with both user and opp clock present at MG entry

    # Phase 80 additions — endgame-entry Stockfish eval (D-09 — parallel pillar)
    # Same trim policy (D-08) and helper as MG-entry; different SQL filter (phase = 2).
    # 99.99% coverage per bench §3 line 353; no analyzed-games caveat (handled in D-10 tooltip).
    avg_eval_endgame_entry_pawns: float | None = (
        None  # signed, user-perspective; None when eval_endgame_n == 0
    )
    eval_endgame_ci_low_pawns: float | None = (
        None  # 95% CI lower bound; None when eval_endgame_n < 2
    )
    eval_endgame_ci_high_pawns: float | None = (
        None  # 95% CI upper bound; None when eval_endgame_n < 2
    )
    eval_endgame_n: int = (
        0  # games used in the EG mean (mate-excluded, NULL-excluded, outlier-trimmed)
    )
    eval_endgame_p_value: float | None = None  # two-sided p-value vs zero (EG-entry sample)
    eval_endgame_confidence: Literal["low", "medium", "high"] = "low"


class MostPlayedOpeningsResponse(BaseModel):
    """Top openings by game count, separated by color."""

    white: list[OpeningWDL]
    black: list[OpeningWDL]
