/**
 * TypeScript mirrors of the Pydantic v2 endgame schemas from the backend.
 */

import type { GameRecord } from './api';

export type EndgameClass = 'rook' | 'minor_piece' | 'pawn' | 'queen' | 'mixed' | 'pawnless';

export interface ConversionRecoveryStats {
  conversion_pct: number;    // win rate when entering with eval >= +1.0 (0-100)
  conversion_games: number;  // games where user entered with eval >= +1.0
  conversion_wins: number;
  conversion_draws: number;
  conversion_losses: number;
  recovery_pct: number;      // draw+win rate when entering with eval <= -1.0 (0-100)
  recovery_games: number;
  recovery_saves: number;    // wins + draws (backward compat)
  recovery_wins: number;
  recovery_draws: number;
}

export interface EndgameCategoryStats {
  endgame_class: EndgameClass;
  label: string;             // "Rook", "Minor Piece", etc.
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  conversion: ConversionRecoveryStats;
  // Wilson score-test p-value of this class's WDL vs 50%.
  // null when total < PVALUE_RELIABILITY_MIN_N (=10). Wire field kept for
  // schema parity; TypeTable shows typical-range cells and does not render it.
  score_p_value: number | null;
  // Per-span mean Score Gap for this endgame type.
  // User-facing label: "Score Gap" (card row) / "Endgame Type Score Gap" (concepts).
  // Internal name retains "achievable".
  type_achievable_score_gap_mean: number | null;
  type_achievable_score_gap_n: number | null;
  type_achievable_score_gap_p_value: number | null;
  type_achievable_score_gap_ci_low: number | null;
  type_achievable_score_gap_ci_high: number | null;
  // TypeTable verdict gates (ranked payload only; false elsewhere).
  conversion_significant: boolean;
  recovery_significant: boolean;
  type_achievable_score_gap_significant: boolean;
  // Descriptive start/end components of the Score Gap.
  // end_mean - start_mean == gap_mean exactly (same span cohort, reconciliation invariant).
  // null when type_achievable_score_gap_n == 0.
  type_achievable_score_start_mean: number | null;
  type_achievable_score_end_mean: number | null;
  // WDLStats-aligned fields so PositionResultsPanel
  // can consume EndgameCategoryStats directly (mirrors WDLStats shape in api.ts).
  score: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;
  ci_low: number;
  ci_high: number;
  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_n: number;
  eval_p_value?: number | null;
  eval_confidence: 'low' | 'medium' | 'high';
  last_played_at?: string | null;
  eval_baseline_pawns: number;
}

export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];  // sorted by total desc; LLM path reads this
  total_games: number;       // Total games matching current filters
  endgame_games: number;     // Games that reached an endgame phase
}

export interface EndgameGamesResponse {
  games: GameRecord[];
  matched_count: number;
  offset: number;
  limit: number;
}

export interface EndgameWDLSummary {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

export type MaterialBucket = 'conversion' | 'parity' | 'recovery';

/** Single point in the score-gap rolling-window time series.
 *  `date` is the Monday of an ISO week (YYYY-MM-DD).
 *  `score_difference` is endgame_score - non_endgame_score on a 0-1 scale (signed).
 *  `endgame_score` / `non_endgame_score` are the absolute per-side
 *  rolling-window means (0-1). They let the two-line chart and the
 *  `score_timeline` insights subsection read absolute scores directly
 *  instead of reconstructing them from `score_difference`. */
export interface ScoreGapTimelinePoint {
  date: string;
  score_difference: number;
  endgame_game_count: number;
  non_endgame_game_count: number;
  // Count of games (endgame + non-endgame) played in THIS specific ISO week.
  // Drives the muted volume-bar series on the Score Gap timeline.
  per_week_total_games: number;
  // Count of ENDGAME games (only) played in THIS specific ISO week. Threaded
  // through to EndgameEloTimelinePoint.per_week_endgame_games so the Endgame
  // ELO Timeline volume bars show per-week endgame activity.
  per_week_endgame_games: number;
  // Absolute per-side rolling-window mean scores (0.0-1.0). Invariant:
  // abs((endgame_score - non_endgame_score) - score_difference) < 1e-9 per bucket.
  endgame_score: number;
  non_endgame_score: number;
  // Per-side trailing-window mean opponent rating. Drives the
  // Performance Rating math backend-side; not consumed by the score chart
  // but mirrored for schema parity with the Pydantic model.
  endgame_opp_rating_avg: number;
  non_endgame_opp_rating_avg: number;
}

// ── Time pressure ──
// Independent opp-quintile split: both sides derived from the user's own game stream.

/** Score-Delta data for one pressure quintile in a time control. */
export interface PressureQuintileBullet {
  quintile_index: number;       // 0 = 0-20% (max pressure) … 4 = 80-100% (min)
  quintile_label: string;       // "0-20%" … "80-100%"
  n: number;                    // user-side game count in this bin
  n_opp: number;                // opponent-side game count in the matching opp-clock quintile
  delta: number;                // user_score - opp_score (independent quintile splits per side)
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  opp_score: number | null;     // opponent's same-game score in the matching opp-clock quintile
  significant: boolean;         // 99% CI excludes 0: only then is the dot coloured
}

/** One ISO-week point on the Average Clock Difference over Time line chart.
 *  `avg_clock_diff_pct` is in PERCENT units
 *  (50.0 = 50%, not 0.5) — matches the chart Y-axis convention and the backend
 *  `(user_clock - opp_clock) / base_time_seconds * 100` calculation. */
export interface ClockDiffTimelinePoint {
  date: string;                  // ISO Monday YYYY-MM-DD
  avg_clock_diff_pct: number;    // rolling-window mean in percent units
  game_count: number;            // trailing rolling-window size (<= 100)
  per_week_game_count: number;   // clock-eligible games in THIS week only
}

/** Per-TC blended rating-anchor
 *  disclosure for the ranked-metric popover. The anchor is the game-weighted
 *  median of converted-chess.com + native-lichess ratings. The per-platform
 *  game-count and native-median fields support the four disclosure branches:
 *
 *    (a) Mixed user (n_chesscom_games > 0 AND n_lichess_games > 0):
 *        "Anchored at ~{anchor_rating} Elo, blending {n_chesscom_games}
 *         chess.com games (median {chesscom_median_native}, converted) with
 *         {n_lichess_games} lichess games (median {lichess_median_native})."
 *
 *    (b) Pure-lichess (n_chesscom_games == 0):
 *        "Anchored at ~{anchor_rating} Elo from {n_lichess_games} lichess
 *         games (native rating)."
 *
 *    (c) Pure-chess.com (n_lichess_games == 0):
 *        "Anchored at ~{anchor_rating} Elo from {n_chesscom_games} chess.com
 *         games (median {chesscom_median_native}, converted to
 *         Lichess-equivalent via ChessGoals snapshot 2026-05-26)."
 *
 *    (d) Suppression (both counts == 0): the caller omits the anchor line.
 *
 *  Fields:
 *  - `anchor_rating`: blended Lichess-equivalent (post-conversion for
 *    chess.com games; native for lichess games).
 *  - `n_chesscom_games`: chess.com games used in the anchor (0 for pure-lichess).
 *  - `n_lichess_games`: lichess games used in the anchor (0 for pure-chess.com).
 *  - `chesscom_median_native`: PRE-conversion chess.com median; null when
 *    n_chesscom_games == 0.
 *  - `lichess_median_native`: native lichess median; null when n_lichess_games == 0. */
export interface RatingAnchorOut {
  anchor_rating: number;
  n_chesscom_games: number;
  n_lichess_games: number;
  chesscom_median_native: number | null;
  lichess_median_native: number | null;
}

// ── Endgame ELO Timeline (rebuilt on Endgame Score Gap) ──

/** Stable string-literal union of all 8 (platform, time_control) combo keys.
 *  Format: {platform_with_dot_replaced_by_underscore}_{time_control}.
 *  Frontend uses this as the lookup key into ELO_COMBO_COLORS.
 *  Backend populates via EndgameEloTimelineCombo.combo_key.
 *
 *  Kept as EloComboKey rather than renaming — the combo_key
 *  encodes (platform, time_control) and carries no "endgame" semantic, so a
 *  rename would add churn without clarifying anything. */
export type EloComboKey =
  | 'chess_com_bullet'
  | 'chess_com_blitz'
  | 'chess_com_rapid'
  | 'chess_com_classical'
  | 'lichess_bullet'
  | 'lichess_blitz'
  | 'lichess_rapid'
  | 'lichess_classical';

/** Single weekly point for a (platform, time_control) combo of the Endgame ELO timeline.
 *  date: Monday of the ISO week, YYYY-MM-DD.
 *  endgame_elo: `actual_elo + spread / 2` where
 *    `spread = 400 · log10((s_E / (1 − s_E)) / (s_N / (1 − s_N)))` (logistic
 *    stretch anchored on Actual ELO).
 *  non_endgame_elo: `actual_elo − spread / 2`. Endgame ELO and Non-Endgame ELO
 *    sit symmetrically around Actual ELO by construction:
 *    `endgame_elo + non_endgame_elo == 2 · actual_elo` for every point.
 *  actual_elo: user's rating at this date via per-combo asof-join (forward-filled).
 *  endgame_games_in_window: trailing 100-game window count (drives ≥10 floor +
 *    tooltip "past N games").
 *  per_week_endgame_games: count of endgame games played in THIS specific ISO
 *    week (NOT the trailing window). Used by the insights service trend math.
 *  per_week_total_games: count of ALL games (endgame + non-endgame) played in
 *    THIS specific ISO week. Drives the muted volume-bar series on the
 *    Endgame ELO Timeline — the chart plots both Endgame ELO and Non-Endgame
 *    ELO, so the volume bar reflects total weekly activity feeding both PR
 *    lines (matches the Endgame Score Gap over Time chart's bars). */
export interface EndgameEloTimelinePoint {
  date: string;
  endgame_elo: number;
  non_endgame_elo: number;
  actual_elo: number;
  endgame_games_in_window: number;
  per_week_endgame_games: number;
  per_week_total_games: number;
}

export interface EndgameEloTimelineCombo {
  combo_key: EloComboKey;
  platform: 'chess.com' | 'lichess';
  time_control: 'bullet' | 'blitz' | 'rapid' | 'classical';
  points: EndgameEloTimelinePoint[];
}

export interface EndgameEloTimelineResponse {
  combos: EndgameEloTimelineCombo[];
  timeline_window: number;
}

// ── Ranked-sample payload (GET /api/endgames/ranked-stats) ──
// Mirrors app/schemas/endgames.py (EndgameRankedStatsResponse and friends). The
// payload takes no filters: every number describes the ranked sample
// (rated games vs human opponents within 100 Elo, last 36 months, <= 1000 games
// per time control), so a value and its percentile always describe the same games.

export type TimeControlBucket = 'bullet' | 'blitz' | 'rapid' | 'classical';

/** The 11 peer-ranked metric families (mirrors the backend CdfMetricId Literal). */
export type CdfMetricId =
  | 'score_gap'
  | 'achievable_score_gap'
  | 'score_gap_conv'
  | 'score_gap_parity'
  | 'recovery_score_gap'
  | 'time_pressure_score_gap'
  | 'clock_gap'
  | 'net_flag_rate'
  | 'conversion_rate'
  | 'parity_rate'
  | 'recovery_rate';

/** Rank status of one (metric, TC) cell:
 *  ranked      value plus a persisted percentile
 *  below_floor not enough games to rank yet (binding count vs floor_required)
 *  unranked    value computable but no persisted percentile row yet
 *  pending     entry evals missing, value not computable yet */
export type RankStatus = 'ranked' | 'below_floor' | 'unranked' | 'pending';

/** One peer-ranked metric for one time control. `value` is in fraction units
 *  (0.62 = 62%). `percentile` is set only when status === 'ranked'. */
export interface RankedMetricOut {
  metric: CdfMetricId;
  value: number | null;
  n: number;
  floor_n: number;
  floor_required: number;
  percentile: number | null;
  status: RankStatus;
  ci_low: number | null;        // 99% CI
  ci_high: number | null;
  p_value: number | null;
  /** 99% CI excludes the null on the verdict's side; red/green needs it. */
  significant: boolean;
}

export interface RankedBucketOut {
  bucket: MaterialBucket;
  games: number;
  wins: number;
  draws: number;
  losses: number;
}

export interface RankedEntryFlowOut {
  entry_eval_mean_pawns: number | null;
  entry_eval_n: number;
  expected_score: number | null;
  actual_score: number | null;
  n: number;
}

export interface RankedOverallOut {
  endgame_wdl: EndgameWDLSummary;
  non_endgame_wdl: EndgameWDLSummary;
  entry_flow: RankedEntryFlowOut;
}

export interface RankedTimePressureOut {
  quintiles: PressureQuintileBullet[];
}

export interface RankedTcStats {
  tc: TimeControlBucket;
  ranked_games: number;
  anchor_games: number;
  anchor_min_games: number;
  anchor: RatingAnchorOut | null;
  eval_pending_games: number;
  metrics: Record<CdfMetricId, RankedMetricOut>;
  overall: RankedOverallOut;
  buckets: RankedBucketOut[];
  time_pressure: RankedTimePressureOut;
  score_gap_timeline: ScoreGapTimelinePoint[];
  score_gap_timeline_window: number;
  clock_diff_timeline: ClockDiffTimelinePoint[];
  elo_timeline: EndgameEloTimelineCombo[];
  elo_timeline_window: number;
  type_categories: EndgameCategoryStats[];
}

/** `tcs` lists only time controls with at least one ranked-sample game, ordered
 *  bullet, blitz, rapid, classical. An empty ranked sample returns []. */
export interface EndgameRankedStatsResponse {
  tcs: RankedTcStats[];
}
