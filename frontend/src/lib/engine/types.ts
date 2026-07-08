/**
 * types — the frozen public contract of the Phase 153 pure search core.
 *
 * These types are locked for the rest of the v2.0 FlawChess Engine milestone
 * (Phases 154-157 build against them unchanged). Every field cites the
 * decision that fixes its shape:
 *   - D-04: the root-only extra-move union with Maia top-k.
 *   - D-06: `practicalScore`/`RankedLine` are root-side-to-move expected
 *     score (0-1), never a per-node/per-ply-relative value.
 *   - D-07: ELO is color-keyed ({w, b}), never self/opponent-keyed.
 *   - D-08: the engine core speaks UCI everywhere (moves, policy keys,
 *     grade keys, paths) and side-to-move is the FEN 'w'/'b' literal.
 *   - D-09: one node = one expansion event (the unit `maxNodes` counts).
 */

import type { MoveGrade } from '@/lib/moveQuality';

// Re-exported so the engine core has a single import surface for move
// grading — do NOT redeclare a structurally-duplicate interface here.
export type { MoveGrade };

/** FEN side-to-move literal (D-08) — 'w' or 'b', never a full-word color. */
export type Side = 'w' | 'b';

/** Fabricated-in-tests-today, real-workers-in-Phase-154 provider surface. */
export interface EngineProviders {
  /** UCI-keyed Maia move-probability distribution at `elo` for `side` to move (D-08). */
  policy(fen: string, elo: number, side: Side): Promise<Record<string, number>>;
  /** UCI-keyed Stockfish shallow-eval grades for the candidate UCI moves, white-POV cp (D-08). */
  grade(fen: string, candidateUcis: string[]): Promise<Map<string, MoveGrade>>;
}

/** Bounds one `SearchRunner` invocation (ENGINE-06). */
export interface SearchBudget {
  /** D-09: one node = one expansion event; the unit this budget counts. */
  maxNodes: number;
  /** D-07: color-keyed ELO, never self/opponent-keyed. */
  elo: { w: number; b: number };
  /** Locked 6-10 ply band (SEED-082). */
  maxPlies: number;
  /** D-03: in-flight expansion concurrency, >=1. */
  concurrency: number;
  /** D-04: root-only UCI moves unioned with Maia top-k at the root. */
  extraRootMoves?: string[];
  /** Phase 159 D-06/D-07: reshapes the user's-side policy before truncation; omitted/1 = no-op. */
  policyTemperature?: number;
}

/** One ranked root candidate line in an `EngineSnapshot` (D-06/D-08). */
export interface RankedLine {
  /** The root candidate move, UCI (D-08). */
  rootMove: string;
  /** D-06: root-side-to-move expected score, 0-1 — never per-ply-relative. */
  practicalScore: number;
  /** Objective white-POV Stockfish eval (cp) at the modal leaf, if available. */
  objectiveEvalCp: number | null;
  /** The line's most-visited continuation, UCI sequence (D-08). */
  modalPath: string[];
  /** Total expansion visits attributed to this root candidate. */
  visits: number;
}

/** The output a `SearchRunner` reports — both at completion and per `onSnapshot` tick. */
export interface EngineSnapshot {
  rankedLines: RankedLine[];
  /** D-09: count of expansion events consumed so far. */
  nodesEvaluated: number;
  /** True once `SearchBudget.maxNodes`/`maxPlies` stopped the search (not an abort). */
  budgetExhausted: boolean;
}
