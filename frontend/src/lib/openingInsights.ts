import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';

// OPENING_INSIGHTS_POPOVER_COPY lives in OpeningInsightsBlock.tsx (JSX co-location).
// ConfidenceTooltipContent (JSX tooltip body) lives in
// components/insights/ConfidenceTooltipContent.tsx — kept separate so
// react-refresh can fast-refresh component vs. helper changes.

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
