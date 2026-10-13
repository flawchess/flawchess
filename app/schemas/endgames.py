"""Pydantic v2 schemas for the endgame analytics API.

Provides response models for:
- GET /api/endgames/stats: per-category W/D/L with inline conversion/recovery stats
- GET /api/endgames/games: paginated game list filtered by endgame class
- GET /api/endgames/ranked-stats: filter-free per-TC ranked-sample payload for the
  percentile-first Stats tab (Phase 238; EndgameRankedStatsResponse)
"""

import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.openings import GameRecord
from app.services.global_percentile_cdf import CdfMetricId

EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]
EndgameLabel = Literal["Rook", "Minor Piece", "Pawn", "Queen", "Mixed", "Pawnless"]

# Time-control union used as the key type for the per-TC ranked payload and the
# rating anchors. Inline string union matches the
# `tc: 'bullet' | 'blitz' | 'rapid' | 'classical'` pattern used on
# EndgameEloTimelineCombo and RankedTcStats.
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]


class RatingAnchorOut(BaseModel):
    """Blended anchor + per-platform composition for the ranked-metric popover.

    D-12 Reversal Amendment (CONTEXT 2026-05-27). The anchor is the
    game-weighted median of converted-chess.com + native-lichess ratings.
    See: .planning/notes/percentile-anchor-d12-reversal.md (rationale, risk profile).

    `anchor_rating` is the blended Lichess-equivalent (post-conversion for
    chess.com games; native for lichess games). The per-platform game-count and
    native-median fields exist solely to support the four tooltip-disclosure
    branches in `RankedMetricPopover`:
      (a) Mixed user (n_chesscom_games > 0 AND n_lichess_games > 0): blended
          composition prose — names both platforms with their native medians.
      (b) Pure-lichess user (n_chesscom_games == 0): drops the chess.com clause;
          flags "native rating" so the user knows no conversion was applied.
      (c) Pure-chess.com user (n_lichess_games == 0): drops the lichess clause;
          discloses the ChessGoals snapshot conversion.
      (d) Suppression (both counts == 0): the popover omits the anchor line at the caller.

    Provenance: populated from the `user_rating_anchors` row written by
    `app/services/user_benchmark_percentiles_service.py::compute_anchors_for_user`
    (Plan 10 blended-anchor rewrite).
    """

    anchor_rating: int
    n_chesscom_games: int
    n_lichess_games: int
    chesscom_median_native: int | None = None
    lichess_median_native: int | None = None


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
    # Gated to None when `total < PVALUE_RELIABILITY_MIN_N`. Kept on the
    # response for compatibility; the TypeTable does not render it.
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

    # Phase 239 D-14: TypeTable verdict gates, set by the ranked service only (False
    # elsewhere). A cell outside its typical band gets red/green only when True: the
    # 99% Wilson CI of the rate excludes the band centre (cohort median stand-in), or
    # the 99% CI of the Score Gap excludes 0.
    conversion_significant: bool = False
    recovery_significant: bool = False
    type_achievable_score_gap_significant: bool = False

    # quick-260519-ni3: descriptive components of the Score Gap. Computed over the
    # exact same span cohort as type_achievable_score_gap_* (same NULL-eval gate),
    # so end_mean - start_mean == gap_mean holds exactly (reconciliation invariant).
    # None when type_achievable_score_gap_n == 0 (no eligible spans).
    # start = mean(es_entry) per span; end = mean(exit_score) per span.
    # These are unsigned expected-score aggregates (0-1 range), no CI / p-value.
    type_achievable_score_start_mean: float | None = None
    type_achievable_score_end_mean: float | None = None

    # Quick task 260519-lu0: WDLStats-aligned score/eval/last_played_at fields.
    # Aligns EndgameCategoryStats with WDLStats (api.ts) so PositionResultsPanel
    # can consume it directly. Defaults match _build_wdl_stats's total==0 path so
    # existing constructor call sites that don't pass them remain valid.
    score: float = 0.5
    confidence: Literal["low", "medium", "high"] = "low"
    p_value: float = 1.0
    ci_low: float = 0.5
    ci_high: float = 0.5
    avg_eval_pawns: float | None = None
    eval_ci_low_pawns: float | None = None
    eval_ci_high_pawns: float | None = None
    eval_n: int = 0
    eval_p_value: float | None = None
    eval_confidence: Literal["low", "medium", "high"] = "low"
    last_played_at: datetime.datetime | None = None
    eval_baseline_pawns: float = (
        0.25  # always EVAL_BASELINE_PAWNS_WHITE for endgames (color-agnostic, D-02)
    )


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

    Used in RankedOverallOut to compare endgame games vs non-endgame games.
    All percentages are 0-100.
    """

    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float


MaterialBucket = Literal["conversion", "parity", "recovery"]


# Phase 87.2 (D-05): opponent_score, opponent_games, diff_p_value, diff_ci_low,
# diff_ci_high deleted. The mirror-bucket Wald-z peer-bullet was mathematically
# degenerate (Conv-Gap == Recov-Gap by symmetry; Parity-Gap affine of gauge).
# Replaced by the eval-baseline Delta-ES Score Gap (the achievable_score_gap metric).


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

    # Phase 87.4 (D-05): Skill composite retired end-to-end. The previous
    # score_gap_skill_* fields (ΔES Skill, equal-weighted mean of
    # the three bucket means) and endgame_skill_rate_mean (rate composite for
    # the gauge) were deleted. See .planning/notes/endgame-skill-dropped-
    # conversion-elo.md for rationale (no composite definition survived
    # scrutiny on cohort de-confounding, individual interpretation, temporal
    # stability, or the Phase 57 median-coincide invariant).


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

    Plan 88-15 (CONTEXT §2 A-2): returned by compute_clock_diff_timeline; the ranked service
    reads its points per time control. points is empty when no game in the user's filtered
    set passes the clock-eligibility predicate — the frontend hides the chart
    in that case.

    points: chronological list of ISO-week points sorted by date ascending.
    """

    points: list[ClockDiffTimelinePoint]


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
        MIN_GAMES_PER_PRESSURE_BIN inside build_quintile_bullets).
    n_opp: opponent-side games in the matching opponent-clock quintile. The
        two splits are independent samples drawn from the same game-set, so
        this can differ from n; the tooltip shows both counts separately.
    delta: user_score - opp_score where each side is bucketed by its OWN
        clock-pct at endgame entry. 0.0 when either side has zero games at
        this quintile (no signal to compare).
    p_value: unpaired two-sample Wilson score-test p-value of
        H0: user_score - opp_score == 0; None when the n-gate is unmet.
    ci_low/ci_high: 99% CI on delta (Phase 239 D-14) from the same two-sample
        test; None when the n-gate is unmet.
    opp_score: opponent's same-game score in the matching opponent-clock
        quintile; None when the n-gate is unmet.
    significant: the 99% CI excludes 0 (D-14). Only then does a dot outside the
        typical band get its red/green colour.
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
    significant: bool = False


# ---------------------------------------------------------------------------
# Phase 238 (SEED-196): percentile-first Endgame Stats payload.
#
# GET /api/endgames/ranked-stats returns, per time control that has at least one
# ranked-sample game, the 11 peer-ranked metric values computed ON READ from the
# canonical ranked slice (rated, human, opponents within 100 Elo, last 36 months,
# at most 3000 games per TC). Values describe the same games the persisted
# percentiles rank (D-00b, D-07). The endpoint takes no filters (D-01).
# ---------------------------------------------------------------------------

# Rank status of one (metric, TC) cell (D-09 / D-11):
#   ranked      - value plus a persisted percentile
#   below_floor - not enough games to rank yet (binding count vs floor in the metric)
#   unranked    - value is computable but no persisted percentile exists yet
#   pending     - entry evals missing, value not computable yet ("analyzing")
RankStatus = Literal["ranked", "below_floor", "unranked", "pending"]


class RankedMetricOut(BaseModel):
    """One peer-ranked metric for one time control.

    value: fraction units (0.62 = 62%, a score gap of 0.05 = 5 points); None only
        when it is not computable (no eligible row, or entry evals still pending).
    n: metric-relevant sample size under the Stage A/B CTE's n definition (endgame
        games for score_gap; non-null d_i for achievable; bucket spans for the rates
        and bucket gaps; least(user, opponent pressured) for time pressure; pool
        size for the clock metrics).
    floor_n / floor_required: the BINDING count and the floor it is compared to
        (e.g. min(endgame, non-endgame) vs 30 for score_gap). When the TC has no
        anchor yet, floor_n is the non-Daily ranked game count and floor_required
        is the 30-game anchor floor ("18 of 30").
    percentile: the persisted Stage A/B percentile; set only when status == "ranked".
    ci_low / ci_high / p_value: popover-footer statistics, 99% CI (None where the metric
        has none or the n-gate is unmet).
    """

    metric: CdfMetricId
    value: float | None
    n: int
    floor_n: int
    floor_required: int
    percentile: float | None
    status: RankStatus
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    # Phase 239 D-14: the percentile verdict (red/green) shows only when True: the 99% CI
    # excludes the null (0 for a difference, the cohort p50 for a raw rate) on the
    # verdict's side. A ranked cell outside 25-75 without it renders neutral.
    significant: bool = False


class RankedBucketOut(BaseModel):
    """W/D/L counts for one entry-eval bucket (conversion / parity / recovery).

    Counted over the same games as the conversion / parity / recovery rate, so
    rate == wins/games, (wins + draws/2)/games, (wins + draws)/games hold exactly.
    """

    bucket: MaterialBucket
    games: int
    wins: int
    draws: int
    losses: int


class RankedEntryFlowOut(BaseModel):
    """Endgame entry flow: mean entry eval, expected vs actual score.

    expected_score / actual_score are means over the achievable-score-gap cohort
    (n games), so actual - expected equals the achievable_score_gap metric value.
    entry_eval_mean_pawns is the mean white-signed-to-user entry eval in pawns over
    cp-only rows (entry_eval_n).
    """

    entry_eval_mean_pawns: float | None
    entry_eval_n: int
    expected_score: float | None
    actual_score: float | None
    n: int


class RankedOverallOut(BaseModel):
    """Overall block for one TC: endgame vs non-endgame WDL plus the entry flow."""

    endgame_wdl: EndgameWDLSummary
    non_endgame_wdl: EndgameWDLSummary
    entry_flow: RankedEntryFlowOut


class RankedTimePressureOut(BaseModel):
    """Time Pressure curve for one TC (per-quintile score gaps); empty without clock data."""

    quintiles: list[PressureQuintileBullet] = []


class RankedTcStats(BaseModel):
    """Everything the Stats tab shows for one time control, from the ranked sample.

    ranked_games: games in the ranked sample (includes chess.com Daily).
    anchor_games: games counted toward the rating anchor (excludes chess.com Daily,
        mirroring the anchor CTE); anchor_min_games is the 30-game floor.
    eval_pending_games: ranked games whose entry evals are not completed yet.
    metrics: all 11 CdfMetricId keys, always present for a listed TC.
    buckets: three entries in conversion, parity, recovery order.
    The timelines, time_pressure curve and type_categories are empty for a TC
    without the data to build them.
    """

    tc: TimeControlBucket
    ranked_games: int
    anchor_games: int
    anchor_min_games: int
    anchor: RatingAnchorOut | None
    eval_pending_games: int
    metrics: dict[CdfMetricId, RankedMetricOut]
    overall: RankedOverallOut
    buckets: list[RankedBucketOut]
    time_pressure: RankedTimePressureOut
    score_gap_timeline: list[ScoreGapTimelinePoint] = []
    score_gap_timeline_window: int
    clock_diff_timeline: list[ClockDiffTimelinePoint] = []
    elo_timeline: list[EndgameEloTimelineCombo] = []
    elo_timeline_window: int
    type_categories: list[EndgameCategoryStats] = []


class EndgameRankedStatsResponse(BaseModel):
    """GET /api/endgames/ranked-stats.

    tcs lists only time controls with at least one ranked-sample game, ordered
    bullet, blitz, rapid, classical (D-14). An empty ranked sample returns [] (D-10).
    """

    tcs: list[RankedTcStats]
