/**
 * TypeScript mirrors of the Pydantic v2 endgame schemas from the backend.
 */

import type { GameRecord } from './api';

export type EndgameClass = 'rook' | 'minor_piece' | 'pawn' | 'queen' | 'mixed' | 'pawnless';

export interface ConversionRecoveryStats {
  conversion_pct: number;    // win rate when up material (0-100)
  conversion_games: number;  // games where user entered up
  conversion_wins: number;
  conversion_draws: number;
  conversion_losses: number;
  recovery_pct: number;      // draw+win rate when down material (0-100)
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
  // Phase 60: opponent's score in the mirror bucket; null when opponent_games < 10
  opponent_score: number | null;
  // Phase 60: opponent's sample size (== swap-bucket game count)
  opponent_games: number;
}

/** Single point in the score-gap rolling-window time series.
 *  `date` is the Monday of an ISO week (YYYY-MM-DD).
 *  `score_difference` is endgame_score - non_endgame_score on a 0-1 scale (signed). */
export interface ScoreGapTimelinePoint {
  date: string;
  score_difference: number;
  endgame_game_count: number;
  non_endgame_game_count: number;
  // Count of games (endgame + non-endgame) played in THIS specific ISO week.
  // Drives the muted volume-bar series on the Score Gap timeline.
  per_week_total_games: number;
}

export interface ScoreGapMaterialResponse {
  endgame_score: number;
  non_endgame_score: number;
  score_difference: number;
  material_rows: MaterialRow[];
  timeline: ScoreGapTimelinePoint[];
  timeline_window: number;
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
  endgame_elo_timeline: EndgameEloTimelineResponse; // Phase 57
}

// ── Phase 57: Endgame ELO Timeline ─────────────────────────────────────────

/** Stable string-literal union of all 8 (platform, time_control) combo keys.
 *  Format: {platform_with_dot_replaced_by_underscore}_{time_control}.
 *  Frontend uses this as the lookup key into ELO_COMBO_COLORS.
 *  Backend populates via EndgameEloTimelineCombo.combo_key. */
export type EloComboKey =
  | 'chess_com_bullet'
  | 'chess_com_blitz'
  | 'chess_com_rapid'
  | 'chess_com_classical'
  | 'lichess_bullet'
  | 'lichess_blitz'
  | 'lichess_rapid'
  | 'lichess_classical';

/** One weekly point for a (platform, time_control) combo (Phase 57 ELO-05; revised Phase 57.1).
 *  date: Monday of ISO week, YYYY-MM-DD.
 *  endgame_elo: skill-adjusted rating = round(actual_elo + 400 * log10(skill / (1 - skill))).
 *  actual_elo: user's rating at this date via per-combo asof-join (forward-filled).
 *  endgame_games_in_window: trailing 100-game window count (drives >=10 floor + tooltip "past N games").
 *  per_week_endgame_games: count of endgame games for THIS specific ISO week (Phase 57.1, drives muted volume bars). */
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
