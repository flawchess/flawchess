"""Pydantic v2 schemas for the endgame analytics API.

Provides response models for:
- GET /api/endgames/stats: per-category W/D/L with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
- GET /api/endgames/overview: composed response including time pressure cards (Phase 88)
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

    Phase 84: opponent baselines via same-game mirror identity, scoped per
    endgame class. opponent_conversion = opponent's win rate when opponent
    entered with eval advantage (derived from user_recovery_*);
    opponent_recovery = opponent's save rate when opponent entered with eval
    deficit (derived from user_conversion_*). Gated on _MIN_OPPONENT_SAMPLE
    against the mirror bucket size.
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

    # Phase 84: per-class opponent baselines via same-game mirror identity.
    opponent_conversion_pct: float | None
    """None when recovery_games < _MIN_OPPONENT_SAMPLE; else opponent's win-rate when opponent entered with eval advantage (Phase 84, mirror identity)."""
    opponent_conversion_games: int
    """== recovery_games (mirror sample size, always int, possibly 0)."""
    opponent_recovery_pct: float | None
    """None when conversion_games < _MIN_OPPONENT_SAMPLE; else opponent's save-rate when opponent entered with eval deficit."""
    opponent_recovery_games: int
    """== conversion_games (mirror sample size, always int, possibly 0)."""


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

    # Phase 87 follow-up: Wilson score-test p-value of this class's WDL vs 50%.
    # Gated to None when `total < PVALUE_RELIABILITY_MIN_N`. Drives the per-card
    # Score bullet sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS AND
    # isConfident(level) AND outside neutral band) in EndgameTypeCard.
    score_p_value: float | None = None

    # Phase 87.1 (SEED-016, D-05): per-span mean Score Gap for this endgame type.
    # gap_span = exit_score - ES_sigmoid(entry_eval, user_color); positive = user
    # outperformed the Stockfish baseline across spans of this type. Populated via
    # compute_paired_difference_test in app/services/score_confidence.py (same
    # helper Phase 85.1 uses for the page-level Achievable Score Gap).
    # User-facing label is "Score Gap" (card row) / "Endgame Type Score Gap"
    # (concepts). Internal name retains "achievable" to mark the math-family with
    # achievable_score_gap (Phase 85.1) — see Phase 87.1 CONTEXT D-02 for the
    # dual-label rationale. n-gates follow compute_paired_difference_test:
    #   n == 0       -> mean = 0.0 (None here), p/CI all None
    #   n == 1       -> mean populated, p/CI all None
    #   n >= 2       -> ci_low/ci_high populated
    #   n >= CONFIDENCE_MIN_N (=10) -> p_value populated
    # Defaults are None for backward compat with existing constructor call sites.
    type_achievable_score_gap_mean: float | None = None
    type_achievable_score_gap_n: int | None = None
    type_achievable_score_gap_p_value: float | None = None
    type_achievable_score_gap_ci_low: float | None = None
    type_achievable_score_gap_ci_high: float | None = None


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

    # Phase 81 (D-11): entry-eval aggregation for "Endgame Start vs End" twin-tile section.
    # Defaults are required so existing call sites that build the response without these
    # fields (tests, prior callers) keep working — see Pitfall 7 in 81-RESEARCH.md.
    entry_eval_mean_pawns: float = 0.0
    """Avg Stockfish eval at endgame entry, signed from user's perspective, in pawns. 0.0 when n=0."""

    entry_eval_n: int = 0
    """Count of games contributing to entry_eval_mean_pawns. Mate scores and NULL evals excluded; per-game (deduped over multi-class entry_rows)."""

    entry_eval_p_value: float | None = None
    """Wald-z two-sided p-value of mean vs 0 cp. None when entry_eval_n < 10 (D-05 reliability gate)."""

    endgame_score_p_value: float | None = None
    """Wilson score-test two-sided p-value of endgame_wdl score vs 50%. None when endgame_wdl.total < 10."""

    non_endgame_score_p_value: float | None = None
    """Wilson score-test two-sided p-value of non_endgame_wdl score vs 50%. None when non_endgame_wdl.total < 10."""

    entry_eval_ci_low_pawns: float | None = None
    """Lower bound of 95% Wald-z CI on entry_eval_mean_pawns (signed, in pawns). None when entry_eval_n < 2."""

    entry_eval_ci_high_pawns: float | None = None
    """Upper bound of 95% Wald-z CI on entry_eval_mean_pawns (signed, in pawns). None when entry_eval_n < 2."""

    # Phase 83 (D-21): Stockfish-baseline achievable score for "Where you start" tile.
    # Defaults match the Phase 81 D-11 safe-empty pattern so existing call sites keep working.
    entry_expected_score: float = 0.0
    """Mean per-game expected score from endgame-entry eval, via Lichess sigmoid (mate->0/1). 0.0 when n=0."""

    entry_expected_score_n: int = 0
    """Count of games contributing to entry_expected_score. Mate INCLUDED (D-06); NULL evals excluded; |eval_cp| < 2000 clip applied."""

    entry_expected_score_p_value: float | None = None
    """Two-sided p-value vs 50%. None when entry_expected_score_n < 10."""

    entry_expected_score_ci_low: float | None = None
    """Lower bound of 95% CI on entry_expected_score. None when entry_expected_score_n < 2."""

    entry_expected_score_ci_high: float | None = None
    """Upper bound of 95% CI on entry_expected_score. None when entry_expected_score_n < 2."""

    # Phase 85.1 (SEC1-10): paired one-sample z-test of per-game
    # (actual_score - expected_score) across the same bucket_rows cohort as
    # entry_expected_score. Server-authoritative — replaces the previous
    # frontend derivation `endgame_score - entry_expected_score`.
    # Defaults match the Phase 83 D-11 safe-empty pattern so existing call
    # sites (older tests) construct the response without explicit args.
    achievable_score_gap: float = 0.0
    """Mean over the surviving bucket_rows of (actual_score_i - expected_score_i).
    Always-present scalar (0.0 when n=0). Same cohort filter as entry_expected_score."""

    achievable_score_gap_p_value: float | None = None
    """Paired one-sample two-sided z-test p-value of mean diff vs 0.
    None when surviving n < PVALUE_RELIABILITY_MIN_N (=10)."""

    achievable_score_gap_ci_low: float | None = None
    """Lower bound of 95% Wald-z CI on achievable_score_gap.
    None when surviving n < 2 (Bessel variance undefined)."""

    achievable_score_gap_ci_high: float | None = None
    """Upper bound of 95% Wald-z CI on achievable_score_gap.
    None when surviving n < 2 (Bessel variance undefined)."""


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
    label: str  # "Conversion (>= +1.0)" | "Parity" | "Recovery (<= -1.0)"
    games: int
    win_pct: float  # 0-100
    draw_pct: float  # 0-100
    loss_pct: float  # 0-100
    score: float  # 0.0-1.0, formula: (win_pct + draw_pct/2) / 100
    # Phase 87.2 (D-05): opponent_score, opponent_games, diff_p_value, diff_ci_low,
    # diff_ci_high deleted. The mirror-bucket Wald-z peer-bullet was mathematically
    # degenerate (Conv-Gap == Recov-Gap by symmetry; Parity-Gap affine of gauge).
    # Replaced by the eval-baseline Delta-ES Score Gap fields on ScoreGapMaterialResponse.


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
    # Count of ENDGAME games (only) played in THIS specific ISO week. Threaded
    # downstream into `EndgameEloTimelinePoint.per_week_endgame_games` so the
    # Endgame ELO Timeline volume bars show per-week endgame activity (not the
    # trailing 100-game window count). Defaults to 0 for back-compat with older
    # fixtures and existing tests that don't set it.
    per_week_endgame_games: int = 0
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

    Phase 87.2 (D-05/D-06): the 5 mirror-bucket rate-diff fields (skill, opp_skill,
    skill_diff_p_value, skill_diff_ci_low, skill_diff_ci_high on this response;
    opponent_score, opponent_games, diff_p_value, diff_ci_low, diff_ci_high on
    MaterialRow) have been deleted and replaced by the 20 eval-baseline Delta-ES
    Score Gap fields below (section2_score_gap_{conv,parity,recov,skill}_{mean,n,
    p_value,ci_low,ci_high}). The rate-based peer-bullet was mathematically
    degenerate; see Phase 87.2 CONTEXT D-05.

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

    # Phase 85.1 (SEC1-08, SEC1-09): independent two-sample z-test on the
    # chess-score difference between endgame and non-endgame cohorts.
    # p_value is gated to None when min(endgame_wdl.total, non_endgame_wdl.total)
    # < PVALUE_RELIABILITY_MIN_N (=10); CI bounds are gated when min n < 2.
    # Defaults are None so existing tests that construct ScoreGapMaterialResponse
    # without these fields keep working.
    score_difference_p_value: float | None = None
    """Two-sided p-value of (endgame_score - non_endgame_score) vs 0.
    None when min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N (=10)."""

    score_difference_ci_low: float | None = None
    """Lower bound of 95% Wald-z CI on score_difference. None when min(...) < 2."""

    score_difference_ci_high: float | None = None
    """Upper bound of 95% Wald-z CI on score_difference. None when min(...) < 2."""

    # Phase 87.2 (D-06): per-bucket Score Gap fields on the Section 2 response.
    # Flat shape mirrors Phase 87.1's type_achievable_score_gap_* on EndgameCategoryStats.
    # D-01: positive = user outperformed Stockfish baseline; negative = below.
    # Defaults are None for backward compat with existing constructor call sites.

    # Conversion bucket (eval_entry >= +1.0 pawn, user perspective):
    section2_score_gap_conv_mean: float | None = None
    section2_score_gap_conv_n: int | None = None
    section2_score_gap_conv_p_value: float | None = None
    section2_score_gap_conv_ci_low: float | None = None
    section2_score_gap_conv_ci_high: float | None = None

    # Parity bucket (|eval_entry| <= 1.0 pawn):
    section2_score_gap_parity_mean: float | None = None
    section2_score_gap_parity_n: int | None = None
    section2_score_gap_parity_p_value: float | None = None
    section2_score_gap_parity_ci_low: float | None = None
    section2_score_gap_parity_ci_high: float | None = None

    # Recovery bucket (eval_entry <= -1.0 pawn):
    section2_score_gap_recov_mean: float | None = None
    section2_score_gap_recov_n: int | None = None
    section2_score_gap_recov_p_value: float | None = None
    section2_score_gap_recov_ci_low: float | None = None
    section2_score_gap_recov_ci_high: float | None = None

    # Phase 87.4 (D-05): Skill composite retired end-to-end. The previous
    # section2_score_gap_skill_* fields (ΔES Skill, equal-weighted mean of
    # the three bucket means) and endgame_skill_rate_mean (rate composite for
    # the gauge) were deleted. See .planning/notes/endgame-skill-dropped-
    # conversion-elo.md for rationale (no composite definition survived
    # scrutiny on cohort de-confounding, individual interpretation, temporal
    # stability, or the Phase 57 median-coincide invariant).


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


class ClockDiffTimelinePoint(BaseModel):
    """One ISO-week point on the Average Clock Difference over Time line chart.

    Plan 88-15 (CONTEXT §2 A-2): restored after the Phase 88-07 cleanup deleted
    the line chart that previously consumed an equivalent shape on the legacy
    clock-pressure response. Renamed (vs the pre-88-07 timeline point class) to
    make the design-pivot history obvious to future readers.

    date: Monday of the ISO week, YYYY-MM-DD.
    avg_clock_diff_pct: rolling-window mean of
        (user_clock - opp_clock) / base_time_seconds * 100 — in PERCENT units,
        not fraction. 50.0 means the user entered the endgame with 50% more of
        the base clock than the opponent. Matches the chart Y-axis unit and the
        pre-deletion convention.
    game_count: count of eligible games in the trailing rolling window
        (<= CLOCK_PRESSURE_TIMELINE_WINDOW). Drives confidence in the rolling
        mean — small windows hint at sparse early history.
    per_week_game_count: count of clock-eligible endgame games in THIS specific
        ISO week (NOT the trailing window). Drives the muted volume-bar series
        on the frontend chart. Mirrors per_week_* fields on the other endgame
        timelines.
    """

    date: str
    avg_clock_diff_pct: float
    game_count: int
    per_week_game_count: int


class ClockDiffTimelineResponse(BaseModel):
    """Wrapper for the Average Clock Difference over Time line chart payload.

    Plan 88-15 (CONTEXT §2 A-2): served on EndgameOverviewResponse alongside
    time_pressure_cards. points is empty when no game in the user's filtered
    set passes the clock-eligibility predicate — the frontend hides the chart
    in that case.

    points: chronological list of ISO-week points sorted by date ascending.
    """

    points: list[ClockDiffTimelinePoint]


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
    """One weekly point for a (platform, time_control) combo of the Endgame ELO
    Timeline (Phase 57 ELO-05; Phase 57.1 anchor change; Phase 87.6 amendment
    2026-05-17 — logistic stretch anchored on Actual ELO).

    date: Monday of the ISO week, YYYY-MM-DD. Aligned with the Score Gap timeline
        for x-axis consistency.
    endgame_elo: ``actual_elo + spread / 2`` where
        ``spread = 400 * log10((s_E / (1 - s_E)) / (s_N / (1 - s_N)))`` and
        ``s_E``, ``s_N`` are the trailing-window mean scores on the endgame /
        non-endgame subsets. The ``400`` is the same logistic scale FIDE Elo
        uses for its expected-score curve — not a calibration knob.
        Supersedes the earlier Phase 87.6 per-side FIDE PR mapping; see
        ``.planning/notes/endgame-elo-logistic-anchored.md`` for derivation.
    non_endgame_elo: ``actual_elo - spread / 2`` (same ``spread``). Endgame ELO
        and Non-Endgame ELO sit symmetrically around Actual ELO by construction:
        ``endgame_elo + non_endgame_elo == 2 * actual_elo`` for every emitted point.
    actual_elo: the user's rating at this point's date, sourced via the per-combo
        asof-join. Three-line chart: Actual ELO is bracketed by Endgame ELO and
        Non-Endgame ELO, making the over/underperformance signal visually obvious.
    endgame_games_in_window: count of endgame games contributing to the trailing-window
        score mean. A point is only emitted when both the endgame and non-endgame
        trailing windows hold >= MIN_GAMES_FOR_TIMELINE (10) games. Drives the
        frontend tooltip's "past N games" copy.
    per_week_endgame_games: count of endgame games played in THIS specific ISO week
        (NOT the trailing window). Used by the insights service trend math
        (`per_week_endgame_games` summed across the series).
    per_week_total_games: count of ALL games (endgame + non-endgame) played in
        THIS specific ISO week. Drives the muted volume-bar series on the
        frontend Endgame ELO Timeline. The chart plots both Endgame ELO and
        Non-Endgame ELO, so the volume bar reflects the total weekly activity
        feeding both PR lines (matches the Endgame Score Gap over Time chart's
        volume bars, which also count both sides).
    """

    date: str
    endgame_elo: int
    non_endgame_elo: int
    actual_elo: int
    endgame_games_in_window: int
    per_week_endgame_games: int
    per_week_total_games: int = 0


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


class PressureQuintileBullet(BaseModel):
    """Per-quintile Score-Delta bullet for the time pressure card.

    Phase 88.1 (D-07 supersedes D-05): the global cohort layer was retired in
    favour of a same-game opponent-quintile split. The user's own filtered
    games are bucketed twice — once by the USER's clock-pct at endgame entry
    (yielding user_score for quintile Q), once by the OPPONENT's clock-pct
    (yielding opp_score for the matching quintile index). The two splits are
    independent samples drawn from the same game-set; the significance test
    is the unpaired two-sample Wilson via compute_score_difference_test.

    quintile_index: 0..4, where 0 = 0-20% clock remaining (maximum pressure),
        4 = 80-100% clock remaining (minimum pressure).
    quintile_label: human-readable range string e.g. "0-20%".
    n: user-side games in this quintile bin (drives the displayed sample-size
        chip; the opponent-side count is gated by min(n_user, n_opp) >=
        MIN_GAMES_PER_PRESSURE_BIN inside _build_quintile_bullets).
    n_opp: opponent-side games in the matching opponent-clock quintile. The
        two splits are independent samples drawn from the same game-set, so
        this can differ from n; the tooltip shows both counts separately.
    delta: user_score - opp_score where each side is bucketed by its OWN
        clock-pct at endgame entry. 0.0 when either side has zero games at
        this quintile (no signal to compare).
    p_value: unpaired two-sample Wilson score-test p-value of
        H0: user_score - opp_score == 0; None when the n-gate is unmet.
    ci_low/ci_high: 95% CI on delta from the same two-sample test; None when
        the n-gate is unmet.
    opp_score: opponent's same-game score in the matching opponent-clock
        quintile; None when the n-gate is unmet.
    """

    quintile_index: int  # 0..4
    quintile_label: str  # "0-20%", "20-40%", "40-60%", "60-80%", "80-100%"
    n: int
    n_opp: int
    delta: float
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    opp_score: float | None


class ClockGapBullet(BaseModel):
    """Clock advantage/disadvantage at endgame entry (Phase 88).

    Summarises the per-game (user_clock - opp_clock) / base_clock distribution
    for one time control. The mean_diff_pct is a fraction (not a percentage):
    0.05 means the user had 5% more base-clock time than the opponent at entry.

    n: games with both clocks available and valid base_clock.
    mean_diff_pct: mean per-game (user_clock - opp_clock) / base_clock.
    p_value/ci_low/ci_high: paired one-sample z-test output from
        compute_paired_difference_test; None when insufficient data.
    """

    n: int
    mean_diff_pct: float
    p_value: float | None
    ci_low: float | None
    ci_high: float | None


class TimePressureTcCard(BaseModel):
    """Per-time-control time pressure card carrying Clock Gap + Score-Delta bullets (Phase 88).

    tc: time control bucket.
    total: total endgame games for this TC (used to gate card visibility).
    clock_gap: paired clock-advantage bullet across all games in this TC.
    quintiles: exactly 5 PressureQuintileBullet entries, ordered Q0..Q4 (0=max pressure).

    Top-zone summary stats restored from the deleted EndgameClockPressureSection
    (CONTEXT §2 A-3, Plan 88-14). The 5 averages are None when no game in this
    TC has clock data (e.g. legacy imports without ply/clock arrays). All ship
    with explicit Pydantic defaults so legacy call sites that build
    TimePressureTcCard(...) keyword-style without these new args do not break
    (B-2 lock).

    user_avg_pct: mean (user_clock / base_time_seconds) across clock-eligible
        games in this TC. Fraction (0..1) — 0.47 means the user entered endgames
        with 47% of their starting clock remaining on average.
    user_avg_seconds: mean user_clock in absolute seconds at endgame entry.
    opp_avg_pct: mean (opp_clock / base_time_seconds), fraction.
    opp_avg_seconds: mean opp_clock in absolute seconds.
    avg_clock_diff_seconds: mean (user_clock − opp_clock) in absolute seconds.
        Related to clock_gap.mean_diff_pct (same metric in fraction units) but
        NOT redundant — one is a fraction, the other is signed seconds.
    net_timeout_rate: (timeout_wins − timeout_losses) / total. Fraction units
        (0.005 = 0.5%) consistent with clock_gap.mean_diff_pct's convention.
        0.0 when neither side timed out.
    """

    tc: Literal["bullet", "blitz", "rapid", "classical"]
    total: int
    user_avg_pct: float | None = None
    user_avg_seconds: float | None = None
    opp_avg_pct: float | None = None
    opp_avg_seconds: float | None = None
    avg_clock_diff_seconds: float | None = None
    net_timeout_rate: float = 0.0
    clock_gap: ClockGapBullet
    quintiles: list[PressureQuintileBullet]  # always 5, ordered Q0..Q4


class TimePressureCardsResponse(BaseModel):
    """Time pressure cards response — one card per TC that meets MIN_GAMES_PER_TC_CARD (Phase 88).

    cards: list of TimePressureTcCard, ordered bullet -> blitz -> rapid -> classical.
        Only includes TCs where total endgame games >= MIN_GAMES_PER_TC_CARD (20).
    """

    cards: list[TimePressureTcCard]


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
    time_pressure_cards: TimePressureCardsResponse  # Phase 88: per-TC time pressure cards
    clock_diff_timeline: ClockDiffTimelineResponse  # Plan 88-15 (CONTEXT §2 A-2): restored Average Clock Difference over Time line chart payload
    endgame_elo_timeline: EndgameEloTimelineResponse  # Phase 57 / 87.5 D-06: paired Endgame ELO + Actual ELO series per (platform, TC) via additive K · eg_score_gap
