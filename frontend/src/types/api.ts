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
/** Frontend representation: mine/opponent/both (relative to the user's color) */
export type MatchSide = 'mine' | 'opponent' | 'both';
/** Backend API representation: white/black/full */
export type ApiMatchSide = 'white' | 'black' | 'full';
export type Recency = 'week' | 'month' | '3months' | '6months' | 'year' | 'all';
export type Color = 'white' | 'black';
export type OpponentType = 'human' | 'bot' | 'both';
export type UserResult = 'win' | 'draw' | 'loss';

/** Resolves mine/opponent/both + color to the API's white/black/full value */
export function resolveMatchSide(matchSide: MatchSide, color: Color): ApiMatchSide {
  if (matchSide === 'both') return 'full';
  if (matchSide === 'mine') return color; // mine when white = 'white', mine when black = 'black'
  // opponent
  return color === 'white' ? 'black' : 'white';
}


export interface AnalysisRequest {
  /** Hash sent as string to avoid JS precision loss. Optional -- omit to get all games. */
  target_hash?: string;
  match_side?: ApiMatchSide;
  time_control?: TimeControl[] | null;
  platform?: Platform[] | null;
  rated?: boolean | null;
  opponent_type?: OpponentType;
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
  user_result: UserResult;
  played_at: string | null;
  time_control_bucket: string | null;
  platform: string;
  platform_url: string | null;
  opening_name: string | null;
  opening_eco: string | null;
  user_color: string;
  move_count: number | null;
  white_username: string | null;
  black_username: string | null;
  white_rating: number | null;
  black_rating: number | null;
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
