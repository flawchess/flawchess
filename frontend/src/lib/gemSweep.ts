/**
 * gemSweep — pure, worker-free primitives for the background gem sweep
 * (Phase 172, SEED-106 D-04, D-05).
 *
 * Two independent pieces live here, both deliberately free of React and
 * Worker imports:
 *
 * 1. `selectSweepCandidates` — the FREE prefilter (D-04). A gem requires C2
 *    (played move is the graded best AND beats the runner-up by at least
 *    MISTAKE_DROP), and C2 implies the played move lost ~zero expected score.
 *    So most plies can be eliminated with data the analysis page already
 *    fetches and currently ignores: `EvalPoint.best_move` (the backend's
 *    engine best move FROM that position, UCI). Nothing here calls Maia or
 *    Stockfish — it is pure data filtering. Mirrors the backend's existing
 *    `_hint_flaw_plies` trick (`scripts/remote_eval_worker.py:226`).
 *
 * 2. `nextSweepDispatch` — the D-05 yield-to-cursor scheduler decision. The
 *    sweep must never starve the live free-run / grading engines for the
 *    position the user is actually looking at. This function is the ONLY
 *    place that decides whether background sweep work may start, and it is
 *    written as a pure function specifically so the yield-to-cursor
 *    invariant is provable without mocking React or Workers — see
 *    `__tests__/gemSweep.test.ts` for the revert-and-fail-red proof.
 */

import { sanToUci } from '@/lib/sanToSquares';
import type { EvalPoint } from '@/types/library';

/** One ply that survived the free prefilter and is ready for the cheap
 *  (Maia C1) / expensive (Stockfish parent grade) cascade stages. */
export interface SweepCandidate {
  /** 0-based index into `moves` / `eval_series` — moves[i] and eval_series[i]
   *  share the same ply index (see EvalPoint's doc comment in library.ts). */
  plyIndex: number;
  /** FEN of the position BEFORE `playedSan` was played. */
  parentFen: string;
  /** The SAN move actually played at this ply. */
  playedSan: string;
}

/**
 * D-04 free prefilter: keep only plies where the played move equals the
 * graded best move AND the ply is out of the opening book.
 *
 * `EvalPoint.best_move` is UCI; `moves[i]` is SAN — `sanToUci` converts the
 * played move against its PARENT fen before comparing. A naive string
 * compare (`playedSan === point.best_move`) is a silent no-op, since a SAN
 * string like "Nf3" never equals a UCI string like "g1f3" (RESEARCH Pitfall
 * 2) — this is the SAN/UCI trap, and it has a dedicated regression test.
 *
 * Strict equality (not an es-loss band) is deliberate and fails safe: the
 * backend searched deeper than the live grading run, so on disagreement we
 * lose a rare gem rather than invent one. Missing a rare gem is the right
 * way to be wrong (D-04).
 */
export function selectSweepCandidates(
  moves: string[],
  evalSeries: EvalPoint[],
  openingPlyCount: number,
  fenAtPly: (i: number) => string | null,
): SweepCandidate[] {
  const candidates: SweepCandidate[] = [];
  for (let i = 0; i < moves.length; i++) {
    // D-04/D-06/D-08: book plies never enter the cascade — a memorized
    // theory move has low Maia probability at low ratings, so C1 alone
    // cannot distinguish preparation from insight.
    if (i < openingPlyCount) continue;

    const point = evalSeries[i];
    const playedSan = moves[i];
    if (point == null || playedSan === undefined) continue; // noUncheckedIndexedAccess — skip, don't throw
    if (point.best_move === null) continue;

    const parentFen = fenAtPly(i);
    if (parentFen === null) continue;

    const playedUci = sanToUci(parentFen, playedSan);
    if (playedUci === null || playedUci !== point.best_move) continue; // strict, fails safe (D-04)

    candidates.push({ plyIndex: i, parentFen, playedSan });
  }
  return candidates; // already ascending ply order — the loop walks forward
}

/**
 * CR-01 gem-marker precedence (Phase 172, SEED-106). The live per-node
 * resolution (`gemByNode`) is AUTHORITATIVE whenever it has graded a node —
 * INCLUDING an explicit `null` "graded, not a gem" verdict — and the background
 * sweep (`gemByPly`) is a FALLBACK, consulted ONLY when the live path has no
 * entry for that node. A `gemByNode.get(id) ?? gemByPly.get(ply)` collapse
 * cannot express this (`null ?? x === x`), which let the sweep's shallower grade
 * silently overrule a deeper live rejection and paint a gem badge on a move the
 * live search explicitly rejected. Pure and generic so both Analysis.tsx's
 * `GemDetail` and useGemSweep's structurally identical `SweepGemDetail` flow
 * through unchanged, and so the precedence has a revert-and-fail-red unit test
 * instead of living only inside a page component's closure. Returns `null` for
 * both "absent" and "rejected" — the single caller only needs "is there a gem
 * to render here"; a `ply < 0` node (off the mainline) has no sweep entry.
 */
export function resolveGemVerdict<K, T>(
  gemByNode: ReadonlyMap<K, T | null>,
  gemByPly: ReadonlyMap<number, T | null>,
  nodeId: K,
  ply: number,
): T | null {
  if (gemByNode.has(nodeId)) return gemByNode.get(nodeId) ?? null;
  if (ply >= 0) return gemByPly.get(ply) ?? null;
  return null;
}

/** Inputs the D-05 scheduler decision reads to decide whether to dispatch. */
export interface SweepDispatchInput {
  /** All candidates that survived the free prefilter for this game, ascending ply order. */
  candidates: SweepCandidate[];
  /** Plies already resolved (gem or confirmed-miss) by a prior cascade pass. */
  resolvedPlyIndices: ReadonlySet<number>;
  /** The candidate currently mid-flight through the cheap/expensive cascade, if any. */
  inFlight: SweepCandidate | null;
  /** True while the live free-run / grading engines are busy on the user's current node. */
  liveBusy: boolean;
  /** True while the browser tab is hidden (backgrounded). */
  tabHidden: boolean;
  /** Sweep on/off switch (e.g. unanalyzed game, feature disabled). */
  enabled: boolean;
}

export type SweepDispatch =
  | { kind: 'idle' }
  | { kind: 'done' }
  | { kind: 'dispatch'; candidate: SweepCandidate };

/**
 * D-05 yield-to-cursor scheduler decision. Pure function — no state, no
 * side effects — so the invariant that the live position always wins can be
 * proven with a plain unit test instead of mocking a Worker or a hook.
 *
 * Guard order is deliberate: `liveBusy` is checked FIRST, before any
 * candidate selection — the sweep must yield even when unresolved
 * candidates exist and nothing is in flight. This is the yield-to-cursor
 * invariant in its purest, most revertible form (see the `liveBusy` test in
 * `__tests__/gemSweep.test.ts`, which is written to go red if this guard is
 * ever removed).
 */
export function nextSweepDispatch(input: SweepDispatchInput): SweepDispatch {
  const { candidates, resolvedPlyIndices, inFlight, liveBusy, tabHidden, enabled } = input;

  // D-05: the live position always wins. Checked before anything else.
  if (liveBusy) return { kind: 'idle' };
  if (tabHidden || !enabled) return { kind: 'idle' };
  if (inFlight !== null) return { kind: 'idle' }; // one candidate at a time

  const next = candidates.find((c) => !resolvedPlyIndices.has(c.plyIndex));
  if (next === undefined) {
    // All candidates resolved — but only truly "done" once nothing is in
    // flight, which the inFlight check above already guarantees by this point.
    return { kind: 'done' };
  }
  return { kind: 'dispatch', candidate: next };
}
