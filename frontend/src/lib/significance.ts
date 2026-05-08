import type { ConfidenceLevel } from '@/lib/scoreConfidence';

/**
 * Confidence-bucket gate for zone-coloring text labels.
 *
 * The Openings tabs only paint a value red/green when (a) the value falls in
 * a colored zone, and (b) the result is statistically confident — the bucket
 * is 'medium' or 'high', not 'low'. Buckets are derived from a p-value
 * threshold in scoreConfidence.ts (currently p < 0.05 for medium); call
 * sites gate on the categorical bucket so the threshold can move without
 * touching every consumer.
 */
export function isConfident(
  confidence: ConfidenceLevel | null | undefined,
): boolean {
  return confidence != null && confidence !== 'low';
}
