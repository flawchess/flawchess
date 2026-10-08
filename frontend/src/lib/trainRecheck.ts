/**
 * trainRecheck — pure rules for the Phase 235 disagreement re-check (SEED-192).
 *
 * The phone grades a played move against the server key with two same-horizon
 * 1.5 s searches. When that reading says a SHARP off-key move is good (the key
 * may be the weaker side of the disagreement), or that any off-key move is an
 * inaccuracy (the short search may have under-read it), the solve screen looks
 * again for 3 s per search before posting. Everything here is pure and
 * takes camelCase parameters: the snake_case TrainPuzzle fields (the key, the
 * puzzle type, the runner-up) are read only in TrainSolveScreen.tsx (D-05).
 * No engine, no React, so it is cheap to test and the hook can share it.
 */

import type { TrainPuzzleType } from '@/lib/trainArrows';
import type { TrainMoveTier } from '@/lib/trainScore';
import type { RecheckOutcome, SolveRecheck } from '@/types/train';

/** Mirrors RECHECK_SCHEMA_VERSION in app/schemas/train.py (the server accepts only this value). */
const RECHECK_SCHEMA_VERSION = 1 as const;

export interface ShouldRecheckInput {
  puzzleType: TrainPuzzleType | null;
  keyUci: string | null;
  runnerUpUci: string | null;
  playedUci: string;
  tier: TrainMoveTier;
  /** D-11 (Phase 236): the UCIs of `TrainPuzzle.server_graded_moves`. */
  serverGradedUcis: readonly string[];
}

/**
 * D-10/D-19: re-check a keyed puzzle's off-key, off-runner-up move in two cases:
 *
 * - a SHARP puzzle whose move the 1.5 s grade rated good (Phase 235): the
 *   answer key may be the weaker side of the disagreement, and the confirmed
 *   claim can earn the guess point server-side;
 * - ANY keyed puzzle whose move the 1.5 s grade rated inaccuracy (quick task
 *   261008-ob1): the short lite search under-reads some sound moves by a few
 *   tenths, which pushes a borderline drop (just under INACCURACY_DROP at
 *   depth) over the line and costs a move point. Prod repro: Nc6 read -0.8 at
 *   1.5 s, -1.2 at depth 12-24 against a -1.8 key. The noise is
 *   type-independent, so this case is not limited to sharp puzzles.
 *
 * A wrong (mistake/blunder) reading is never re-checked: a 1.5 s search rarely
 * overstates a drop of 0.10 or more enough to flip the verdict, and it would
 * add the ~6 s wait to a large share of solves. The sharp runner-up is
 * excluded because the server grades it from its own blob (D-02), so a
 * re-check would burn 6 s on a result the server overrides. The same holds for
 * every move in the puzzle's server-graded set (Phase 236 D-11): the server
 * discards the phone tier for it, so the ~6 s re-check would buy nothing.
 */
export function shouldRecheck(input: ShouldRecheckInput): boolean {
  const offKey =
    input.keyUci !== null &&
    input.playedUci !== input.keyUci &&
    input.playedUci !== input.runnerUpUci;
  if (!offKey) return false;
  if (input.serverGradedUcis.includes(input.playedUci)) return false;
  if (input.tier === 'inaccuracy') return true;
  return input.puzzleType === 'sharp' && input.tier === 'good';
}

/** D-13: the re-check is confirmed iff the 3 s reading rates the played move
 * good. For an inaccuracy-triggered re-check that means the move was upgraded;
 * the two trigger populations stay separable by the 1.5 s pair in the record. */
export function recheckOutcome(tier: TrainMoveTier): RecheckOutcome {
  return tier === 'good' ? 'confirmed' : 'resolved';
}

export interface RecheckPayloadInput {
  outcome: RecheckOutcome;
  /** Mover-POV expected scores of the 1.5 s key and played searches. */
  keyEs: number;
  playedEs: number;
  keyDepth: number | null;
  playedDepth: number | null;
  /** Mover-POV expected scores of the 3 s key and played searches. */
  keyEsRecheck: number;
  playedEsRecheck: number;
  keyDepthRecheck: number | null;
  playedDepthRecheck: number | null;
}

/** Map the camelCase readings to the snake_case wire record; a null depth is sent as 0. */
export function buildRecheckPayload(input: RecheckPayloadInput): SolveRecheck {
  return {
    v: RECHECK_SCHEMA_VERSION,
    outcome: input.outcome,
    key_es: input.keyEs,
    played_es: input.playedEs,
    key_es_recheck: input.keyEsRecheck,
    played_es_recheck: input.playedEsRecheck,
    key_depth: input.keyDepth ?? 0,
    played_depth: input.playedDepth ?? 0,
    key_depth_recheck: input.keyDepthRecheck ?? 0,
    played_depth_recheck: input.playedDepthRecheck ?? 0,
  };
}
