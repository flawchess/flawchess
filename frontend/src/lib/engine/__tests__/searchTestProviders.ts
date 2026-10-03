/**
 * Shared fabricated providers for the mctsSearch test suites (Phase 227-10).
 *
 * `uniformPolicyFromLegalMoves`, `makeFixedPolicy`, `withJitter`, `hashedEvalCp`
 * and `makeVariedGrade` are MOVED verbatim from `mctsSearch.test.ts` so the
 * continuous-dispatch tests (`mctsSearch.continuous.test.ts`) reuse the exact
 * same fixtures the round-mode suites use. The remaining helpers are new in
 * Phase 227-10: `deferred` and `makeControlledGrade` (hand-settled provider
 * promises for ordering control), `settlesWithin` (a bounded wait, so a hang
 * fails an assertion instead of timing the whole test out), and the peaked /
 * chain policies whose shapes exercise `selectPath`'s per-fill block logic.
 */

import { Chess } from 'chess.js';
import type { EngineProviders, MoveGrade, Side } from '../types';

export interface PolicyCall {
  fen: string;
  elo: number;
  side: Side;
}

/** Uniform distribution over chess.js's OWN legal-move list at `fen` — never hand-enumerated. */
export function uniformPolicyFromLegalMoves(fen: string): Record<string, number> {
  const chess = new Chess(fen);
  const moves = chess.moves({ verbose: true });
  const ucis = moves.map((m) => `${m.from}${m.to}${m.promotion ?? ''}`);
  const weight = ucis.length > 0 ? 1 / ucis.length : 0;
  const dist: Record<string, number> = {};
  for (const uci of ucis) dist[uci] = weight;
  return dist;
}

/**
 * A fabricated `policy()`: returns `byFen[fen]` when explicitly configured,
 * else falls back to a uniform distribution over chess.js's real legal moves
 * (so deeper/unconfigured tree nodes always receive a legal distribution).
 * Records every call when `calls` is provided (ENGINE-04 oracle / ENGINE-02
 * dropped-tail assertions).
 */
export function makeFixedPolicy(
  byFen: Record<string, Record<string, number>>,
  calls?: PolicyCall[],
): EngineProviders['policy'] {
  return async (fen, elo, side) => {
    calls?.push({ fen, elo, side });
    return byFen[fen] ?? uniformPolicyFromLegalMoves(fen);
  };
}

/** Wraps an async fabricated provider fn with an artificial, deliberately jittered resolution delay. */
export function withJitter<Args extends unknown[], Result>(
  fn: (...args: Args) => Promise<Result>,
  jitterMsSequence: number[],
): (...args: Args) => Promise<Result> {
  let callIndex = 0;
  return async (...args: Args) => {
    const idx = callIndex;
    callIndex += 1;
    const delay = jitterMsSequence[idx % jitterMsSequence.length] ?? 0;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return fn(...args);
  };
}

// CR-01 fixture hardening: the original determinism fixtures used uniform
// policies and all-zero grades, pinning every node value at exactly 0.5 —
// structurally unable to detect a selection-order regression (any two search
// trees look identical when every value is 0.5). These constants derive a
// deterministic NON-neutral grade from (fen, uci) so different trees produce
// different outputs.
const GRADE_HASH_MULTIPLIER = 31;
const GRADE_EVAL_CP_SPAN = 300;

/** Deterministic non-neutral cp eval in (-GRADE_EVAL_CP_SPAN, GRADE_EVAL_CP_SPAN) derived from (fen, uci). */
function hashedEvalCp(fen: string, uci: string): number {
  const s = `${fen}|${uci}`;
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (Math.imul(h, GRADE_HASH_MULTIPLIER) + s.charCodeAt(i)) | 0;
  return (Math.abs(h) % (2 * GRADE_EVAL_CP_SPAN)) - GRADE_EVAL_CP_SPAN;
}

/** A fabricated `grade()` returning deterministic, varied (non-0.5-collapsing) grades at every node. */
export function makeVariedGrade(): EngineProviders['grade'] {
  return async (fen, candidateUcis) => {
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      map.set(uci, { evalCp: hashedEvalCp(fen, uci), evalMate: null, depth: 10 });
    }
    return map;
  };
}

// ─── Phase 227-10 additions ──────────────────────────────────────────────────

/** A promise whose settlement the test controls by hand. */
export interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

export function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/** One recorded call into a controlled grade provider. */
export interface ControlledGradeCall {
  fen: string;
  candidateUcis: string[];
  signal: AbortSignal | undefined;
  gradingDepth: number | undefined;
  result: Deferred<Map<string, MoveGrade>>;
}

/**
 * A `grade()` whose every call returns a hand-settled promise, recorded in
 * call order. `settle(i)` resolves call `i` with `makeVariedGrade`-style values
 * (non-0.5, so a wrongly applied result is visible); `settleNeutral(i)`
 * resolves it with all-equal `evalCp: 0` grades (every child ties at 0.5, so a
 * `{ epsilonThreshold: 0 }` stop rule fires at its node floor); `settleEmpty(i)`
 * resolves it with an empty Map (the pool's answer for an aborted request).
 */
export function makeControlledGrade(): {
  grade: EngineProviders['grade'];
  calls: ControlledGradeCall[];
  settle: (index: number) => void;
  settleNeutral: (index: number) => void;
  settleEmpty: (index: number) => void;
} {
  const calls: ControlledGradeCall[] = [];
  const grade = ((fen: string, candidateUcis: string[], signal?: AbortSignal, gradingDepth?: number) => {
    const result = deferred<Map<string, MoveGrade>>();
    calls.push({ fen, candidateUcis: [...candidateUcis], signal, gradingDepth, result });
    return result.promise;
  }) as EngineProviders['grade'];
  const settle = (index: number): void => {
    const call = calls[index];
    if (call === undefined) throw new Error('settle: no such grade call');
    // Resolved synchronously (not through the async `makeVariedGrade`), so settling several calls (or settling one
    // and rejecting another) in one turn gives them identical microtask depth and a deterministic arrival order.
    const map = new Map<string, MoveGrade>();
    for (const uci of call.candidateUcis) {
      map.set(uci, { evalCp: hashedEvalCp(call.fen, uci), evalMate: null, depth: 10 });
    }
    call.result.resolve(map);
  };
  const settleNeutral = (index: number): void => {
    const call = calls[index];
    if (call === undefined) throw new Error('settleNeutral: no such grade call');
    const map = new Map<string, MoveGrade>();
    for (const uci of call.candidateUcis) map.set(uci, { evalCp: 0, evalMate: null, depth: 10 });
    call.result.resolve(map);
  };
  const settleEmpty = (index: number): void => {
    const call = calls[index];
    if (call === undefined) throw new Error('settleEmpty: no such grade call');
    call.result.resolve(new Map<string, MoveGrade>());
  };
  return { grade, calls, settle, settleNeutral, settleEmpty };
}

/** Macrotask turns that let every pending promise chain drain. */
const FLUSH_TURNS = 5;

/** Lets microtask chains (provider promise -> dispatchExpansion -> loop) run to completion. */
export async function flushTurns(turns: number = FLUSH_TURNS): Promise<void> {
  for (let i = 0; i < turns; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

/** Outcome of `settlesWithin`. */
export type Settlement<T> =
  | { state: 'resolved'; value: T }
  | { state: 'rejected'; error: unknown }
  | { state: 'pending' };

/** Default bounded wait: long enough for any microtask chain, short enough that a hang fails fast. */
const SETTLE_WINDOW_MS = 250;

/**
 * Waits up to `ms` for `promise` to settle. A search that hangs (the
 * lost-wakeup failure mode) reports `pending` instead of timing the whole
 * test out, so the assertion names the failure.
 */
export async function settlesWithin<T>(promise: Promise<T>, ms: number = SETTLE_WINDOW_MS): Promise<Settlement<T>> {
  const timeout = new Promise<Settlement<T>>((resolve) => {
    setTimeout(() => resolve({ state: 'pending' }), ms);
  });
  const outcome = promise.then(
    (value): Settlement<T> => ({ state: 'resolved', value }),
    (error: unknown): Settlement<T> => ({ state: 'rejected', error }),
  );
  return Promise.race([outcome, timeout]);
}

/** chess.js's OWN legal-move UCI list at `fen`, sorted ascending — never hand-enumerated. */
function legalUcisSorted(fen: string): string[] {
  const chess = new Chess(fen);
  return chess
    .moves({ verbose: true })
    .map((m) => `${m.from}${m.to}${m.promotion ?? ''}`)
    .sort();
}

/**
 * A `policy()` that gives the first `peaks.length` sorted legal moves the
 * given peak masses and splits the remainder evenly over the rest, so
 * `truncateAndRenormalize`'s ~90% mass cut keeps exactly `peaks.length`
 * candidates. At `rootFen` it returns `rootPeaks` instead (default: uniform
 * over all legal moves, a broad Maia-like root). Used for the "peaked non-root
 * policy" shape (SEED-170 item 2) and for chains that collapse a subtree to a
 * single live child.
 */
export function makePeakedPolicy(
  rootFen: string,
  peaks: number[],
  rootPeaks?: number[],
): EngineProviders['policy'] {
  const shape = (ucis: string[], masses: number[]): Record<string, number> => {
    const peakMass = masses.reduce((sum, p) => sum + p, 0);
    const tailUcis = ucis.slice(masses.length);
    const tailWeight = tailUcis.length > 0 ? Math.max(0, 1 - peakMass) / tailUcis.length : 0;
    const dist: Record<string, number> = {};
    ucis.forEach((uci, i) => {
      const peak = masses[i];
      dist[uci] = peak !== undefined ? peak : tailWeight;
    });
    return dist;
  };
  return async (fen) => {
    const ucis = legalUcisSorted(fen);
    if (fen === rootFen && rootPeaks === undefined) {
      const weight = ucis.length > 0 ? 1 / ucis.length : 0;
      const dist: Record<string, number> = {};
      for (const uci of ucis) dist[uci] = weight;
      return dist;
    }
    return shape(ucis, fen === rootFen && rootPeaks !== undefined ? rootPeaks : peaks);
  };
}

/** Deterministic non-neutral evalCp per uci (char-code sum modulo 201, minus 100) — no randomness, no collapsing to 0.5 everywhere. */
export function makeUciDerivedGrade(): EngineProviders['grade'] {
  const UCI_GRADE_MODULUS = 201;
  const UCI_GRADE_OFFSET = 100;
  return async (_fen, candidateUcis) => {
    const map = new Map<string, MoveGrade>();
    for (const uci of candidateUcis) {
      let charSum = 0;
      for (let i = 0; i < uci.length; i += 1) charSum += uci.charCodeAt(i);
      map.set(uci, { evalCp: (charSum % UCI_GRADE_MODULUS) - UCI_GRADE_OFFSET, evalMate: null, depth: 10 });
    }
    return map;
  };
}
