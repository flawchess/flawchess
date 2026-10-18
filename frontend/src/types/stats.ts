export interface RatingDataPoint {
  date: string;
  rating: number;
  time_control_bucket: string;
  /** Games played that day in this time control (daily volume bars). */
  game_count: number;
}

export interface RatingHistoryResponse {
  chess_com: RatingDataPoint[];
  lichess: RatingDataPoint[];
}

export interface WDLByCategory {
  label: string;
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

export interface GlobalStatsResponse {
  by_time_control: WDLByCategory[];
  by_color: WDLByCategory[];
}

export interface OpeningWDL {
  opening_eco: string;
  opening_name: string;
  /** Canonical name with "vs. " prefix when the opening is defined by the off-color. */
  display_name: string;
  label: string;
  pgn: string;
  fen: string;
  full_hash: string;
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;

  // Score verdict inputs, computed server-side (D-18): (W + 0.5*D) / n, the Wilson
  // confidence bucket and p-value against 50%, and the 95% Wilson CI (D-33).
  score: number;
  score_confidence: 'low' | 'medium' | 'high';
  score_p_value: number;
  score_ci_low: number;
  score_ci_high: number;

  // MG-entry pillar.
  // avg_eval_pawns is signed user-perspective (positive = user better).
  // eval_n counts games used in the mean (mate-excluded, outlier-trimmed).
  // eval_p_value / eval_confidence test the mean against the colour baseline.
  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_n: number;
  eval_p_value?: number | null;
  eval_confidence: 'low' | 'medium' | 'high';
  // MAX(games.played_at) across the games visiting this opening's full_hash.
  // ISO 8601 string; null when contributing games all have NULL played_at.
  // Drives the "last played" line in the repertoire cards.
  last_played_at?: string | null;
  /** True when last_played_at is on or after the colour's current-repertoire cutoff (D-04). */
  is_current: boolean;
}

export interface MostPlayedOpeningsResponse {
  white: OpeningWDL[];
  black: OpeningWDL[];
  /** Engine-asymmetry baseline (in pawns) for white-color cells: the eval verdict
   * bar's centre and the H0 the per-row z-test uses. */
  eval_baseline_pawns_white: number;
  /** Engine-asymmetry baseline (in pawns) for black-color cells. */
  eval_baseline_pawns_black: number;
  /** Per-colour current-repertoire cutoff (ISO 8601); null when every opening counts as current. */
  current_cutoff_white: string | null;
  current_cutoff_black: string | null;
}

export interface BookmarkPhaseEntryQuery {
  target_hash: string;
  match_side: 'white' | 'black' | 'full';
  color: 'white' | 'black' | null;
}

export interface BookmarkPhaseEntryItem {
  target_hash: string;

  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_n: number;
  eval_p_value?: number | null;
  eval_confidence: 'low' | 'medium' | 'high';
}

export interface BookmarkPhaseEntryRequest {
  bookmarks: BookmarkPhaseEntryQuery[];
  time_control?: string[] | null;
  platform?: string[] | null;
  rated?: boolean | null;
  opponent_type?: string;
  opponent_gap_min?: number | null;
  opponent_gap_max?: number | null;
  from_date?: string | null;
  to_date?: string | null;
}

export interface BookmarkPhaseEntryResponse {
  items: BookmarkPhaseEntryItem[];
}
