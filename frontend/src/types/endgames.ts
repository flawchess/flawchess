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
  overall_win_rate: number;
  endgame_win_rate: number;
  aggregate_conversion_pct: number;
  aggregate_conversion_wins: number;
  aggregate_conversion_games: number;
  aggregate_recovery_pct: number;
  aggregate_recovery_saves: number;
  aggregate_recovery_games: number;
  relative_strength: number;
  endgame_skill: number;
}

export interface EndgameTimelinePoint {
  date: string;
  win_rate: number;
  game_count: number;
  window_size: number;
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

export interface ConvRecovTimelinePoint {
  date: string;
  rate: number; // 0.0-1.0 fraction
  game_count: number; // games in rolling window at this point
  window_size: number;
}

export interface ConvRecovTimelineResponse {
  conversion: ConvRecovTimelinePoint[];
  recovery: ConvRecovTimelinePoint[];
  window: number;
}

export type MaterialBucket = 'ahead' | 'equal' | 'behind';
export type Verdict = 'good' | 'ok' | 'bad';

export interface MaterialRow {
  bucket: MaterialBucket;
  label: string;
  games: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  score: number;
  verdict: Verdict;
}

export interface ScoreGapMaterialResponse {
  endgame_score: number;
  non_endgame_score: number;
  score_difference: number;
  overall_score: number;
  material_rows: MaterialRow[];
}

export interface EndgameOverviewResponse {
  stats: EndgameStatsResponse;
  performance: EndgamePerformanceResponse;
  timeline: EndgameTimelineResponse;
  conv_recov_timeline: ConvRecovTimelineResponse;
  score_gap_material: ScoreGapMaterialResponse;  // NEW — Phase 53
}
