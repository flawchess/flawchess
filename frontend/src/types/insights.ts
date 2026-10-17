import type { AxiosError } from 'axios';

/**
 * Response envelope types. Consumed by useEndgameInsights hook
 * and EndgameInsightsBlock component. Literal unions mirror
 * app/schemas/insights.py exactly — any divergence breaks the contract.
 */

export type SectionId =
  | 'overall'
  | 'metrics_elo'
  | 'time_pressure'
  | 'type_breakdown';

export type InsightsStatus =
  | 'fresh'
  | 'cache_hit';

export type InsightsError =
  | 'provider_error'
  | 'validation_failure'
  | 'config_error';

export interface SectionInsight {
  section_id: SectionId;
  headline: string;    // <= 120 chars (~12 words)
  bullets: string[];   // 0..2 items, each <= 200 chars (~20 words)
}

/** Pending / error view of the Generate mutation, shared across the Stats tab's two mounts. */
export interface InsightsGenerateState {
  isPending: boolean;
  isError: boolean;
}

export interface EndgameInsightsReport {
  /** 1-2 sentence takeaway, the quoted header of the Insights block. */
  summary: string;
  /** Player profile paragraph (~3-5 sentences). Always populated. */
  player_profile: string;
  /**
   * Natural-language overview (1-2 paragraphs, <= 150 words).
   * Empty string when INSIGHTS_HIDE_OVERVIEW=true (per-section insights still render).
   */
  overview: string;
  /** 2-4 short bullet recommendations grounded in weak/typical metrics. */
  recommendations: string[];
  /** Min 1, max 4 section insights. */
  sections: SectionInsight[];
  /** FE does not display to end users; available for debug. */
  model_used: string;
  /** FE does not display to end users; available for debug. */
  prompt_version: string;
}

export interface EndgameInsightsResponse {
  report: EndgameInsightsReport;
  status: InsightsStatus;
}

export interface InsightsErrorResponse {
  error: InsightsError;
}

export type InsightsAxiosError = AxiosError<InsightsErrorResponse>;

// ─── Opening Insights ──────────────────────────────────────────
// Hand-mirrored from app/schemas/opening_insights.py.

export interface OpeningInsightFinding {
  color: 'white' | 'black';
  classification: 'weakness' | 'strength';
  severity: 'minor' | 'major';
  opening_name: string;
  opening_eco: string;
  display_name: string;
  entry_fen: string;
  entry_san_sequence: string[];  // SAN tokens start→entry (candidate excluded)
  entry_full_hash: string;
  candidate_move_san: string;
  resulting_full_hash: string;
  n_games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;
  ci_low: number;
  ci_high: number;
  // Wilson 99% score interval (card popover footer quotes it: the card gate is p < 0.01).
  ci99_low?: number | null;
  ci99_high?: number | null;
  // MG-entry eval fields (parity with OpeningWDL). Card findings only: not-clear findings
  // carry no eval. The eval z-test is centred on the finding colour's baseline.
  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_ci99_low_pawns?: number | null;
  eval_ci99_high_pawns?: number | null;
  eval_n?: number;
  eval_p_value?: number | null;
  eval_confidence?: 'low' | 'medium' | 'high';
  // MAX(games.played_at) across all games visiting this (entry, candidate)
  // transition. ISO 8601 string; null when contributing games all have NULL
  // played_at. Drives the finding card's "older games" chip title ("Last seen <month year>").
  last_played_at?: string | null;
  // True when last_played_at is on or after the colour's current-repertoire cutoff.
  // False renders the "older games" chip (the backend already sorted those after current ones).
  is_current: boolean;
}

export interface OpeningInsightsResponse {
  white_weaknesses: OpeningInsightFinding[];
  black_weaknesses: OpeningInsightFinding[];
  white_strengths: OpeningInsightFinding[];
  black_strengths: OpeningInsightFinding[];
  /** Medium-confidence (p < 0.05, not at 99%) candidates, at most 10 per list, current first then lowest p. */
  white_weaknesses_not_clear: OpeningInsightFinding[];
  black_weaknesses_not_clear: OpeningInsightFinding[];
  white_strengths_not_clear: OpeningInsightFinding[];
  black_strengths_not_clear: OpeningInsightFinding[];
  /** Full medium-candidate count per section, before the 10-row cap. */
  white_weaknesses_not_clear_count: number;
  black_weaknesses_not_clear_count: number;
  white_strengths_not_clear_count: number;
  black_strengths_not_clear_count: number;
  /** ISO cutoff of the current repertoire per colour; null when everything is current. */
  current_cutoff_white: string | null;
  current_cutoff_black: string | null;
  /** Per-color engine-asymmetry baselines (in pawns). Rendered as a reference tick on the finding card's eval bullet chart. */
  eval_baseline_pawns_white: number;
  eval_baseline_pawns_black: number;
}
