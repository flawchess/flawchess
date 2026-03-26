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
  aggregate_recovery_pct: number;
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
