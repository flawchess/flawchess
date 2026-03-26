/**
 * TypeScript mirrors of the Pydantic v2 endgame schemas from the backend.
 */

import type { GameRecord } from './api';

export type EndgameClass = 'rook' | 'minor_piece' | 'pawn' | 'queen' | 'mixed' | 'pawnless';

export interface ConversionRecoveryStats {
  conversion_pct: number;    // win rate when up material (0-100)
  conversion_games: number;  // games where user entered up
  conversion_wins: number;
  recovery_pct: number;      // draw+win rate when down material (0-100)
  recovery_games: number;
  recovery_saves: number;
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
