"""Pydantic v2 schemas for stats endpoints."""

import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class RatingDataPoint(BaseModel):
    """Last rating of the day for one time control, plus that day's game count."""

    date: str
    rating: int
    time_control_bucket: str
    game_count: int


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
    display_name: str  # canonical name with "vs. " prefix when off-color
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
    # Score verdict inputs (D-18): (W + 0.5*D) / n, two-sided Wilson p vs 50%, and the
    # 95% Wilson CI (D-33). Computed server-side by score_confidence.score_verdict_fields.
    score: float
    score_confidence: Literal["low", "medium", "high"]
    score_p_value: float
    score_ci_low: float
    score_ci_high: float

    # Middlegame-entry Stockfish eval
    # All optional with defaults so existing callers/tests keep working.
    # Trim |eval_cp| >= 2000 happens upstream in SQL.
    avg_eval_pawns: float | None = None  # signed, user-perspective; None when eval_n == 0
    eval_ci_low_pawns: float | None = None  # 95% CI lower bound; None when eval_n < 2
    eval_ci_high_pawns: float | None = None  # 95% CI upper bound; None when eval_n < 2
    eval_n: int = 0  # games used in the mean (mate-excluded, NULL-excluded, outlier-trimmed)
    eval_p_value: float | None = None  # two-sided p-value vs the colour baseline (D-13)
    eval_confidence: Literal["low", "medium", "high"] = "low"
    # MAX(games.played_at) across the games visiting
    # this opening's full_hash. Drives the "Last played: <relative>" line in
    # the OpeningStatsCard score-confidence popover. None when every
    # contributing game has a NULL played_at (rare).
    last_played_at: datetime.datetime | None = None
    # True when last_played_at is on or after the colour's current-repertoire cutoff
    # (or the colour has no cutoff). False = "Played before" group (D-04).
    is_current: bool


class MostPlayedOpeningsResponse(BaseModel):
    """Top openings by game count, separated by color."""

    white: list[OpeningWDL]
    black: list[OpeningWDL]
    # Engine-asymmetry baselines (in pawns): on Openings surfaces they are the eval
    # bar's centre and the H0 of the per-row eval z-test (D-13, applied server-side by
    # opening_eval.finalize_opening_eval); avg_eval_pawns itself stays the raw mean.
    # Per-game mean from the 2026-05-04 Lichess benchmark run (values in
    # opening_insights_constants.EVAL_BASELINE_PAWNS_*).
    eval_baseline_pawns_white: float
    eval_baseline_pawns_black: float
    # Per-colour current-repertoire cutoff (D-01..D-04). None means the user has
    # fewer than 200 games of that colour under the active filters, so every
    # opening of that colour is current.
    current_cutoff_white: datetime.datetime | None = None
    current_cutoff_black: datetime.datetime | None = None


class BookmarkPhaseEntryItem(BaseModel):
    """Middlegame-entry eval fields for a single bookmark target_hash (parallel to
    OpeningWDL's eval subset). Returned by ``POST /stats/bookmark-phase-entry-metrics``.

    Mirrors the OpeningWDL eval fields exactly so the frontend can spread
    them onto a synthetic OpeningWDL row for bookmarks.
    """

    target_hash: str  # echoed back; key for the frontend lookup map

    # MG-entry pillar
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None  # two-sided p-value vs the bookmark colour's baseline
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
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "BookmarkPhaseEntryRequest":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be <= to_date")
        return self


class BookmarkPhaseEntryResponse(BaseModel):
    """Middlegame-entry eval fields keyed by target_hash (string form)."""

    items: list[BookmarkPhaseEntryItem]
