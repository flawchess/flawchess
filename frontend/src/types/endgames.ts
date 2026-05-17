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
  // Phase 87 follow-up: Wilson score-test p-value of this class's WDL vs 50%.
  // null when total < PVALUE_RELIABILITY_MIN_N (=10). Drives the per-card
  // Score bullet sig-gating triple in EndgameTypeCard.
  score_p_value: number | null;
  // Phase 87.1 (SEED-016, D-05): per-span mean Score Gap for this endgame type.
  // User-facing label: "Score Gap" (card row) / "Endgame Type Score Gap" (concepts).
  // Internal name retains "achievable" to preserve grep-ability with Phase 85.1.
  type_achievable_score_gap_mean: number | null;
  type_achievable_score_gap_n: number | null;
  type_achievable_score_gap_p_value: number | null;
  type_achievable_score_gap_ci_low: number | null;
  type_achievable_score_gap_ci_high: number | null;
}

export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];  // sorted by total desc
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

export interface EndgamePerformanceResponse {
  endgame_wdl: EndgameWDLSummary;
  non_endgame_wdl: EndgameWDLSummary;
  endgame_win_rate: number;
  // Phase 81 (D-11): entry-eval aggregation for "Endgame Start vs End" section.
  entry_eval_mean_pawns: number;
  entry_eval_n: number;
  entry_eval_p_value: number | null;
  endgame_score_p_value: number | null;
  non_endgame_score_p_value: number | null;
  entry_eval_ci_low_pawns: number | null;
  entry_eval_ci_high_pawns: number | null;
  // Phase 83 (D-21): Stockfish-baseline achievable score for "Where you start" tile.
  // Mate INCLUDED in cohort; NULL evals excluded; |eval_cp| < 2000 clip applied.
  entry_expected_score: number;
  entry_expected_score_n: number;
  entry_expected_score_p_value: number | null;
  entry_expected_score_ci_low: number | null;
  entry_expected_score_ci_high: number | null;
  // Phase 85.1 (SEC1-10): server-side achievable score gap + paired z-test.
  // Always-present scalar (0.0 when n=0); p / CI gated to null when n is below
  // the reliability gate (PVALUE_RELIABILITY_MIN_N=10 for p, 2 for CI).
  achievable_score_gap: number;
  achievable_score_gap_p_value: number | null;
  achievable_score_gap_ci_low: number | null;
  achievable_score_gap_ci_high: number | null;
}

/** Single data point in the per-type weekly win-rate time series.
 *  `date` is the Monday of an ISO week (YYYY-MM-DD). `win_rate` is wins / games
 *  in that week. Only weeks with at least 3 games are emitted. */
export interface EndgameTimelinePoint {
  date: string;
  win_rate: number;
  game_count: number;
  // Count of games for THIS specific ISO week (NOT the trailing window).
  // Drives the muted volume-bar series on the Win Rate by Endgame Type chart.
  per_week_game_count: number;
}

export interface EndgameOverallPoint {
  date: string;
  endgame_win_rate: number | null;
  non_endgame_win_rate: number | null;
  endgame_game_count: number;
  non_endgame_game_count: number;
  window_size: number;
}

export interface EndgameTimelineResponse {
  overall: EndgameOverallPoint[];
  per_type: Record<string, EndgameTimelinePoint[]>;
  window: number;
}

export type MaterialBucket = 'conversion' | 'parity' | 'recovery';

export interface MaterialRow {
  bucket: MaterialBucket;
  label: string;
  games: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  score: number;
  // Phase 87.2 (D-05): opponent_score, opponent_games, diff_p_value, diff_ci_low,
  // diff_ci_high deleted. The mirror-bucket Wald-z peer-bullet was mathematically
  // degenerate (Conv-Gap == Recov-Gap by symmetry; Parity-Gap affine of gauge).
  // Replaced by the eval-baseline Delta-ES Score Gap fields on ScoreGapMaterialResponse.
}

/** Single point in the score-gap rolling-window time series.
 *  `date` is the Monday of an ISO week (YYYY-MM-DD).
 *  `score_difference` is endgame_score - non_endgame_score on a 0-1 scale (signed).
 *  `endgame_score` / `non_endgame_score` are the absolute per-side
 *  rolling-window means (0-1). Phase 68 added them so the two-line chart
 *  and the `score_timeline` insights subsection read absolute scores
 *  directly instead of reconstructing them from `score_difference`. */
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
  // Phase 68: absolute per-side rolling-window mean scores (0.0-1.0). Invariant:
  // abs((endgame_score - non_endgame_score) - score_difference) < 1e-9 per bucket.
  endgame_score: number;
  non_endgame_score: number;
}

export interface ScoreGapMaterialResponse {
  endgame_score: number;
  non_endgame_score: number;
  score_difference: number;
  material_rows: MaterialRow[];
  timeline: ScoreGapTimelinePoint[];
  timeline_window: number;
  // Phase 85.1 (SEC1-08, SEC1-09): independent two-sample z-test on
  // (endgame_score - non_endgame_score). p_value is gated to null when
  // min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N
  // (=10); CI bounds are gated when min n < 2.
  score_difference_p_value: number | null;
  score_difference_ci_low: number | null;
  score_difference_ci_high: number | null;
  // Phase 87.2 (D-06): 20 eval-baseline Delta-ES Score Gap fields (4 buckets x 5).
  // Replaces the rate-based mirror-bucket peer-bullet (skill, opp_skill, skill_diff_*
  // deleted per D-04). Each cluster: mean per-span Score Gap, sample count,
  // one-sample paired z-test p_value, and 95% CI bounds.
  // All fields are null when the cohort is empty (n=0) or below the reliability gate.
  // Mirrors app/schemas/endgames.py ScoreGapMaterialResponse (Phase 87.2 D-06).
  // Dual-label rationale: "conv/parity/recov" in field names vs "conversion/parity/recovery"
  // in user-facing labels — the abbreviated form is shorter and consistent with backend.

  // Conversion bucket (entered endgame with eval >= +1.0):
  section2_score_gap_conv_mean: number | null;
  section2_score_gap_conv_n: number | null;
  section2_score_gap_conv_p_value: number | null;
  section2_score_gap_conv_ci_low: number | null;
  section2_score_gap_conv_ci_high: number | null;

  // Parity bucket (entered endgame with eval between -1.0 and +1.0):
  section2_score_gap_parity_mean: number | null;
  section2_score_gap_parity_n: number | null;
  section2_score_gap_parity_p_value: number | null;
  section2_score_gap_parity_ci_low: number | null;
  section2_score_gap_parity_ci_high: number | null;

  // Recovery bucket (entered endgame with eval <= -1.0):
  section2_score_gap_recov_mean: number | null;
  section2_score_gap_recov_n: number | null;
  section2_score_gap_recov_p_value: number | null;
  section2_score_gap_recov_ci_low: number | null;
  section2_score_gap_recov_ci_high: number | null;

  // Phase 87.4 (D-05): the 6 Skill fields (section2_score_gap_skill_* and
  // endgame_skill_rate_mean) were hard-deleted alongside EndgameSkillCard.
  // No composite definition survived scrutiny on all four axes; see
  // .planning/notes/endgame-skill-dropped-conversion-elo.md.
}

export interface ClockStatsRow {
  time_control: string;       // "bullet" | "blitz" | "rapid" | "classical"
  label: string;              // "Bullet" | "Blitz" | "Rapid" | "Classical"
  total_endgame_games: number;
  clock_games: number;
  user_avg_pct: number | null;
  user_avg_seconds: number | null;
  opp_avg_pct: number | null;
  opp_avg_seconds: number | null;
  avg_clock_diff_seconds: number | null;
  net_timeout_rate: number;
}

export interface ClockPressureTimelinePoint {
  date: string;                 // Monday of ISO week, YYYY-MM-DD
  avg_clock_diff_pct: number;   // mean (user_clock - opp_clock) / base_time * 100 over trailing window
  game_count: number;           // games in the rolling window (<= timeline_window)
  // Count of clock-eligible endgame games in THIS specific ISO week.
  // Drives the muted volume-bar series on the Average Clock Difference timeline.
  per_week_game_count: number;
}

export interface ClockPressureResponse {
  rows: ClockStatsRow[];
  total_clock_games: number;
  total_endgame_games: number;
  timeline: ClockPressureTimelinePoint[];
  timeline_window: number;
}

export interface TimePressureBucketPoint {
  bucket_index: number;      // 0-9
  bucket_label: string;      // "0-10%" etc.
  score: number | null;      // null when game_count == 0
  game_count: number;
}

export interface TimePressureChartResponse {
  user_series: TimePressureBucketPoint[];  // 10 points, pre-aggregated across time controls
  opp_series: TimePressureBucketPoint[];   // 10 points, pre-aggregated across time controls
  total_endgame_games: number;
}

export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;  // Phase 53
  clock_pressure: ClockPressureResponse;         // Phase 54
  time_pressure_chart: TimePressureChartResponse; // Phase 55
  endgame_elo_timeline: EndgameEloTimelineResponse; // Phase 57 (rebuilt Phase 87.5)
}

// ── Phase 87.5: Endgame ELO Timeline (rebuilt on Endgame Score Gap) ──

/** Stable string-literal union of all 8 (platform, time_control) combo keys.
 *  Format: {platform_with_dot_replaced_by_underscore}_{time_control}.
 *  Frontend uses this as the lookup key into ELO_COMBO_COLORS.
 *  Backend populates via EndgameEloTimelineCombo.combo_key.
 *
 *  Phase 87.4 D-06: kept as EloComboKey rather than renaming — the combo_key
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

/** One weekly point for a (platform, time_control) combo.
 *  Phase 87.5 D-01: rebuilt on the additive Endgame Score Gap mapping.
 *  date: Sunday of ISO week (end of week), YYYY-MM-DD. Aligned with the asof
 *    rating moment so a daily rating chart at the same date shows the same value.
 *  endgame_elo: round(actual_elo + K · eg_score_gap), where eg_score_gap is the
 *    trailing-window Endgame Score minus Non-Endgame Score for this combo. At
 *    eg_score_gap = 0 the rendered Endgame ELO equals actual_elo exactly.
 *    K is a single global constant (locked at 450 in app/services/endgame_service.py).
 *    Positive Endgame Score Gap lifts the rating; negative holds it back.
 *  actual_elo: user's rating at this date via per-combo asof-join (forward-filled).
 *  endgame_games_in_window: trailing 100-game window count (drives ≥10 floor + tooltip "past N games").
 *  per_week_endgame_games: count of endgame games played in THIS specific ISO week
 *    (NOT the trailing window). Drives the muted volume-bar series on the Endgame
 *    ELO Timeline so the bars reflect per-week activity. Restored to per-week
 *    semantics in the UAT fix that followed Phase 87.5 CR-01. */
export interface EndgameEloTimelinePoint {
  date: string;
  endgame_elo: number;
  actual_elo: number;
  endgame_games_in_window: number;
  per_week_endgame_games: number;
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
