/**
 * Shared helpers and constants for the Phase 85 "Endgame Overall Performance"
 * composite section (EndgameOverallPerformanceSection + sub-cards). Co-located
 * here rather than promoted to a global lib so the surface stays scoped to the
 * components that own this view.
 */

import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import { MIN_GAMES_FOR_RELIABLE_STATS } from '@/lib/theme';

// Endgame tile half-domain for the W+0.5D bullets. Locked to 0.15 per
// CONTEXT D-13 so the neutral band [0.45, 0.55] fills ≈1/3 of the axis (0.10 / 0.30).
export const ENDGAME_TILE_SCORE_DOMAIN = 0.15;

// Score Gap bullet half-domain. p05 tail reaches -22.1pp and was clipped at the
// old ±0.20 axis edge; ±0.22 covers it per
// reports/benchmarks-diff-2026-05-17-vs-2026-05-19.md item B.
export const SCORE_GAP_DOMAIN = 0.22;

// Per-class Score Gap (Endgame Type Breakdown) half-domain. Sized so the
// neutral band (±0.04, width 0.08) fills 1/3 of the axis — matching the
// Endgame Score bullet above it (band 0.10 / axis 0.30 = 1/3).
export const ENDGAME_TYPE_SCORE_GAP_DOMAIN = 0.12;

// Confidence-bucket thresholds (mirrors scoreConfidence.computeScoreConfidence).
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

// Kept in lockstep with scoreConfidence.computeScoreConfidence's bucketing.
// Takes a precomputed p-value instead of (W, D, total) so backend-provided
// p-values (endgame_score_p_value, non_endgame_score_p_value, ...) can drive
// the same confidence buckets the UI uses everywhere else.
export function deriveLevel(p: number | null, n: number): ConfidenceLevel {
  if (n < MIN_GAMES_FOR_RELIABLE_STATS || p == null) return 'low';
  if (p < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (p < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}
