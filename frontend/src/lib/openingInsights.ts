import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';

// OPENING_INSIGHTS_POPOVER_COPY lives in OpeningInsightsBlock.tsx (JSX co-location).

type ConfidenceLevel = 'low' | 'medium' | 'high';

const CONFIDENCE_BASE_COPY: Record<ConfidenceLevel, (noun: string) => string> = {
  low: () => 'Not enough evidence: this could plausibly be chance',
  medium: (noun) => `Moderate evidence: this is likely a real ${noun}`,
  high: (noun) => `Strong evidence: this is very likely a real ${noun}`,
};

/**
 * Tooltip copy for confidence indicators — significance level explainer plus the actual p-value.
 * `noun` is the directional thing being claimed (e.g. "weakness", "strength"). Defaults to
 * "effect" for the Move Explorer's non-directional confidence column.
 */
export function formatConfidenceTooltip(
  level: ConfidenceLevel,
  pValue: number,
  noun: string = 'effect',
): string {
  return `${CONFIDENCE_BASE_COPY[level](noun)} (p = ${pValue.toFixed(3)})`;
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
