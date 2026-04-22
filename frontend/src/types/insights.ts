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
  /**
   * Natural-language overview (1-2 paragraphs, <= 150 words).
   * BETA-02: empty string when INSIGHTS_HIDE_OVERVIEW=true (per-section insights still render).
   */
  overview: string;
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
