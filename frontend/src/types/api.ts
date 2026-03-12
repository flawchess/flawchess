/**
 * TypeScript mirrors of the Pydantic v2 schemas from the backend.
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// ─── Analysis ────────────────────────────────────────────────────────────────

export type TimeControl = 'bullet' | 'blitz' | 'rapid' | 'classical';
export type MatchSide = 'white' | 'black' | 'full';
export type Recency = 'week' | 'month' | '3months' | '6months' | 'year' | 'all';
export type Color = 'white' | 'black';
export type UserResult = 'win' | 'draw' | 'loss';

export interface AnalysisRequest {
  /** Hash sent as string to avoid JS precision loss for large 64-bit integers */
  target_hash: string;
  match_side?: MatchSide;
  time_control?: TimeControl[] | null;
  rated?: boolean | null;
  recency?: Recency | null;
  color?: Color | null;
  offset?: number;
  limit?: number;
}

export interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

export interface GameRecord {
  game_id: number;
  opponent_username: string | null;
  user_result: UserResult;
  played_at: string | null;
  time_control_bucket: string | null;
  platform: string;
  platform_url: string | null;
}

export interface AnalysisResponse {
  stats: WDLStats;
  games: GameRecord[];
  matched_count: number;
  offset: number;
  limit: number;
}

// ─── Imports ─────────────────────────────────────────────────────────────────

export type Platform = 'chess.com' | 'lichess';

export interface ImportRequest {
  platform: Platform;
  username: string;
}

export interface ImportStartedResponse {
  job_id: string;
  status: string;
}

export type ImportJobStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface ImportStatusResponse {
  job_id: string;
  platform: string;
  username: string;
  status: ImportJobStatus;
  games_fetched: number;
  games_imported: number;
  /** Error message if status is 'error' */
  error: string | null;
}
