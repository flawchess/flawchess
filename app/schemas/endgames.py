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

    Buckets are split by the Stockfish evaluation at the endgame-entry ply
    (REFAC-02): Conversion = user entered with eval >= +1.0 (>= +100 cp),
    Recovery = user entered with eval <= -1.0 (<= -100 cp). The old material
    imbalance + 4-ply persistence proxy is gone — eval coverage is 100%.

    Conversion: win rate when user entered this endgame type with eval advantage.
    Recovery: draw+win rate when user entered this endgame type with eval deficit.
    Both are computed per endgame type (D-11), not per game phase.
    """

    conversion_pct: float  # win rate when user entered with eval >= +1.0 (0-100), per D-08
    conversion_games: int  # games where user entered this endgame type with eval >= +1.0
    conversion_wins: int  # wins among those games
    conversion_draws: int  # draws among those games
    conversion_losses: int  # losses among those games (= conversion_games - wins - draws)

    recovery_pct: float  # draw+win rate when user entered with eval <= -1.0 (0-100), per D-09
    recovery_games: int  # games where user entered this endgame type with eval <= -1.0
    recovery_saves: int  # draws+wins among those games (kept for backward compat)
    recovery_wins: int  # wins among those games
    recovery_draws: int  # draws among those games


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
    total_games: int  # Total games matching current filters (not just endgame games)
    endgame_games: int  # Games that reached an endgame phase


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
    """Response for GET /api/endgames/performance (Phase 59-trimmed).

    Provides WDL comparison for endgame vs non-endgame games and the endgame win rate.
    Endgame games = games that spent >= ENDGAME_PLY_THRESHOLD plies in any endgame class.
    Non-endgame games = games that never reached any endgame class above the threshold.
    Phase 59 removed the aggregate conversion/recovery/skill fields (along with the
    admin gauge UI that consumed them) — see .planning/phases/59-*/59-CONTEXT.md.
    """

    endgame_wdl: EndgameWDLSummary  # games reaching any endgame class >= ENDGAME_PLY_THRESHOLD
    non_endgame_wdl: EndgameWDLSummary  # games NOT reaching any endgame class
    endgame_win_rate: float  # wins / total for endgame games only, 0-100


class EndgameTimelinePoint(BaseModel):
    """Single data point in the per-type rolling-window time series, sampled weekly.

    Represents the rolling win rate over the trailing `window` games of history
    (see EndgameTimelineResponse.window), measured after the final game of one
    ISO week. `date` is the Monday of that week as `YYYY-MM-DD`. Early points
    with fewer than MIN_GAMES_FOR_TIMELINE games in the window are dropped.
    """

    date: str  # Monday of the ISO week, "YYYY-MM-DD"
    win_rate: float  # rolling win rate (0.0-1.0) over trailing `window` games
    game_count: int  # number of games in the rolling window (<= window)
    # Count of games for THIS specific ISO week (NOT the trailing window).
    # Drives the muted volume-bar series on the frontend Win Rate by Endgame Type
    # chart so users see at a glance whether a weekly point is well-supported or
    # marginal (just over the 10-game floor). Mirrors `per_week_endgame_games`
    # on EndgameEloTimelinePoint (Phase 57.1).
    per_week_game_count: int


class EndgameOverallPoint(BaseModel):
    """Single data point in the overall endgame vs non-endgame rolling-window time series.

    Tracks two parallel series (endgame games, non-endgame games) merged by date.
    Either win_rate may be None if that series has no games on this date's window.
    """

    date: str
    endgame_win_rate: float | None  # rolling win rate for endgame games
    non_endgame_win_rate: float | None  # rolling win rate for non-endgame games
    endgame_game_count: int  # rolling window size for endgame series
    non_endgame_game_count: int  # rolling window size for non-endgame series
    window_size: int  # configured window size


class EndgameTimelineResponse(BaseModel):
    """Response for GET /api/endgames/timeline.

    overall: merged endgame vs non-endgame series aligned by date.
    per_type: per-endgame-class rolling win-rate series (keys are EndgameClass strings).
    window: configured rolling window size.

    Uses dict[str, ...] not dict[EndgameClass, ...] because Pydantic requires str keys
    for JSON serialization of dict models.
    """

    overall: list[EndgameOverallPoint]
    # per_type: per-endgame-class weekly win-rate series (keys are EndgameClass strings).
    per_type: dict[str, list[EndgameTimelinePoint]]
    window: int


MaterialBucket = Literal["conversion", "parity", "recovery"]


class MaterialRow(BaseModel):
    """One row in the eval-stratified WDL table (section 2 of endgame-analysis-v2.md).

    Represents the user's performance when entering endgames with a specific
    Stockfish evaluation at the endgame-entry ply (REFAC-02 \u2014 material_imbalance
    + 4-ply persistence proxy retired in favor of 100% Stockfish eval coverage):
    conversion (eval >= +1.0), parity (eval between -1.0 and +1.0), or
    recovery (eval <= -1.0). The bucket name is kept as `MaterialBucket` for
    schema/wire compatibility, but the underlying signal is engine eval, not
    material imbalance.
    """

    bucket: MaterialBucket
    label: str  # "Conversion (\u2265 +1.0)" | "Parity" | "Recovery (\u2264 \u22121.0)"
    games: int
    win_pct: float  # 0-100
    draw_pct: float  # 0-100
    loss_pct: float  # 0-100
    score: float  # 0.0-1.0, formula: (win_pct + draw_pct/2) / 100
    # opponent_score: mirror-bucket score (1 - user_score); None when sample < _MIN_OPPONENT_SAMPLE.
    opponent_score: float | None
    # opponent_games: opponent's sample size (== swap-bucket game count).
    opponent_games: int


class ScoreGapTimelinePoint(BaseModel):
    """One point in the score-difference timeline (quick-260417-o2l).

    date: Monday of the ISO week, YYYY-MM-DD.
    score_difference: endgame_score - non_endgame_score on a 0.0-1.0 scale,
        signed (e.g. 0.05 = endgame 5 percentage points stronger). Each side
        is the trailing-window mean of per-game scores (1.0 win / 0.5 draw /
        0.0 loss). Endgame and non-endgame games each carry their own
        trailing window of `timeline_window` games.
    endgame_game_count: games in the trailing endgame window (<= timeline_window).
    non_endgame_game_count: games in the trailing non-endgame window
        (<= timeline_window).
    endgame_score: absolute rolling-window mean score (0.0-1.0) for endgame
        games only — persists the per-side value so both the frontend
        two-line chart (Phase 68) and the insights `score_timeline`
        subsection can read absolute scores directly instead of
        reconstructing them from `score_difference`.
    non_endgame_score: absolute rolling-window mean score (0.0-1.0) for
        non-endgame games only — mirror of `endgame_score`. Invariant:
        abs((endgame_score - non_endgame_score) - score_difference) < 1e-9
        per bucket.
    """

    date: str
    score_difference: float
    endgame_game_count: int
    non_endgame_game_count: int
    # Count of games (endgame + non-endgame) played in THIS specific ISO week.
    # Drives the muted volume-bar series on the frontend Score % Difference
    # timeline so users see at a glance whether a weekly point is well-supported
    # or marginal. Mirrors the per_week_* fields on the other endgame timelines.
    per_week_total_games: int
    # Phase 68: absolute per-side rolling-window mean scores (0.0-1.0). Drives
    # the two-line Endgame vs Non-Endgame Score chart and the
    # `score_timeline` insights subsection's two per-part series blocks.
    endgame_score: float
    non_endgame_score: float


class ScoreGapMaterialResponse(BaseModel):
    """Endgame score difference + eval-stratified WDL table (Phase 53; REFAC-02 cutover).

    endgame_score: user's score (0.0-1.0) in games that reached an endgame.
    non_endgame_score: user's score in games that never reached an endgame.
    score_difference: endgame_score - non_endgame_score (signed, can be negative).
    material_rows: 3-row table — conversion / parity / recovery — split by the
        Stockfish eval at the endgame-entry ply (>= +1.0 / between -1.0 and
        +1.0 / <= -1.0). Field name kept as `material_rows` for wire-format
        compatibility; the underlying signal is engine eval, not material.

    Phase 60: each MaterialRow carries an opponent_score (1 - user_score[swap_bucket])
    and opponent_games. overall_score was removed; it was only consumed by the old
    global-average baseline display.

    quick-260417-o2l: `timeline` is a weekly rolling-window series of the score
    difference between endgame and non-endgame games. Each side keeps its own
    trailing `timeline_window`-game window so weeks with sparse activity on one
    side still reflect the broader history of that side.
    """

    endgame_score: float  # 0.0-1.0
    non_endgame_score: float  # 0.0-1.0
    score_difference: float  # endgame_score - non_endgame_score (signed)
    material_rows: list[MaterialRow]  # 3 rows: conversion / parity / recovery
    timeline: list[ScoreGapTimelinePoint]
    timeline_window: int


class ClockStatsRow(BaseModel):
    """One row in the Clock Stats table — one per time control (Phase 54).

    Represents clock state at endgame entry for a specific time control bucket.
    Games without clock data are excluded from time columns but counted for net timeout.
    """

    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    label: str  # "Bullet" | "Blitz" | "Rapid" | "Classical"
    total_endgame_games: int
    clock_games: int  # games where both user and opp clocks were available
    user_avg_pct: (
        float | None
    )  # mean (user_clock / base_time_seconds * 100) at entry; None if no base_time_seconds
    user_avg_seconds: float | None  # mean user_clock at entry in seconds; None if no clock data
    opp_avg_pct: (
        float | None
    )  # mean (opp_clock / base_time_seconds * 100) at entry; None if no base_time_seconds
    opp_avg_seconds: float | None  # mean opp_clock at entry in seconds; None if no clock data
    avg_clock_diff_seconds: (
        float | None
    )  # mean (user_clock - opp_clock) in seconds at entry; None if no clock data
    net_timeout_rate: float  # (timeout wins - timeout losses) / total_endgame_games * 100


class ClockPressureTimelinePoint(BaseModel):
    """One point in the clock-diff timeline (quick-260416-w3q).

    date: Monday of the ISO week, YYYY-MM-DD.
    avg_clock_diff_pct: mean of (user_clock - opp_clock) / base_time_seconds * 100
        over the trailing `timeline_window` games (see ClockPressureResponse).
        Positive means the user entered the endgame with more clock than the opponent.
    game_count: games represented in the window (<= timeline_window).
    """

    date: str
    avg_clock_diff_pct: float
    game_count: int
    # Count of clock-eligible endgame games in THIS specific ISO week (NOT the
    # trailing window). Drives the muted volume-bar series on the frontend
    # Average Clock Difference timeline. Mirrors the per_week_* fields on the
    # other endgame timelines.
    per_week_game_count: int


class ClockPressureResponse(BaseModel):
    """Time Pressure at Endgame Entry — table broken down by time control (Phase 54).

    rows: per-time-control stats (only rows with >= MIN_GAMES_FOR_CLOCK_STATS games).
    total_clock_games: total games (across all time controls) with both clocks present.
    total_endgame_games: total distinct endgame games across all time controls.
    Both totals include all time controls (even hidden rows) for "Based on X of Y" note.

    timeline: weekly rolling-window series of average clock-diff % across all time
        controls (quick-260416-w3q). Collapsed to a single series — filter by time
        control via the sidebar filter.
    timeline_window: rolling window size used for each timeline point.
    """

    rows: list[ClockStatsRow]
    total_clock_games: int
    total_endgame_games: int
    timeline: list[ClockPressureTimelinePoint]
    timeline_window: int


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


class TimePressureChartResponse(BaseModel):
    """Time Pressure vs Performance chart data (Phase 55, quick-260416-pkx pooled shape).

    user_series: 10 bucket points, pre-aggregated across all time controls that
        passed MIN_GAMES_FOR_CLOCK_STATS. Each point is the weighted average
        (score_sum / game_count) of user scores by user's time-remaining bucket.
    opp_series: 10 bucket points, same aggregation but by opponent's bucket
        and using 1 - user_score per game.
    total_endgame_games: total endgame games across all contributing time controls
        (used by the frontend for empty-state detection and the "Based on X" note).

    Per-time-control rows were dropped in quick-260416-pkx — the frontend previously
    re-aggregated them into a single series anyway, so the math now lives in the
    service layer (closer to the data).
    """

    user_series: list[TimePressureBucketPoint]
    opp_series: list[TimePressureBucketPoint]
    total_endgame_games: int


class EndgameEloTimelinePoint(BaseModel):
    """One weekly point for a (platform, time_control) combo (Phase 57 ELO-05; revised in Phase 57.1).

    date: Sunday of the ISO week (end of week), YYYY-MM-DD. Aligned with the asof
        rating moment so a daily rating chart at the same date shows the same value
        (assuming matching filter inputs).
    endgame_elo: skill-adjusted rating
        = round(actual_elo_at_date + 400 * log10(clamp(skill) / (1 - clamp))),
        anchored on the user's actual rating at the point's date (per-combo asof-join
        with forward-fill from the latest game played on or before the ISO-week-end).
        skill is the endgame-skill composite (Conv Win %, Parity Score %, Recov Save %)
        over the trailing ENDGAME_ELO_TIMELINE_WINDOW endgame games. When skill == 0.5
        the formula returns actual_elo_at_date exactly (zero delta at the neutral mark).
    actual_elo: the user's rating at this point's date, sourced via the same per-combo
        asof-join used as the endgame_elo anchor. Both lines share the anchor so the
        gap between them IS the skill signal.
    endgame_games_in_window: count of endgame games contributing to the trailing-window
        skill computation. Drives the >=MIN_GAMES_FOR_TIMELINE (10) emission floor and
        the frontend tooltip's "past N games" copy.
    per_week_endgame_games: count of endgame games for THIS specific ISO week (NOT the
        trailing window). Frontend uses this for the muted volume-bar series so users can
        see at a glance whether a weekly point is well-supported (50+ games this week)
        or marginal (just over the 10-game floor).
    """

    date: str
    endgame_elo: int
    actual_elo: int
    endgame_games_in_window: int
    per_week_endgame_games: int


class EndgameEloTimelineCombo(BaseModel):
    """One (platform, time_control) combo's paired-line series (Phase 57 ELO-05).

    combo_key: underscore-joined key like "chess_com_blitz" / "lichess_classical".
        Frontend uses this as the lookup key into ELO_COMBO_COLORS.
    platform / time_control: denormalized for the legend label, avoiding frontend
        string-split and keeping the wire format explicit.
    points: weekly points sorted by date ASC. Combos with zero qualifying points
        are dropped from the response entirely (D-10 tier 2), so callers never
        receive an empty `points` list.
    """

    combo_key: str
    platform: Literal["chess.com", "lichess"]
    time_control: Literal["bullet", "blitz", "rapid", "classical"]
    points: list[EndgameEloTimelinePoint]


class EndgameEloTimelineResponse(BaseModel):
    """Response wrapper for the Endgame ELO timeline (Phase 57 ELO-05).

    combos: one series per qualifying (platform, time_control). Ordered
        chess.com-first then lichess, bullet->blitz->rapid->classical within each
        platform (matches _TIME_CONTROL_ORDER elsewhere in endgame_service).
        Empty list when no combo has any qualifying weekly point, the frontend
        then swaps the chart body to an empty-state.
    timeline_window: rolling window size used for each point (== ENDGAME_ELO_TIMELINE_WINDOW).
    """

    combos: list[EndgameEloTimelineCombo]
    timeline_window: int


class EndgameOverviewResponse(BaseModel):
    """Composed response for GET /api/endgames/overview.

    Serves the endgame dashboard payloads from a single request so the
    frontend can issue one HTTP call that runs sequentially on one AsyncSession
    (Phase 52). The conv/recov rolling timeline sub-payload was removed in Phase 59
    along with the admin gauge UI that consumed it.
    """

    stats: EndgameStatsResponse
    performance: EndgamePerformanceResponse
    timeline: EndgameTimelineResponse
    score_gap_material: ScoreGapMaterialResponse  # Phase 53: score gap & material breakdown
    clock_pressure: ClockPressureResponse  # Phase 54: time pressure at endgame entry
    time_pressure_chart: TimePressureChartResponse  # Phase 55: time pressure vs performance chart
    endgame_elo_timeline: EndgameEloTimelineResponse  # Phase 57: paired Endgame ELO + Actual ELO series per (platform, TC)
