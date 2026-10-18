import { sanToSquares } from '@/lib/sanToSquares';
import { isConfident } from '@/lib/significance';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type { OpeningInsightFinding } from '@/types/insights';

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
 * Shared primitive: FlawCard imports this directly;
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
 * Delegates to `formatMoveNotation` (no duplicated plyIndex/moveNumber
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

/** "2... e6": the move a finding is about, in PGN notation. */
export function findingMoveText(finding: OpeningInsightFinding): string {
  return formatCandidateMove(finding.entry_san_sequence, finding.candidate_move_san);
}

/**
 * True when the candidate move is the user's own, false for an opponent's reply. The side to
 * move at the entry position follows the ply parity (even = white, as in formatMoveNotation).
 */
export function isOwnMove(finding: OpeningInsightFinding): boolean {
  const whiteToMove = finding.entry_san_sequence.length % 2 === 0;
  return whiteToMove === (finding.color === 'white');
}

/**
 * One arrow from the candidate move's squares, red for a weakness and green for a strength.
 * A low-confidence card gets the neutral blue (D-38): listed by rank, but its direction is not a
 * verdict, matching its blue spine.
 */
export function findingArrows(
  finding: OpeningInsightFinding,
): ReadonlyArray<{ from: string; to: string; color: string }> | undefined {
  const squares = sanToSquares(finding.entry_fen, finding.candidate_move_san);
  if (!squares) return undefined;
  const color = !isConfident(finding.confidence)
    ? ZONE_NEUTRAL
    : finding.classification === 'weakness'
      ? ZONE_DANGER
      : ZONE_SUCCESS;
  return [{ from: squares.from, to: squares.to, color }];
}
