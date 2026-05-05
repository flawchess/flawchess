// OPENING_INSIGHTS_POPOVER_COPY lives in OpeningInsightsBlock.tsx (JSX co-location).
// ConfidenceTooltipContent (JSX tooltip body) lives in
// components/insights/ConfidenceTooltipContent.tsx — kept separate so
// react-refresh can fast-refresh component vs. helper changes.

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
