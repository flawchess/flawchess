"""Pydantic v2 schemas for the endgame analytics API.

Provides response models for:
- GET /api/endgames/stats: per-category W/D/L with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
- GET /api/endgames/overview: composed response including clock pressure stats (Phase 54)
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.openings import GameRecord

EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]
EndgameLabel = Literal["Rook", "Minor Piece", "Pawn", "Queen", "Mixed", "Pawnless"]


class ConversionRecoveryStats(BaseModel):
    """Inline conversion/recovery stats for one endgame category (D-06, D-08, D-09).

    Conversion: win rate when user entered this endgame type with material advantage.
    Recovery: draw+win rate when user entered this endgame type with material disadvantage.
    Both are computed per endgame type (D-11), not per game phase.
    """

    conversion_pct: float   # win rate when up material entering endgame (0-100), per D-08
    conversion_games: int   # games where user entered this endgame type with material advantage
    conversion_wins: int    # wins among those games
    conversion_draws: int   # draws among those games
    conversion_losses: int  # losses among those games (= conversion_games - wins - draws)

    recovery_pct: float     # draw+win rate when down material entering endgame (0-100), per D-09
    recovery_games: int     # games where user entered this endgame type with material disadvantage
    recovery_saves: int     # draws+wins among those games (kept for backward compat)
    recovery_wins: int      # wins among those games
    recovery_draws: int     # draws among those games


class EndgameCategoryStats(BaseModel):
    """W/D/L + inline conversion/recovery for one endgame category (D-06, D-10).

    endgame_class maps to one of the six categories defined in D-07:
    rook | minor_piece | pawn | queen | mixed | pawnless
    """

    endgame_class: EndgameClass
    label: EndgameLabel
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    conversion: ConversionRecoveryStats  # Inline, not a separate section (D-10)


class EndgameStatsResponse(BaseModel):
    """Response for GET /api/endgames/stats.

    Categories sorted by total game count descending (D-05).
    No color filter applied — stats cover both colors (D-02).
    """

    categories: list[EndgameCategoryStats]
    total_games: int       # Total games matching current filters (not just endgame games)
    endgame_games: int     # Games that reached an endgame phase


class EndgameGamesResponse(BaseModel):
    """Response for GET /api/endgames/games (D-12, D-14).

    Reuses GameRecord from analysis schema for consistency with existing game displays.
    """

    games: list[GameRecord]
    matched_count: int
    offset: int
    limit: int


# --- Performance chart schemas (Phase 32) ---


class EndgameWDLSummary(BaseModel):
    """W/D/L summary for a set of games (endgame or non-endgame).

    Used in EndgamePerformanceResponse to compare endgame games vs non-endgame games.
    All percentages are 0-100.
    """

    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float


class EndgamePerformanceResponse(BaseModel):
    """Response for GET /api/endgames/performance.

    Provides WDL comparison and gauge values for endgame performance analytics.
    Endgame games = games that spent >= ENDGAME_PLY_THRESHOLD plies in any endgame class.
    Non-endgame games = games that never reached any endgame class above the threshold.
    """

    endgame_wdl: EndgameWDLSummary       # games reaching any endgame class >= ENDGAME_PLY_THRESHOLD
    non_endgame_wdl: EndgameWDLSummary   # games NOT reaching any endgame class
    overall_win_rate: float              # wins / total across ALL games, 0-100
    endgame_win_rate: float              # wins / total for endgame games only, 0-100
    aggregate_conversion_pct: float      # sum of conversion_wins / sum of conversion_games * 100 (D-07)
    aggregate_conversion_wins: int       # total games converted (won from material advantage)
    aggregate_conversion_games: int      # total games entering endgame with material advantage
    aggregate_recovery_pct: float        # sum of recovery_saves / sum of recovery_games * 100 (D-07)
    aggregate_recovery_saves: int        # total games recovered (won or drawn from material deficit)
    aggregate_recovery_games: int        # total games entering endgame with material deficit
    relative_strength: float             # endgame_win_rate / overall_win_rate * 100, can exceed 100 (D-05)
    endgame_skill: float                 # 0.6 * conversion_pct + 0.4 * recovery_pct, 0-100 (D-06)


class EndgameTimelinePoint(BaseModel):
    """Single data point in a per-type rolling-window time series.

    Represents win rate over the trailing `window_size` games (or fewer if early in the series).
    """

    date: str           # ISO date string "YYYY-MM-DD" of the game
    win_rate: float     # fraction (0.0–1.0) wins in the rolling window
    game_count: int     # number of games in the rolling window (may be < window_size early on)
    window_size: int    # configured window size


class EndgameOverallPoint(BaseModel):
    """Single data point in the overall endgame vs non-endgame rolling-window time series.

    Tracks two parallel series (endgame games, non-endgame games) merged by date.
    Either win_rate may be None if that series has no games on this date's window.
    """

    date: str
    endgame_win_rate: float | None          # rolling win rate for endgame games
    non_endgame_win_rate: float | None      # rolling win rate for non-endgame games
    endgame_game_count: int                 # rolling window size for endgame series
    non_endgame_game_count: int             # rolling window size for non-endgame series
    window_size: int                        # configured window size


class EndgameTimelineResponse(BaseModel):
    """Response for GET /api/endgames/timeline.

    overall: merged endgame vs non-endgame series aligned by date.
    per_type: per-endgame-class rolling win-rate series (keys are EndgameClass strings).
    window: configured rolling window size.

    Uses dict[str, ...] not dict[EndgameClass, ...] because Pydantic requires str keys
    for JSON serialization of dict models.
    """

    overall: list[EndgameOverallPoint]
    per_type: dict[str, list[EndgameTimelinePoint]]
    window: int


class ConvRecovTimelinePoint(BaseModel):
    """Single data point in a conversion or recovery rolling timeline."""

    date: str
    rate: float  # 0.0-1.0 fraction
    game_count: int  # games in rolling window at this point
    window_size: int


class ConvRecovTimelineResponse(BaseModel):
    """Response for GET /api/endgames/conv-recov-timeline.

    Two rolling-window series showing how conversion rate (winning when up material)
    and recovery rate (saving when down material) trend over game history.
    """

    conversion: list[ConvRecovTimelinePoint]
    recovery: list[ConvRecovTimelinePoint]
    window: int


MaterialBucket = Literal["conversion", "even", "recovery"]


class MaterialRow(BaseModel):
    """One row in the material-stratified WDL table (section 2 of endgame-analysis-v2.md).

    Represents the user's performance when entering endgames with a specific
    material imbalance that persists 4 plies into the endgame:
    conversion (>= +1 pawn preserved), even, or recovery (<= -1 pawn preserved).
    Games where the imbalance does not persist fall into the "even" bucket to
    filter out transient noise from piece trades at the endgame boundary.
    """

    bucket: MaterialBucket
    label: str           # "Conversion (\u2265 +1)" | "Even" | "Recovery (\u2264 \u22121)"
    games: int
    win_pct: float       # 0-100
    draw_pct: float      # 0-100
    loss_pct: float      # 0-100
    score: float         # 0.0-1.0, formula: (win_pct + draw_pct/2) / 100


class ScoreGapMaterialResponse(BaseModel):
    """Endgame score difference + material-stratified WDL table (Phase 53).

    endgame_score: user's score (0.0-1.0) in games that reached an endgame.
    non_endgame_score: user's score in games that never reached an endgame.
    score_difference: endgame_score - non_endgame_score (signed, can be negative).
    overall_score: weighted combination across all games.
    material_rows: 3-row table — conversion / even / recovery — always present.
    """

    endgame_score: float        # 0.0-1.0
    non_endgame_score: float    # 0.0-1.0
    score_difference: float     # endgame_score - non_endgame_score (signed)
    overall_score: float        # user's overall score across ALL games
    material_rows: list[MaterialRow]  # 3 rows: conversion / even / recovery


class ClockStatsRow(BaseModel):
    """One row in the Clock Stats table — one per time control (Phase 54).

    Represents clock state at endgame entry for a specific time control bucket.
    Games without clock data are excluded from time columns but counted for net timeout.
    """

    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str  # "Bullet" | "Blitz" | "Rapid" | "Classical"
    total_endgame_games: int
    clock_games: int              # games where both user and opp clocks were available
    user_avg_pct: float | None    # mean (user_clock / time_control_seconds * 100) at entry; None if no time_control_seconds
    user_avg_seconds: float | None  # mean user_clock at entry in seconds; None if no clock data
    opp_avg_pct: float | None     # mean (opp_clock / time_control_seconds * 100) at entry; None if no time_control_seconds
    opp_avg_seconds: float | None   # mean opp_clock at entry in seconds; None if no clock data
    avg_clock_diff_seconds: float | None  # mean (user_clock - opp_clock) in seconds at entry; None if no clock data
    net_timeout_rate: float       # (timeout wins - timeout losses) / total_endgame_games * 100


class ClockPressureResponse(BaseModel):
    """Time Pressure at Endgame Entry — table broken down by time control (Phase 54).

    rows: per-time-control stats (only rows with >= MIN_GAMES_FOR_CLOCK_STATS games).
    total_clock_games: total games (across all time controls) with both clocks present.
    total_endgame_games: total distinct endgame games across all time controls.
    Both totals include all time controls (even hidden rows) for "Based on X of Y" note.
    """

    rows: list[ClockStatsRow]
    total_clock_games: int
    total_endgame_games: int


class TimePressureBucketPoint(BaseModel):
    """One data point in the time-pressure performance chart (Phase 55).

    bucket_index: 0-9 (0 = 0-10% time remaining, 9 = 90-100%)
    bucket_label: "0-10%" ... "90-100%"
    score: AVG score for this series in this bucket (0.0-1.0); None if game_count == 0
    game_count: number of games backing this data point
    """

    bucket_index: int
    bucket_label: str
    score: float | None
    game_count: int


class TimePressureChartRow(BaseModel):
    """Per-time-control data for the time-pressure chart (Phase 55).

    time_control: one of bullet/blitz/rapid/classical
    label: "Bullet" etc.
    total_endgame_games: total endgame games for this time control (with or without clock data)
    user_series: 10 points -- user's score by user's time bucket
    opp_series: 10 points -- opponent's score by opponent's time bucket
    """

    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str
    total_endgame_games: int
    user_series: list[TimePressureBucketPoint]
    opp_series: list[TimePressureBucketPoint]


class TimePressureChartResponse(BaseModel):
    """Time Pressure vs Performance chart data (Phase 55).

    rows: per-time-control data; only rows with >= MIN_GAMES_FOR_CLOCK_STATS games included.
    """

    rows: list[TimePressureChartRow]


class EndgameOverviewResponse(BaseModel):
    """Composed response for GET /api/endgames/overview.

    Serves the endgame dashboard payloads from a single request so the
    frontend can issue one HTTP call that runs sequentially on one AsyncSession
    instead of fanning out into parallel connections (Phase 52).
    """

    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    conv_recov_timeline: ConvRecovTimelineResponse
    score_gap_material: ScoreGapMaterialResponse  # Phase 53: score gap & material breakdown
    clock_pressure: ClockPressureResponse          # Phase 54: time pressure at endgame entry
    time_pressure_chart: TimePressureChartResponse  # Phase 55: time pressure vs performance chart
