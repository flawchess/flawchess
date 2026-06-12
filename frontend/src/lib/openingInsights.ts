// ConfidenceTooltipContent (JSX tooltip body) lives in
// components/insights/ConfidenceTooltipContent.tsx — kept separate so
// react-refresh can fast-refresh component vs. helper changes.

/**
 * Render a ply index and SAN in PGN move-number notation.
 *
 * Parity rule: even plyIndex = white mover, odd plyIndex = black mover.
 * (Mirrors kernel convention: `mover = "white" if n % 2 == 0`.)
 *
 * @param plyIndex - 0-based half-move index (0 = white's first move, 1 = black's first move, …)
 * @param san - The move SAN string.
 * @returns "N. san" for white plys (e.g. plyIndex=2 → "2. Nxd4"),
 *          "N... san" for black plys (e.g. plyIndex=3 → "2... c5").
 *
 * Shared primitive (D-04): FlawCard imports this directly;
 * formatCandidateMove delegates to it (no duplication).
 */
export function formatMoveNotation(plyIndex: number, san: string): string {
  const isWhitePly = plyIndex % 2 === 0;
  const moveNumber = Math.floor(plyIndex / 2) + 1;
  return isWhitePly ? `${moveNumber}. ${san}` : `${moveNumber}... ${san}`;
}

/**
 * Render the candidate move alone with PGN move-number notation. The board
 * already shows the position context, so the card only needs to identify the
 * single move that produced the score.
 *
 * Delegates to `formatMoveNotation` (D-04 — no duplicated plyIndex/moveNumber
 * logic). The plyIndex is derived from `entrySanSequence.length` — the number
 * of half-moves played to reach the entry position equals the 0-based index
 * of the next (candidate) move in the full game.
 *
 * @param entrySanSequence - SAN tokens from start to entry position (candidate excluded). May be empty.
 * @param candidateMoveSan - The candidate move SAN (always present).
 * @returns "N. san" for white plys, "N... san" for black plys (e.g. "4. Nxd4", "3... c5").
 */
export function formatCandidateMove(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string {
  return formatMoveNotation(entrySanSequence.length, candidateMoveSan);
}
