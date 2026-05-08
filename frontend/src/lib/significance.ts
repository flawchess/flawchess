/**
 * Statistical-significance helper for zone-coloring text labels.
 *
 * The Openings tabs only paint a value red/green when (a) the value falls in
 * the red or green zone, and (b) the result is statistically significant at
 * p < 0.05. Otherwise the text renders in the default foreground color so the
 * eye is drawn to values we're confident about.
 *
 * For the score domain, `confidence !== 'low'` is equivalent to `p < 0.05`
 * because computeScoreConfidence buckets at CONFIDENCE_MEDIUM_MAX_P = 0.05
 * (see scoreConfidence.ts). Either expression works at call sites; this
 * helper accepts both shapes so callers can pass whichever they have on
 * hand.
 */
export const SIGNIFICANCE_P_THRESHOLD = 0.05;

export function isSignificant(pValue: number | null | undefined): boolean {
  return pValue != null && pValue < SIGNIFICANCE_P_THRESHOLD;
}
