export interface RatingDataPoint {
  date: string;
  rating: number;
  time_control_bucket: string;
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
  /** Canonical name with "vs. " prefix when the opening is defined by the off-color (PRE-01). */
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

  // Phase 80 MG-entry pillar (D-01, D-04, D-08).
  // avg_eval_pawns is signed user-perspective (positive = user better).
  // eval_n counts games used in the mean (mate-excluded, outlier-trimmed).
  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_n: number;
  eval_p_value?: number | null;
  eval_confidence: 'low' | 'medium' | 'high';
}

export interface MostPlayedOpeningsResponse {
  white: OpeningWDL[];
  black: OpeningWDL[];
  /** Engine-asymmetry baseline (in pawns) for white-color cells, used to
   * center the bullet chart on the same H0 the per-row z-test uses. */
  eval_baseline_pawns_white: number;
  /** Engine-asymmetry baseline (in pawns) for black-color cells. */
  eval_baseline_pawns_black: number;
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
  recency?: string | null;
}

export interface BookmarkPhaseEntryResponse {
  items: BookmarkPhaseEntryItem[];
}
