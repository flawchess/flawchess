/**
 * Frontend port of `app/services/score_confidence.py` for client-side Wilson
 * confidence stats over (W, D, L). Used by OpeningStatsCard so the Stats tab
 * can surface score-domain CI + p-value in its info popover without a
 * dedicated backend endpoint.
 *
 * Mirrors the backend formulas exactly:
 *   - Wilson 95% score interval, clamped to [0, 1].
 *   - Two-sided Wilson score-test p-value vs H0: score == 0.5,
 *     using null SE = 0.5 / sqrt(n) and p = erfc(|z| / sqrt(2)).
 *   - Confidence bucket with N >= 10 gate.
 */

const CI_Z_95 = 1.96;
const SCORE_PIVOT = 0.5;
const CONFIDENCE_MIN_N = 10;
const CONFIDENCE_HIGH_MAX_P = 0.01;
const CONFIDENCE_MEDIUM_MAX_P = 0.05;

export type ConfidenceLevel = 'low' | 'medium' | 'high';

export interface ScoreConfidence {
  score: number;
  ciLow: number;
  ciHigh: number;
  confidence: ConfidenceLevel;
  pValue: number;
}

function erf(x: number): number {
  // Abramowitz-Stegun 7.1.26 — max error ~1.5e-7, plenty for UI confidence calls.
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const t = 1.0 / (1.0 + p * ax);
  const y =
    1.0 -
    ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
  return sign * y;
}

function erfc(x: number): number {
  return 1.0 - erf(x);
}

export function wilsonBounds(p: number, n: number): [number, number] {
  if (n <= 0) return [0, 1];
  const z = CI_Z_95;
  const z2 = z * z;
  const denom = 1.0 + z2 / n;
  const center = (p + z2 / (2 * n)) / denom;
  const margin =
    (z * Math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n))) / denom;
  const lower = Math.max(0, Math.min(1, center - margin));
  const upper = Math.max(0, Math.min(1, center + margin));
  return [lower, upper];
}

export function computeScoreConfidence(
  wins: number,
  draws: number,
  total: number,
): ScoreConfidence {
  if (total <= 0) {
    return { score: 0.5, ciLow: 0, ciHigh: 1, confidence: 'low', pValue: 1 };
  }
  const score = (wins + 0.5 * draws) / total;
  const [ciLow, ciHigh] = wilsonBounds(score, total);
  const seNull = Math.sqrt((SCORE_PIVOT * (1 - SCORE_PIVOT)) / total);
  const z = (score - SCORE_PIVOT) / seNull;
  const pValue = erfc(Math.abs(z) / Math.sqrt(2));

  let confidence: ConfidenceLevel;
  if (total < CONFIDENCE_MIN_N) {
    confidence = 'low';
  } else if (pValue < CONFIDENCE_HIGH_MAX_P) {
    confidence = 'high';
  } else if (pValue < CONFIDENCE_MEDIUM_MAX_P) {
    confidence = 'medium';
  } else {
    confidence = 'low';
  }
  return { score, ciLow, ciHigh, confidence, pValue };
}
