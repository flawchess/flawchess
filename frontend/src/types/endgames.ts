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
  // quick-260519-ni3: descriptive start/end components of the Score Gap.
  // end_mean - start_mean == gap_mean exactly (same span cohort, reconciliation invariant).
  // null when type_achievable_score_gap_n == 0.
  type_achievable_score_start_mean: number | null;
  type_achievable_score_end_mean: number | null;
  // Quick task 260519-lu0: WDLStats-aligned fields so PositionResultsPanel
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
  // Phase 98: per-(class × TC) rates for the collapsible endgame type cards.
  // Optional for back-compat with older server responses (Pitfall 6).
  // D-15: the LLM insights path reads `categories` (pooled) and never touches this field.
  categories_by_tc?: Record<
    'bullet' | 'blitz' | 'rapid' | 'classical',
    EndgameCategoryStats[]
  >;
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
  /** Phase 94 (PCTL-02): cohort percentile [0,100] for Achievable Score Gap vs the Phase 93 global CDF.
   *  null when the endgame-entry span count is below PVALUE_RELIABILITY_MIN_N (=10). */
  achievable_score_gap_percentile: number | null;
  /** Quick task 260527-q0b: per-TC breakdown for the chip tooltip bullet 2.
   *  Backend defaults to [] so the field is always serialised. */
  achievable_score_gap_per_tc: PerTcBreakdownOut[];
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
  // Phase 87.6: per-side trailing-window mean opponent rating. Drives the
  // Performance Rating math backend-side; not consumed by the score chart
  // but mirrored for schema parity with the Pydantic model.
  endgame_opp_rating_avg: number;
  non_endgame_opp_rating_avg: number;
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
  /** Phase 94 (PCTL-02): cohort percentile [0,100] for Endgame Score Gap vs the Phase 93 global CDF.
   *  Name mirrors the MetricId (`score_gap`), not the wire sibling `score_difference` (D-11).
   *  null when min(endgame_wdl.total, non_endgame_wdl.total) < PVALUE_RELIABILITY_MIN_N (=10). */
  score_gap_percentile: number | null;
  /** Quick task 260527-q0b: per-TC breakdown for the chip tooltip bullet 2. */
  score_gap_per_tc: PerTcBreakdownOut[];
  // Phase 87.2 (D-06): 20 eval-baseline Delta-ES Score Gap fields (4 buckets x 5).
  // Replaces the rate-based mirror-bucket peer-bullet (skill, opp_skill, skill_diff_*
  // deleted per D-04). Each cluster: mean per-span Score Gap, sample count,
  // one-sample paired z-test p_value, and 95% CI bounds.
  // All fields are null when the cohort is empty (n=0) or below the reliability gate.
  // Mirrors app/schemas/endgames.py ScoreGapMaterialResponse (Phase 87.2 D-06).
  // Dual-label rationale: "conv/parity/recov" in field names vs "conversion/parity/recovery"
  // in user-facing labels — the abbreviated form is shorter and consistent with backend.

  // Conversion bucket (entered endgame with eval >= +1.0):
  score_gap_conv_mean: number | null;
  score_gap_conv_n: number | null;
  score_gap_conv_p_value: number | null;
  score_gap_conv_ci_low: number | null;
  score_gap_conv_ci_high: number | null;
  // Parity bucket (entered endgame with eval between -1.0 and +1.0):
  score_gap_parity_mean: number | null;
  score_gap_parity_n: number | null;
  score_gap_parity_p_value: number | null;
  score_gap_parity_ci_low: number | null;
  score_gap_parity_ci_high: number | null;

  // Recovery bucket (entered endgame with eval <= -1.0):
  score_gap_recov_mean: number | null;
  score_gap_recov_n: number | null;
  score_gap_recov_p_value: number | null;
  score_gap_recov_ci_low: number | null;
  score_gap_recov_ci_high: number | null;

  // Phase 97 D-10: score_gap_conv_percentile, score_gap_parity_percentile,
  // recovery_score_gap_percentile, score_gap_conv_per_tc, score_gap_parity_per_tc,
  // and recovery_score_gap_per_tc removed — Metrics-section-only fields deleted
  // with EndgameMetricsSection.tsx (superseded by per-TC cards).

  // Phase 87.4 (D-05): the 6 Skill fields (score_gap_skill_* and
  // endgame_skill_rate_mean) were hard-deleted alongside EndgameSkillCard.
  // No composite definition survived scrutiny on all four axes; see
  // .planning/notes/endgame-skill-dropped-conversion-elo.md.
}

// ── Phase 88: Time Pressure Cards (replaces ClockPressureResponse + TimePressureChartResponse) ──
// Phase 88.1 (D-07): independent opp-quintile split — both sides derived from the user's
// own filtered game stream. See .planning/.../88-CONTEXT.md D-07 for design rationale.

/** Score-Delta bullet data for one pressure quintile in a TC card. */
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
}

/** Clock Gap bullet data for one TC card (mean of (my-opp)/base at endgame entry). */
export interface ClockGapBullet {
  n: number;
  mean_diff_pct: number;        // mean (user_clock - opp_clock) / base_clock
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

/** All bullet data for one time-control card.
 *
 * Plan 88-14 A-3: restored top-zone summary stats from the deleted
 * EndgameClockPressureSection (CONTEXT §2 scope amendment). The 5 averages are
 * fractions / absolute seconds depending on the suffix; net_timeout_rate is a
 * fraction (0.005 = 0.5%) consistent with clock_gap.mean_diff_pct's convention.
 * Averages are null when no game in this TC has clock data (legacy imports).
 *
 * Phase 94.3 (CONTEXT.md D-1): three per-(metric × TC) chip percentile fields
 * for the per-TC chip slots. null when the user is below the pooled >=30
 * inclusion floor for that metric × TC combo, when Stage B has not yet computed
 * (race window after import + cold-drain), or when the field is not yet
 * populated by the backend (back-compat default). Frontend gates chip rendering
 * on `!= null`.
 */
export interface TimePressureTcCard {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  total: number;                    // total endgame games in this TC
  user_avg_pct: number | null;      // mean user_clock/base across clock-eligible games, fraction
  user_avg_seconds: number | null;  // mean user_clock in absolute seconds
  opp_avg_pct: number | null;       // mean opp_clock/base, fraction
  opp_avg_seconds: number | null;   // mean opp_clock in absolute seconds
  avg_clock_diff_seconds: number | null; // mean (user_clock - opp_clock) in seconds
  net_timeout_rate: number;         // (timeout_wins - timeout_losses) / total, fraction (0.005 = 0.5%)
  clock_gap: ClockGapBullet;
  quintiles: PressureQuintileBullet[]; // always 5, ordered Q0..Q4
  // Phase 94.3: per-(metric × TC) percentile annotations (optional for
  // back-compat — older fixtures and pre-94.3 server responses don't set these).
  time_pressure_score_gap_percentile?: number | null;
  clock_gap_percentile?: number | null;
  net_flag_rate_percentile?: number | null;
  // Quick task 260527-q0b: per-TC chip tooltip bullet 2 simplified framing —
  // chip-cohort (n_games, value) from the PercentileRow. Optional for
  // back-compat with older fixtures that build TimePressureTcCard without these.
  time_pressure_score_gap_n_games?: number | null;
  time_pressure_score_gap_value?: number | null;
  clock_gap_n_games?: number | null;
  clock_gap_value?: number | null;
  net_flag_rate_n_games?: number | null;
  net_flag_rate_value?: number | null;
}

/** Replaces ClockPressureResponse + TimePressureChartResponse (Phase 88). */
export interface TimePressureCardsResponse {
  cards: TimePressureTcCard[];  // only TCs with total >= MIN_GAMES_PER_TC_CARD
}

/** One ISO-week point on the Average Clock Difference over Time line chart.
 *  Plan 88-15 (CONTEXT §2 A-2): restored after the Phase 88-07 cleanup deleted
 *  the line chart. Renamed (vs the pre-88-07 timeline point class) to make the
 *  design-pivot history obvious. `avg_clock_diff_pct` is in PERCENT units
 *  (50.0 = 50%, not 0.5) — matches the chart Y-axis convention and the backend
 *  `(user_clock - opp_clock) / base_time_seconds * 100` calculation. */
export interface ClockDiffTimelinePoint {
  date: string;                  // ISO Monday YYYY-MM-DD
  avg_clock_diff_pct: number;    // rolling-window mean in percent units
  game_count: number;            // trailing rolling-window size (<= 100)
  per_week_game_count: number;   // clock-eligible games in THIS week only
}

/** Wrapper for the Average Clock Difference over Time line chart payload.
 *  Plan 88-15 (CONTEXT §2 A-2). points is empty when no clock-eligible game
 *  exists in the user's filtered set — frontend hides the chart in that case. */
export interface ClockDiffTimelineResponse {
  points: ClockDiffTimelinePoint[];
}

/** D-12 Reversal Amendment (CONTEXT 2026-05-27) — per-TC blended rating-anchor
 *  disclosure for the percentile chip tooltip. The anchor is the game-weighted
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
 *    (d) Suppression (both counts == 0): chip suppresses at the caller.
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

/** Quick task 260527-q0b: mirrors backend PerTcBreakdownOut.
 *  One per-TC entry for the PercentileChip tooltip bullet 2 (aggregated chips).
 *
 *  Branch semantics on render:
 *    - value != null && percentile != null: above floor with percentile →
 *      render `<tc>: <value> over <n_games> games -> <percentile> percentile`.
 *    - value != null && percentile == null: above floor but CDF out-of-range →
 *      DROP the line entirely (backend stays honest about wire shape).
 *    - value == null && n_games > 0: below floor → render `<tc>: insufficient games`.
 *    - n_games == 0: backend should not emit; defensive frontend drop.
 *
 *  260529-l1i: each renderable row also shows a per-TC rating-anchor line
 *  ("<tc> — anchored at ~<anchor> Lichess Elo"). `anchor` is null when this TC
 *  has no anchor; the anchor line is then omitted for that row.
 *
 *  TCs ordered bullet → blitz → rapid → classical by the backend builder. */
export interface PerTcBreakdownOut {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  value: number | null;
  n_games: number;
  percentile: number | null;
  anchor: number | null;
}

// ── Phase 97: Per-TC Endgame Metrics Cards ──────────────────────────────────

/** Stats for one material bucket (conversion / parity / recovery) within one TC.
 *  Mirrors backend PerTcBucketStats (Plan 97-02). */
export interface PerTcBucketStats {
  games: number;
  win_pct: number;    // percent 0-100
  draw_pct: number;
  loss_pct: number;
  rate: number | null;             // conversion win%, parity score%, recovery save%
  score_gap_mean: number | null;
  score_gap_n: number | null;
  score_gap_p_value: number | null;
  score_gap_ci_low: number | null;
  score_gap_ci_high: number | null;
  percentile: number | null;       // per-TC DeltaES-gap percentile
  // Chip-cohort n_games + value from the same PercentileRow as `percentile`.
  // Feed the chip tooltip's "Based on {n} of your recent {tc} games … Your
  // value: {v}" line (mirrors TimePressureTcCard). Optional for older fixtures.
  percentile_n_games?: number | null;
  percentile_value?: number | null;
}

/** One TC card in the per-TC Endgame Metrics section.
 *  Mirrors backend EndgameMetricsTcCard (Plan 97-02). */
export interface EndgameMetricsTcCard {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  total: number;
  conversion: PerTcBucketStats;
  parity: PerTcBucketStats;
  recovery: PerTcBucketStats;
}

/** Response wrapper for the per-TC endgame metrics cards.
 *  Mirrors backend EndgameMetricsCardsResponse (Plan 97-02). */
export interface EndgameMetricsCardsResponse {
  cards: EndgameMetricsTcCard[];
}

export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;  // Phase 53
  time_pressure_cards: TimePressureCardsResponse; // Phase 88 (replaces clock_pressure + time_pressure_chart)
  clock_diff_timeline: ClockDiffTimelineResponse; // Plan 88-15 (CONTEXT §2 A-2): restored line chart payload
  endgame_elo_timeline: EndgameEloTimelineResponse; // Phase 57 (rebuilt Phase 87.5)
  /** Phase 94.4 D-07 bullet 4: top-level rating-anchor disclosure block.
   *  Keyed by time control. Missing-TC keys are absent (Partial<Record>);
   *  Plan 07's tooltip picks the dominant TC's anchor. Missing keys mean
   *  the user is below the inclusion floor for that TC or (for chess.com
   *  sources) the conversion returned null. */
  rating_anchors: Partial<Record<'bullet' | 'blitz' | 'rapid' | 'classical', RatingAnchorOut>>;
  /** Phase 97: per-TC endgame metrics cards (conversion / parity / recovery per TC).
   *  Optional for back-compat with older fixtures and pre-97 server responses. */
  endgame_metrics_cards?: EndgameMetricsCardsResponse;
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

/** Single weekly point for a (platform, time_control) combo of the Endgame ELO timeline.
 *  date: Monday of the ISO week, YYYY-MM-DD.
 *  endgame_elo: `actual_elo + spread / 2` where
 *    `spread = 400 · log10((s_E / (1 − s_E)) / (s_N / (1 − s_N)))` (Phase 87.6
 *    amendment 2026-05-17 — logistic stretch anchored on Actual ELO,
 *    supersedes the earlier per-side FIDE PR mapping).
 *  non_endgame_elo: `actual_elo − spread / 2`. Endgame ELO and Non-Endgame ELO
 *    sit symmetrically around Actual ELO by construction:
 *    `endgame_elo + non_endgame_elo == 2 · actual_elo` for every point.
 *    See .planning/notes/endgame-elo-logistic-anchored.md.
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
