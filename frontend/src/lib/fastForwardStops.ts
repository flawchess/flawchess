import { isUserPly } from '@/lib/plyOwnership';
import { isRareMoveTier } from '@/types/library';
import type { EvalPoint, FlawMarker } from '@/types/library';

interface FastForwardStopInputs {
  flawMarkers: readonly FlawMarker[] | null | undefined;
  evalSeries: readonly EvalPoint[] | null | undefined;
  userColor: string | null | undefined;
  ownMovesOnly: boolean;
}

/**
 * Main-line plies where the analysis board's Jump (fast-forward) button stops:
 * plies whose FlawMarker.severity is blunder/mistake, plus plies whose
 * EvalPoint.best_move_tier is gem/great. Both sides by default, matching the
 * board's both-sides highlight display.
 *
 * Derived from eval_series directly rather than from the board's
 * storedGemGreatByPly map: that map additionally requires maia_prob != null, a
 * TypeScript-narrowing artifact of its own purpose that could silently drop a
 * legitimate stop here.
 *
 * With `ownMovesOnly` the set is narrowed to the user's plies (isUserPly is the
 * single parity rule). An unknown user color falls back to both sides on
 * purpose: isUserPly is false for it, so filtering would empty the set and make
 * Jump run straight to the final move.
 */
export function computeFastForwardStops(inputs: FastForwardStopInputs): Set<number> {
  const { flawMarkers, evalSeries, userColor, ownMovesOnly } = inputs;
  const stops = new Set<number>();
  for (const fm of flawMarkers ?? []) {
    if (fm.severity === 'blunder' || fm.severity === 'mistake') stops.add(fm.ply);
  }
  for (const point of evalSeries ?? []) {
    if (isRareMoveTier(point.best_move_tier)) stops.add(point.ply);
  }
  if (!ownMovesOnly || (userColor !== 'white' && userColor !== 'black')) return stops;
  return new Set([...stops].filter((ply) => isUserPly(ply, userColor)));
}
