/**
 * trainRecheck — pure rules for the Phase 235 disagreement re-check (SEED-192).
 *
 * The phone grades a played move against the server key with two same-horizon
 * 1.5 s searches. When that reading says a SHARP off-key move is good, the
 * answer key may be the weaker side of the disagreement, so the solve screen
 * looks again for 3 s per search before posting. Everything here is pure and
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
}

/**
 * D-10/D-19: re-check only a sharp puzzle's off-key, off-runner-up move that
 * the 1.5 s grade rated good. "Good only" is the owner's choice: an inaccuracy
 * or wrong reading already costs the user points, and the rare disagreement
 * this exists for (~1 in 700 sharp solves) is the phone's move surviving. The
 * sharp runner-up is excluded because the server grades it from its own blob
 * (D-02), so a re-check would burn 6 s on a result the server overrides.
 */
export function shouldRecheck(input: ShouldRecheckInput): boolean {
  return (
    input.puzzleType === 'sharp' &&
    input.keyUci !== null &&
    input.playedUci !== input.keyUci &&
    input.playedUci !== input.runnerUpUci &&
    input.tier === 'good'
  );
}

/** D-13: the re-check is confirmed iff the 3 s reading still rates the played move good. */
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
