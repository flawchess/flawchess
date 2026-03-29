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
}

export interface MostPlayedOpeningsResponse {
  white: OpeningWDL[];
  black: OpeningWDL[];
}
