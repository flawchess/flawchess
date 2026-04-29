import type { MatchSide } from './api';

export interface PositionBookmarkResponse {
  id: number;
  label: string;
  target_hash: string;   // string from backend (avoids JS precision loss)
  fen: string;
  moves: string[];
  color: 'white' | 'black' | null;
  match_side: MatchSide;
  is_flipped: boolean;
  sort_order: number;
}

export interface PositionBookmarkCreate {
  label: string;
  target_hash: string;   // send as string — backend coerces to int
  fen: string;
  moves: string[];
  color: 'white' | 'black' | null;
  match_side: 'mine' | 'opponent' | 'both';
  is_flipped: boolean;
}

export interface PositionBookmarkUpdate {
  label?: string;
  sort_order?: number;
}

export interface PositionBookmarkReorderRequest {
  ids: number[];
}

export interface MatchSideUpdateRequest {
  match_side: 'mine' | 'opponent' | 'both';
}

export interface TimeSeriesBookmarkParam {
  bookmark_id: number;
  target_hash: string;
  match_side: 'white' | 'black' | 'full'; // backend API format (resolved before sending)
  color: 'white' | 'black' | null;
}

export interface TimeSeriesRequest {
  bookmarks: TimeSeriesBookmarkParam[];
  // Optional global filters
  time_control?: ('bullet' | 'blitz' | 'rapid' | 'classical')[] | null;
  platform?: ('chess.com' | 'lichess')[] | null;
  rated?: boolean | null;
  opponent_type?: 'human' | 'bot' | 'both';
  recency?: 'week' | 'month' | '3months' | '6months' | 'year' | '3years' | '5years' | 'all' | null;
  opponent_gap_min?: number;
  opponent_gap_max?: number;
}

export interface TimeSeriesPoint {
  date: string;          // "2025-01-15"
  win_rate: number;      // 0.0 - 1.0
  game_count: number;    // games in rolling window (1..window_size)
  window_size: number;   // configured window size (ROLLING_WINDOW_SIZE)
}

export interface BookmarkTimeSeries {
  bookmark_id: number;
  data: TimeSeriesPoint[];
  total_wins: number;
  total_draws: number;
  total_losses: number;
  total_games: number;
}

export interface TimeSeriesResponse {
  series: BookmarkTimeSeries[];
}
