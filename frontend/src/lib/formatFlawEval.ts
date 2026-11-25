/**
 * Adjust a stored white-POV mate count for how far the user has stepped into a PV.
 *
 * `anchorMate` is the signed moves-to-mate at the line's eval anchor (white-POV:
 * positive = white delivers mate). The UCI mate score counts the *mating side's*
 * remaining moves, so it drops by one each time the mating side moves — every two
 * plies — and the first drop's timing depends on whose turn it is at the anchor.
 *
 * `matingSideToMoveAtAnchor` selects that parity: when the mating side is to move
 * at the anchor it delivers mate on ply `2|M|-1`, otherwise on ply `2|M|`. Walking
 * `stepPlies` into the line leaves `pliesToMate - stepPlies` plies to mate; the
 * displayed (white-POV) count is `ceil(remaining / 2)` with the original sign.
 * Returns 0 once mate has been delivered (the mate count tracks the
 * selected ply in the Tactic Line Explorer).
 */
export function mateAtPly(
  anchorMate: number,
  stepPlies: number,
  matingSideToMoveAtAnchor: boolean,
): number {
  const absMate = Math.abs(anchorMate);
  const pliesToMate = matingSideToMoveAtAnchor ? 2 * absMate - 1 : 2 * absMate;
  const remaining = pliesToMate - stepPlies;
  if (remaining <= 0) return 0;
  return Math.sign(anchorMate) * Math.ceil(remaining / 2);
}
