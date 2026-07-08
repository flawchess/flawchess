/**
 * engineEvalLookup — pure, worker-free module that is the single UCI-keyed
 * eval lookup for the whole `/analysis` page (Phase 158, SEED-087).
 *
 * Merges the authoritative free run's `pvLines` (UCI-keyed by `moves[0]`) and
 * the shared grading run's `gradeMapBySan` (SAN-keyed — see
 * useStockfishGradingEngine.ts's "key by pv[0], multipv is an eval rank, not
 * a stable move identity" caveat, which applies transitively here since this
 * module consumes that same grade map) into one `Map<string, MoveGrade>`
 * keyed by UCI, with strict free-run-first precedence: a move present in both
 * sources always resolves to the free-run value, never the grading value.
 *
 * Reuses `sanToUci` from `@/lib/sanToSquares` for SAN->UCI conversion (never
 * a second SAN<->UCI implementation) and the `MoveGrade` type from
 * `@/lib/moveQuality` rather than re-deriving either. Does NOT re-normalize
 * sign or apply any sigmoid math — both sources are already white-POV
 * normalized upstream.
 *
 * Does NOT read any MCTS pool grade — there is no such parameter. This makes
 * "display a shallow pool grade" impossible by construction (CONTEXT.md
 * LOCKED): a move absent from both the free run and the grading run resolves
 * to `null`, never a pool-derived fallback.
 */

import { sanToUci } from '@/lib/sanToSquares';
import type { PvLine } from '@/hooks/uciParser';
import type { MoveGrade } from '@/lib/moveQuality';

/**
 * Builds the UCI-keyed eval lookup from the free run's `pvLines` and the
 * grading run's SAN-keyed `gradeMapBySan`, relative to `baseFen`.
 *
 * Free run first: every `pvLines` entry is inserted under its own
 * `moves[0]` UCI key. The grading run is layered in second, converting each
 * SAN via `sanToUci(baseFen, san)` — a SAN that `sanToUci` cannot resolve
 * (returns null) is skipped, never thrown. Either loop uses
 * `!lookup.has(uci)` so a free-run entry is never overwritten by a grading
 * entry for the same move (precedence never regresses).
 */
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();

  for (const line of pvLines) {
    const uci = line.moves[0];
    if (uci === undefined || lookup.has(uci)) continue;
    lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth });
  }

  for (const [san, grade] of gradeMapBySan) {
    const uci = sanToUci(baseFen, san);
    if (uci === null || lookup.has(uci)) continue;
    lookup.set(uci, grade);
  }

  return lookup;
}

/** Looks up a move's eval by its UCI key. Never `undefined` — `null` when absent. */
export function getByUci(lookup: Map<string, MoveGrade>, uci: string): MoveGrade | null {
  return lookup.get(uci) ?? null;
}

/**
 * Looks up a move's eval by its SAN, converting to UCI via `sanToUci(baseFen,
 * san)` first. An unresolvable SAN returns `null`, never a throw.
 */
export function getBySan(lookup: Map<string, MoveGrade>, baseFen: string, san: string): MoveGrade | null {
  const uci = sanToUci(baseFen, san);
  if (uci === null) return null;
  return getByUci(lookup, uci);
}
