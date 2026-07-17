/**
 * Ply ownership by mover parity (Phase 175 Plan 06 fix).
 *
 * Even ply = White's move, odd ply = Black's move — the same convention used by
 * EvalChart's formatMoveLabel and Analysis.tsx's per-ply clock logic
 * (`if (point.ply % 2 === 0) white = ...`). A ply belongs to the user when the
 * mover at that ply is the user's color.
 *
 * Motivation: `EvalPoint.best_move_tier` (gem/great) is POSITION-scoped, not
 * user-scoped — the backend stores a tier for BOTH players' best moves. Every
 * gem/great consumption surface (eval-chart dots, count badges, cycling, board
 * markers) must therefore filter to the user's own plies, or it counts/shows the
 * opponent's gems/greats too. This helper is the single source of that parity rule
 * so no site duplicates the `ply % 2` expression.
 */

/**
 * True iff the move at `ply` was made by the user. `userColor` must be 'white' or
 * 'black'; any other value (null/undefined/free-play sentinel) yields false —
 * ownership is undefined without a known user color, and the safe default for a
 * user-only filter is to exclude rather than over-count.
 */
export function isUserPly(ply: number, userColor: 'white' | 'black' | string): boolean {
  if (userColor === 'white') return ply % 2 === 0;
  if (userColor === 'black') return ply % 2 === 1;
  return false;
}
