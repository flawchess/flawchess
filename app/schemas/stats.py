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


class MostPlayedOpeningsResponse(BaseModel):
    """Top openings by game count, separated by color."""

    white: list[OpeningWDL]
    black: list[OpeningWDL]
    # Engine-asymmetry baselines (in pawns) used by the frontend bullet chart
    # to center the visual on the same H0 the per-row z-test uses. Sourced from
    # _baseline_cp_for_color('white'|'black') / 100.0; per-game mean from the
    # 2026-05-04 Lichess benchmark (reports/benchmarks-2026-05-04.md).
    eval_baseline_pawns_white: float
    eval_baseline_pawns_black: float


class BookmarkPhaseEntryItem(BaseModel):
    """Phase 80 fields for a single bookmark target_hash (parallel to OpeningWDL's
    Phase 80 subset). Returned by ``POST /stats/bookmark-phase-entry-metrics``.

    Mirrors the OpeningWDL Phase 80 additions exactly so the frontend can spread
    them onto a synthetic OpeningWDL row for bookmarks.
    """

    target_hash: str  # echoed back; key for the frontend lookup map

    # MG-entry pillar
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None
    eval_confidence: Literal["low", "medium", "high"] = "low"


class BookmarkPhaseEntryQuery(BaseModel):
    """Single bookmark coordinate for the phase-entry batch lookup."""

    target_hash: str  # 64-bit signed integer as a string (mirrors OpeningWDL.full_hash)
    match_side: Literal["white", "black", "full"]
    color: Literal["white", "black"] | None = None


class BookmarkPhaseEntryRequest(BaseModel):
    """Request body for ``POST /stats/bookmark-phase-entry-metrics``.

    bookmarks groups by (match_side, color) at the service layer; each group is
    a single batched DB call.
    """

    bookmarks: list[BookmarkPhaseEntryQuery]
    time_control: list[str] | None = None
    platform: list[str] | None = None
    rated: bool | None = None
    opponent_type: str = "human"
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None
    recency: str | None = None  # "30d" / "90d" / "1y" / "all" / None — handled like other endpoints


class BookmarkPhaseEntryResponse(BaseModel):
    """Phase 80 fields keyed by target_hash (string form)."""

    items: list[BookmarkPhaseEntryItem]
