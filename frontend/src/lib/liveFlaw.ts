/**
 * liveFlaw — classify a freely-played board move (off the precomputed game line)
 * from the live engine's eval before vs after the move (Quick w8k item 4).
 *
 * Mirrors the backend severity method (app/services/flaws_service.py +
 * app/services/eval_utils.py): convert each white-POV engine eval to the mover's
 * expected score via the Lichess winning-chances sigmoid (mate mapped to ±1000cp,
 * the same "Option B" mapping the flaw classifier uses), then grade the drop:
 *   drop >= BLUNDER_DROP (0.15)    → blunder
 *   drop >= MISTAKE_DROP (0.10)    → mistake
 *   drop >= INACCURACY_DROP (0.05) → inaccuracy
 * All thresholds come from the generated mirror so they never drift from Python.
 */

import type { FlawSeverity } from '@/types/library';
import {
  BLUNDER_DROP,
  MISTAKE_DROP,
  INACCURACY_DROP,
  MATE_CP_EQUIVALENT,
  LICHESS_K,
} from '@/generated/flawThresholds';

export type MoverColor = 'white' | 'black';

/** Side to move encoded in a FEN's second field. Defaults to white on malformed input. */
export function sideToMoveFromFen(fen: string): MoverColor {
  return fen.split(' ')[1] === 'b' ? 'black' : 'white';
}

/**
 * Convert a white-POV engine eval (cp or mate-in-N) to the mover's expected score
 * in (0, 1). Mate is mapped to ±MATE_CP_EQUIVALENT cp before the sigmoid (Option B),
 * matching the flaw classifier. Returns 0.5 (neutral) when no eval is available.
 */
export function evalToExpectedScore(
  evalCp: number | null,
  evalMate: number | null,
  mover: MoverColor,
): number {
  const sign = mover === 'white' ? 1 : -1;
  let cp: number;
  if (evalMate != null && evalMate !== 0) {
    cp = evalMate > 0 ? MATE_CP_EQUIVALENT : -MATE_CP_EQUIVALENT;
  } else if (evalCp != null) {
    cp = evalCp;
  } else {
    return 0.5;
  }
  return 1 / (1 + Math.exp(-LICHESS_K * sign * cp));
}

/**
 * Grade the mover's move from the expected-score drop (best achievable before the
 * move minus what the played move achieved). Returns null for a clean move.
 */
export function classifyLiveSeverity(esBefore: number, esAfter: number): FlawSeverity | null {
  const drop = esBefore - esAfter;
  if (drop >= BLUNDER_DROP) return 'blunder';
  if (drop >= MISTAKE_DROP) return 'mistake';
  if (drop >= INACCURACY_DROP) return 'inaccuracy';
  return null;
}
