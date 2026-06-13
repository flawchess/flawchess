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
  // Optional global filters (D-19 amendment 2026-06-13: date bounds now accepted;
  // the time-series path date-filters emitted points + WDL totals while warming
  // the rolling average from pre-window games)
  time_control?: ('bullet' | 'blitz' | 'rapid' | 'classical')[] | null;
  platform?: ('chess.com' | 'lichess')[] | null;
  rated?: boolean | null;
  opponent_type?: 'human' | 'bot' | 'both';
  opponent_gap_min?: number;
  opponent_gap_max?: number;
  // Resolved date bounds for windowed emission (ISO YYYY-MM-DD strings)
  from_date?: string;
  to_date?: string;
}

export interface TimeSeriesPoint {
  date: string;          // "2025-01-15"
  score: number;         // chess score (W + 0.5·D) / N, 0.0 - 1.0
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
  // ISO 8601 (or null when no qualifying games). MAX(played_at) across all
  // matching games — drives the bookmark card "Last played: <relative>" line.
  last_played_at?: string | null;
}

export interface TimeSeriesResponse {
  series: BookmarkTimeSeries[];
}
