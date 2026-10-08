/**
 * trainPhoneGrade — the phone's own grading reading as an audit record
 * (Phase 236, SEED-193).
 *
 * Every keyed solve graded on the phone records the 1.5 s expected-score pair
 * (after-key vs after-played) with the tier it produced and the engine depths,
 * so the server can compare phone grades with its own blob grades over time.
 * It is audit data only and never a grading input (D-02), and it carries no
 * device or engine field (D-07). Pure, no React.
 */

import type { TrainMoveTier } from '@/lib/trainScore';
import type { PhoneGrade, ServerGradedMove } from '@/types/train';

/** Mirrors PHONE_GRADE_SCHEMA_VERSION in app/schemas/train.py (the server accepts only this value). */
const PHONE_GRADE_SCHEMA_VERSION = 1 as const;

/**
 * The phone's reading for one keyed solve (D-04): mover-POV expected scores of
 * the think-time after-key search and the after-played search at the standard
 * grading budget, plus the tier they produced. Depths are as reported by the
 * engine, null when no exact line arrived.
 */
export interface PhoneReading {
  tier: TrainMoveTier;
  keyEs: number;
  playedEs: number;
  keyDepth: number | null;
  playedDepth: number | null;
}

/** Map the camelCase reading to the snake_case wire record; a null depth is sent as 0. */
export function buildPhoneGradePayload(reading: PhoneReading): PhoneGrade {
  return {
    v: PHONE_GRADE_SCHEMA_VERSION,
    tier: reading.tier,
    key_es: reading.keyEs,
    played_es: reading.playedEs,
    key_depth: reading.keyDepth ?? 0,
    played_depth: reading.playedDepth ?? 0,
  };
}

/**
 * The tier the server owns for a played move (Phase 236 D-09/D-10), or null
 * when the solve keeps today's graded path.
 *
 * Null when `keyUci` is null (the legacy no-key path; D-08 sends no set there
 * anyway) or when the played move IS the key: the key is listed for soft and
 * herring puzzles, but that solve already waits only for the think-time anchor
 * and carries its D-05 record on the POST (D-13). Otherwise the tier of the
 * FIRST entry matching `playedUci` (first match, like `_override_for_key_move`).
 *
 * The returned tier is only ever ASSERTED on the solve POST (D-10), never
 * rendered (D-09): the verdict comes from the SolveResponse.
 */
export function instantServerTier(
  moves: readonly ServerGradedMove[],
  playedUci: string,
  keyUci: string | null,
): TrainMoveTier | null {
  if (keyUci === null || playedUci === keyUci) return null;
  const entry = moves.find((move) => move.uci === playedUci);
  return entry === undefined ? null : entry.tier;
}
