import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';

// OPENING_INSIGHTS_POPOVER_COPY lives in OpeningInsightsBlock.tsx (JSX co-location).

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_PREFIX: Record<ConfidenceLevel, string> = {
  low: 'Low confidence',
  medium: 'Medium confidence',
  high: 'High confidence',
};

const CONFIDENCE_VERDICT: Record<ConfidenceLevel, (noun: string) => string> = {
  low: () => 'could plausibly be chance',
  medium: (noun) => `is likely a real ${noun}`,
  high: (noun) => `is very likely a real ${noun}`,
};

/**
 * Tooltip copy for confidence indicators — significance level explainer with the
 * observed score, its signed distance from the 50% break-even line, and the p-value.
 * `noun` is the directional thing being claimed: "strength" when score ≥ 50%,
 * otherwise "weakness".
 */
export function formatConfidenceTooltip(
  level: ConfidenceLevel,
  pValue: number,
  score: number,
): string {
  const noun: 'strength' | 'weakness' = score >= 0.5 ? 'strength' : 'weakness';
  const scorePct = score * 100;
  const roundedScore = Math.round(scorePct);
  const diff = scorePct - 50;
  const roundedDiff = Math.round(Math.abs(diff));
  const scoreDescriptor =
    roundedDiff === 0
      ? `${roundedScore}% score (at 50%)`
      : `${roundedScore}% score (${roundedDiff}% ${diff >= 0 ? 'above' : 'below'} 50%)`;
  return `${CONFIDENCE_PREFIX[level]}: ${scoreDescriptor} ${CONFIDENCE_VERDICT[level](noun)} (p = ${pValue.toFixed(3)})`;
}

/**
 * Map a classification + severity tuple to the appropriate border-left color hex.
 * Mirrors getArrowColor's two-tier shade scheme — guarantees the card border and
 * the on-board arrow render the same color after the deep-link.
 */
export function getSeverityBorderColor(
  classification: OpeningInsightFinding['classification'],
  severity: OpeningInsightFinding['severity'],
): string {
  if (classification === 'weakness') {
    return severity === 'major' ? DARK_RED : LIGHT_RED;
  }
  return severity === 'major' ? DARK_GREEN : LIGHT_GREEN;
}

/**
 * Render the candidate move alone with PGN move-number notation. The board
 * already shows the position context, so the card only needs to identify the
 * single move that produced the score.
 *
 * @param entrySanSequence - SAN tokens from start to entry position (candidate excluded). May be empty.
 * @param candidateMoveSan - The candidate move SAN (always present).
 * @returns "N.san" for white plys, "N...san" for black plys (e.g. "4.Nxd4", "3...c5").
 */
export function formatCandidateMove(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string {
  const plyIndex = entrySanSequence.length;  // 0-based index of the candidate in the full sequence
  const isWhitePly = plyIndex % 2 === 0;
  const moveNumber = Math.floor(plyIndex / 2) + 1;
  return isWhitePly ? `${moveNumber}.${candidateMoveSan}` : `${moveNumber}...${candidateMoveSan}`;
}
