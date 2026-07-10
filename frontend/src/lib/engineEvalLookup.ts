/**
 * engineEvalLookup — pure, worker-free module that is the single UCI-keyed
 * eval lookup for the whole `/analysis` page (Phase 158, SEED-087; flipped
 * to grading-first precedence in Phase 162, SEED-090).
 *
 * Merges the shared grading run's `gradeMapBySan` (SAN-keyed — see
 * useStockfishGradingEngine.ts's "key by pv[0], multipv is an eval rank, not
 * a stable move identity" caveat, which applies transitively here since this
 * module consumes that same grade map) and the free run's `pvLines`
 * (UCI-keyed by `moves[0]`) into one `Map<string, MoveGrade>` keyed by UCI,
 * with grading-first precedence: a move present in both sources resolves to
 * the grading (deeper, depth-parity) value, not the free-run value. A move
 * present ONLY in the free run (not yet graded) still resolves to the
 * free-run value, preserving its placeholder role until grading catches up.
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
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';

/**
 * Builds the UCI-keyed eval lookup from the grading run's SAN-keyed
 * `gradeMapBySan` and the free run's `pvLines`, relative to `baseFen`.
 *
 * Grading run first: every `gradeMapBySan` entry is inserted under its
 * `sanToUci(baseFen, san)` UCI key — a SAN that `sanToUci` cannot resolve
 * (returns null) is skipped, never thrown. The free run is layered in
 * second, inserting each `moves[0]` entry only when `!lookup.has(uci)`, so
 * a not-yet-graded move still resolves to the free-run value while an
 * overlapping move resolves to the grading value (grading-wins-on-overlap,
 * free-run-fills-gaps).
 */
export function buildEvalLookup(
  pvLines: PvLine[],
  gradeMapBySan: Map<string, MoveGrade>,
  baseFen: string,
): Map<string, MoveGrade> {
  const lookup = new Map<string, MoveGrade>();

  for (const [san, grade] of gradeMapBySan) {
    const uci = sanToUci(baseFen, san);
    if (uci === null || lookup.has(uci)) continue;
    lookup.set(uci, grade);
  }

  for (const line of pvLines) {
    const uci = line.moves[0];
    if (uci === undefined || lookup.has(uci)) continue;
    // `pv` retained (162 UAT) so a free-run entry can render its full move
    // sequence on the Stockfish card, symmetric with grading entries.
    lookup.set(uci, { evalCp: line.evalCp, evalMate: line.evalMate, depth: line.depth, pv: line.moves });
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

/** One reconciled ranked candidate: its UCI key and the grade it resolved to. */
export interface ReconciledCandidate {
  uci: string;
  grade: MoveGrade;
}

/**
 * Full reconciled ranking (162 UAT card re-source) — every candidate that
 * resolves through `evalLookup`, sorted by descending expected score. The
 * Stockfish card's displayed lines are `slice(0, 2)` of this; the canonical
 * argmax (`resolveReconciledBest`) is its head, so card line 1, arrow, chart
 * crown, and verdict agree by construction.
 *
 * Skips (never throws on) a UCI absent from `evalLookup`. Expected score via
 * `evalToExpectedScore` from `@/lib/liveFlaw` — the project's ONLY sigmoid,
 * never re-derived here. The sort is stable (candidate input order preserved
 * on ties), except an EXACT expected-score tie prefers `tieBreakUci` — the
 * same semantics the pre-ranking argmax loop had.
 */
export function rankReconciledCandidates(
  evalLookup: Map<string, MoveGrade>,
  candidateUcis: string[],
  mover: MoverColor,
  tieBreakUci: string | null,
): ReconciledCandidate[] {
  const resolved: Array<ReconciledCandidate & { es: number }> = [];
  for (const uci of candidateUcis) {
    const grade = evalLookup.get(uci);
    if (!grade) continue;
    resolved.push({ uci, grade, es: evalToExpectedScore(grade.evalCp, grade.evalMate, mover) });
  }
  resolved.sort((a, b) => {
    if (b.es !== a.es) return b.es - a.es;
    if (a.uci === tieBreakUci) return -1;
    if (b.uci === tieBreakUci) return 1;
    return 0;
  });
  return resolved.map(({ uci, grade }) => ({ uci, grade }));
}

/**
 * Canonical reconciled-best resolver (Phase 162 D-03) — the single argmax
 * every downstream display consumer (arrow, verdict, eval bar, labels)
 * threads through instead of re-deriving its own best-move loop over
 * `evalLookup` (the Phase 158 anti-pattern this phase exists to kill).
 *
 * The head of `rankReconciledCandidates` (same skip/tie-break semantics —
 * one ranking, argmax = its first element). Returns `null` when no candidate
 * resolves to a grade.
 */
export function resolveReconciledBest(
  evalLookup: Map<string, MoveGrade>,
  candidateUcis: string[],
  mover: MoverColor,
  tieBreakUci: string | null,
): string | null {
  return rankReconciledCandidates(evalLookup, candidateUcis, mover, tieBreakUci)[0]?.uci ?? null;
}
