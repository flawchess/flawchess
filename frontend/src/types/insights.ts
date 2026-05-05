import type { AxiosError } from 'axios';

/**
 * Phase 65 response envelope types. Consumed by useEndgameInsights hook
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
  | 'cache_hit'
  | 'stale_rate_limited';

export type InsightsError =
  | 'rate_limit_exceeded'
  | 'provider_error'
  | 'validation_failure'
  | 'config_error';

export interface SectionInsight {
  section_id: SectionId;
  headline: string;    // <= 120 chars (~12 words)
  bullets: string[];   // 0..2 items, each <= 200 chars (~20 words)
}

export interface EndgameInsightsReport {
  /** v9: Player profile paragraph (~3-5 sentences). Always populated. */
  player_profile: string;
  /**
   * Natural-language overview (1-2 paragraphs, <= 150 words).
   * BETA-02: empty string when INSIGHTS_HIDE_OVERVIEW=true (per-section insights still render).
   */
  overview: string;
  /** v9: 2-4 short bullet recommendations grounded in weak/typical metrics. */
  recommendations: string[];
  /** Min 1, max 4 section insights. See Phase 65 D-19. */
  sections: SectionInsight[];
  /** FE does not display to end users; available for debug. */
  model_used: string;
  /** FE does not display to end users; available for debug. */
  prompt_version: string;
}

export interface EndgameInsightsResponse {
  report: EndgameInsightsReport;
  status: InsightsStatus;
  /** D-13: FE ignores this field. Retained for debug/future use. */
  stale_filters: unknown;
}

export interface InsightsErrorResponse {
  error: InsightsError;
  /** Only populated on HTTP 429 rate_limit_exceeded. */
  retry_after_seconds: number | null;
}

export type InsightsAxiosError = AxiosError<InsightsErrorResponse>;

// ─── Phase 71 — Opening Insights ──────────────────────────────────────────
// Hand-mirrored from app/schemas/opening_insights.py.
// entry_san_sequence added by Phase 71 backend amendment (Plan 01, D-13).

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
}

export interface OpeningInsightsResponse {
  white_weaknesses: OpeningInsightFinding[];
  black_weaknesses: OpeningInsightFinding[];
  white_strengths: OpeningInsightFinding[];
  black_strengths: OpeningInsightFinding[];
}
