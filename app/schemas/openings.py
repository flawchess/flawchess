"""Pydantic v2 schemas for the openings API."""

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    color: Literal["white", "black"] | None = None

    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None

    # Pagination
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=200)] = 50

    @model_validator(mode="after")
    def _check_date_range(self) -> "OpeningsRequest":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be <= to_date")
        return self


class WDLStats(BaseModel):
    """Win/draw/loss aggregate statistics."""

    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    # Score and confidence fields — computed via compute_confidence_bucket
    # (same Wilson score-test formula as per-move pipeline).
    score: float
    confidence: Literal["low", "medium", "high"]
    p_value: float
    ci_low: float
    ci_high: float
    # MAX(games.played_at) across the games contributing to these stats. Drives
    # the "Last played: <relative>" line in the WDL confidence tooltip. None
    # when no contributing game has a populated
    # played_at — the FE omits the line entirely in that case.
    last_played_at: datetime.datetime | None = None
    # MG-entry eval fields. Mirror the OpeningWDL
    # shape from app/schemas/stats.py so the Openings → Moves "Results played
    # as" section can render the same WDL + Score + Eval three-pillar layout
    # used by the Stats tab cards. Optional because the position +
    # filter combo may have no MG-entry rows; the frontend renders an em-dash
    # in that case. Defaults match the OpeningWDL "no eval data" state.
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None
    eval_confidence: Literal["low", "medium", "high"] = "low"


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
    ply_count: int | None
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
    # Per-color engine-asymmetry baseline (in pawns). Resolved server-side
    # from the request's color (BLACK when color == "black", WHITE otherwise).
    # Phase 242: this is the eval verdict bar centre AND the z-test H0 (the
    # eval_p_value / eval_confidence above are tested against it); avg_eval_pawns
    # stays the raw mean.
    eval_baseline_pawns: float


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
    """Request body for POST /openings/time-series.

    The time-series endpoint returns one weekly point per active ISO week (keyed by
    that week's Monday) and accepts optional from_date/to_date bounds.
    When present, only TimeSeriesPoints whose
    played_at falls within [from_date, to_date] are emitted, and WDL totals
    count only in-window games. The rolling average is still warmed from games
    before the window start — full chronological history is loaded so trailing
    averages anchor correctly (warm-up preserved). When from_date/to_date are
    omitted, behavior is unchanged: the chart covers the full game history.

    Other game filters (time_control, platform, rated, opponent_type,
    opponent_gap) still apply to narrow which games contribute to the series.
    """

    bookmarks: list[TimeSeriesBookmarkParam]

    # Optional global filters applied to all bookmarks
    time_control: list[Literal["bullet", "blitz", "rapid", "classical"]] | None = None
    platform: list[Literal["chess.com", "lichess"]] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "both"] = "human"
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None
    # Resolved date bounds for windowed emission (no recency preset).
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "TimeSeriesRequest":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be <= to_date")
        return self


class TimeSeriesPoint(BaseModel):
    """Score data for a single rolling-window datapoint."""

    date: str  # "2025-01-12" (ISO Monday of the week; one point per active ISO week)
    score: float  # (wins + 0.5 * draws) / total in trailing window after the week's last game
    game_count: int  # total games in the window (1..window_size)
    window_size: int  # the configured window size (always ROLLING_WINDOW_SIZE)
    # In-window games through this bookmark position that ISO week. Drives the
    # grey weekly volume bars on the expanded-row ScoreChart (D-00).
    per_week_games: int


class BookmarkTimeSeries(BaseModel):
    """Rolling-window time-series data for one bookmark."""

    bookmark_id: int
    data: list[TimeSeriesPoint]
    total_wins: int
    total_draws: int
    total_losses: int
    total_games: int
    # MAX(games.played_at) across in-window games visiting this bookmark's
    # target_hash (date-windowed when from_date/to_date are set).
    # Drives the bookmark card score-confidence popover's "Last played: <relative>" line.
    last_played_at: datetime.datetime | None = None
    # Score verdict inputs over the in-window totals (D-18): score, two-sided Wilson
    # p-value bucket, and the 95% Wilson CI (D-33). Same helper as the most-played rows, so
    # identical games report identical numbers. Empty series: 0.5 / "low" / p 1.0.
    score: float
    score_confidence: Literal["low", "medium", "high"]
    score_p_value: float
    score_ci_low: float
    score_ci_high: float
    # False when this opening was last played before the colour's current-repertoire
    # cutoff under the request filters (D-04): drives the "not played recently" chip.
    # Colour-less bookmarks and series without games read as current.
    is_current: bool


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
    from_date: datetime.date | None = None
    to_date: datetime.date | None = None
    color: Literal["white", "black"] | None = None
    sort_by: Literal["frequency", "win_rate"] = "frequency"
    opponent_gap_min: int | None = None
    opponent_gap_max: int | None = None

    @model_validator(mode="after")
    def _check_date_range(self) -> "NextMovesRequest":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be <= to_date")
        return self


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
    result_hash: str  # BigInt as string for JS safety (full_hash of resulting position)
    result_fen: str  # board FEN of resulting position (piece placement only)
    transposition_count: int
    score: float = Field(ge=0.0, le=1.0)  # (W + 0.5*D)/n; canonical classification metric
    confidence: Literal[
        "low", "medium", "high"
    ]  # Two-sided Wilson score-test p-value bucket with N>=10 gate (p<0.01 high, p<0.05 medium) (shared via score_confidence.py)
    p_value: float = Field(
        ge=0.0, le=1.0
    )  # Two-sided Wilson score-test p-value on H0: score = 0.50 (null SE = 0.5/sqrt(n))
    # MAX(games.played_at) across all games where the user played this candidate
    # move from the queried position. Surfaces the "Last played: <relative>"
    # line in the move-explorer Score popover. None
    # when every contributing game has a NULL played_at (rare).
    last_played_at: datetime.datetime | None = None


class NextMovesResponse(BaseModel):
    """Response from POST /openings/next-moves."""

    position_stats: WDLStats
    moves: list[NextMoveEntry]
