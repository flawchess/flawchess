/**
 * Shared chess display helpers.
 */

/**
 * Derive full-move count from a ply (half-move) count.
 *
 * The API exposes raw `ply_count` (exact half-moves). This helper converts it
 * to the full-move count displayed as "N Moves" in game cards (Phase 114.1).
 *
 * Math.ceil handles both even-ply games (ended on Black's move) and odd-ply
 * games (ended on White's move):
 *   - 80 plies (Black's last) → 40 full moves
 *   - 81 plies (White's last) → 41 full moves
 */
export function plysToFullMoves(plyCount: number): number {
  return Math.ceil(plyCount / 2);
}
