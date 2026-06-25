/**
 * Full-move label for a PV move anchored to the real game ply.
 *
 * `flawPly + index` is the 0-based ply BEFORE this move is made. Returns the
 * standard move-number label: "12." for a white move, "12..." for a black move.
 *
 * Used by the TacticLineExplorer horizontal move list so the numbering matches
 * the real game ply (Phase 135).
 */
export function moveLabel(flawPly: number, index: number): string {
  const realPly = flawPly + index; // ply BEFORE this move is made (0-based)
  const fullMove = Math.ceil((realPly + 1) / 2);
  const isWhite = realPly % 2 === 0;
  return isWhite ? `${fullMove}.` : `${fullMove}...`;
}
