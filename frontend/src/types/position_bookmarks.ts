export interface PositionBookmarkResponse {
  id: number;
  label: string;
  target_hash: string;   // string from backend (avoids JS precision loss)
  fen: string;
  moves: string[];
  color: 'white' | 'black' | null;
  match_side: 'mine' | 'opponent' | 'both' | 'white' | 'black' | 'full'; // new values + legacy values for backward compat
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
  recency?: 'week' | 'month' | '3months' | '6months' | 'year' | 'all' | null;
}

export interface TimeSeriesPoint {
  month: string;       // "2025-01"
  win_rate: number;    // 0.0 - 1.0
  game_count: number;
  wins: number;
  draws: number;
  losses: number;
}

export interface BookmarkTimeSeries {
  bookmark_id: number;
  data: TimeSeriesPoint[];
}

export interface TimeSeriesResponse {
  series: BookmarkTimeSeries[];
}
