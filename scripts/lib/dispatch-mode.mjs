#!/usr/bin/env node
/**
 * dispatch-mode.mjs — the harness side of Phase 227's `dispatchMode` flag
 * (D-13/D-14) and the guard against a label-only dispatch mode.
 *
 * Phase 198 lesson: a `--dispatch-mode` option that only changes a label in the
 * output, not a code path, lets a harness run report one mode while measuring
 * another. `probeDispatchMode` makes that impossible: it runs the REAL
 * `mctsSearch` (passed in by the caller) against mock providers whose grade
 * promises it controls, and OBSERVES whether the engine dispatched a new
 * expansion before every in-flight expansion settled. That is the defining
 * behavioral difference between the two loops:
 *
 *   round       — a barrier: no new dispatch until the whole round settled.
 *   continuous  — a new dispatch as soon as any one expansion settles.
 *
 * Every gate script calls `assertDispatchModeLive` at startup; a requested mode
 * the engine did not actually execute exits non-zero before any measurement.
 * (Before Plan 227-10 landed the continuous loop, requesting continuous exited 3.)
 *
 * Usage: node --import ./scripts/lib/frontend-alias-hook.mjs <script.mjs>
 * (the `@/` import below needs the alias hook).
 */
import { FLAWCHESS_DISPATCH_MODE } from '@/lib/engine/botBudget';

import { resolveFrontendModule } from './node-engine-providers.mjs';

/** The two dispatch modes `SearchBudget.dispatchMode` accepts (never a bare string). */
export const DISPATCH_MODES = Object.freeze(['round', 'continuous']);

/** Exit code when continuous is requested but the engine ran the round loop. */
export const DISPATCH_MODE_NOT_LIVE_EXIT = 3;

/** Exit code for every other dispatch-mode failure (bad flag, probe shape, reverse mismatch). */
const DISPATCH_MODE_ERROR_EXIT = 1;

/** Probe node budget: large enough that the budget never bounds the observed dispatch pattern. */
export const PROBE_MAX_NODES = 6;
/** Probe search depth cap (plies). */
const PROBE_MAX_PLIES = 3;
/** Probe in-flight concurrency: two slots so one can settle while the other stays in flight. */
export const PROBE_CONCURRENCY = 2;
/** Probe candidate count per expansion (the first N legal moves in UCI order). */
export const PROBE_POLICY_WIDTH = 3;
/** Macrotask turns to let promise chains drain before observing the grade-call count. */
export const PROBE_SETTLE_TURNS = 5;

/** Neutral ELO the probe searches at (color-keyed, same for both sides). */
const PROBE_ELO = 1500;

/** Fixed policy probabilities over the probe's candidates (sum to 1). */
const PROBE_POLICY_PROBS = [0.5, 0.3, 0.2];

/** Spacing between the mock grades' centipawn values so grades differ per candidate. */
const PROBE_EVAL_CP_STEP = 25;

/** Standard chess start position FEN (probe root). */
const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Fixed messages: no interpolated variables (Sentry-grouping rule extends to harness errors). */
export const DISPATCH_MODE_NOT_LIVE_MESSAGE =
  'CONTINUOUS-NOT-IMPLEMENTED: dispatchMode "continuous" was requested but mctsSearch ran the round barrier loop';
export const DISPATCH_PROBE_UNEXPECTED_MESSAGE =
  'DISPATCH-PROBE-UNEXPECTED: the probe did not observe the expected grade-call sequence, so the dispatch mode cannot be trusted';
const DISPATCH_MODE_MISMATCH_MESSAGE =
  'DISPATCH-MODE-MISMATCH: dispatchMode "round" was requested but mctsSearch dispatched continuously';
const DISPATCH_MODE_BAD_FLAG_MESSAGE = 'Invalid dispatch mode: expected exactly "round" or "continuous"';

/** Build an Error carrying the process exit code the calling gate script should use. */
function exitError(message, exitCode) {
  const err = new Error(message);
  err.exitCode = exitCode;
  return err;
}

/** Parse a `--mode` / `--dispatch-mode` flag value: exactly the two literals, else a fixed-message throw. */
export function parseDispatchModeFlag(value) {
  if (value === 'round' || value === 'continuous') return value;
  throw exitError(DISPATCH_MODE_BAD_FLAG_MESSAGE, DISPATCH_MODE_ERROR_EXIT);
}

/** The shipped mode: the app's single constant (app == harness), never a hard-coded literal. */
export function defaultDispatchMode() {
  return FLAWCHESS_DISPATCH_MODE;
}

/** Let promise chains drain: `turns` macrotasks (setImmediate runs after all microtasks). */
async function settleTurns(turns) {
  for (let i = 0; i < turns; i += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

/** First `PROBE_POLICY_WIDTH` legal moves of `fen` in UCI order, as a fixed 0.5/0.3/0.2 distribution. */
function makeProbePolicy(Chess) {
  return async (fen) => {
    const ucis = new Chess(fen)
      .moves({ verbose: true })
      .map((m) => `${m.from}${m.to}${m.promotion ?? ''}`)
      .sort()
      .slice(0, PROBE_POLICY_WIDTH);
    const dist = {};
    ucis.forEach((uci, i) => {
      dist[uci] = PROBE_POLICY_PROBS[i] ?? 0;
    });
    return dist;
  };
}

/** MoveGrade-shaped values, one per candidate, distinct per candidate index. */
function makeProbeGrades(candidateUcis) {
  const map = new Map();
  candidateUcis.forEach((uci, i) => {
    map.set(uci, { evalCp: i * PROBE_EVAL_CP_STEP, evalMate: null, depth: 10 });
  });
  return map;
}

/**
 * Grade provider whose every call returns a promise the probe settles by hand,
 * recorded in call order. `autoResolve()` settles every pending and every
 * future call immediately (drains the search once the observation is made).
 */
function makeDeferredGrader() {
  const calls = [];
  let auto = false;
  const grade = (fen, candidateUcis) =>
    new Promise((resolve) => {
      const call = { candidateUcis: [...candidateUcis], resolve, settled: false };
      calls.push(call);
      if (auto) {
        call.settled = true;
        resolve(makeProbeGrades(call.candidateUcis));
      }
    });
  const settle = (index) => {
    const call = calls[index];
    if (call === undefined || call.settled) return;
    call.settled = true;
    call.resolve(makeProbeGrades(call.candidateUcis));
  };
  const autoResolve = () => {
    auto = true;
    for (let i = 0; i < calls.length; i += 1) settle(i);
  };
  const settledCount = () => calls.filter((c) => c.settled).length;
  return { grade, calls, settle, autoResolve, settledCount };
}

/**
 * Run `search` (the real `mctsSearch`) with `dispatchMode: mode` against deferred
 * mock grades and report which dispatch behavior it actually executed.
 *
 * Sequence: the root expansion grades first (round 1 is always the root alone);
 * settle it, after which the engine fills `PROBE_CONCURRENCY` slots, so exactly
 * `1 + PROBE_CONCURRENCY` grade calls are recorded. Settle ONLY the second call
 * (one of the two in-flight expansions). A further grade call means the engine
 * dispatched before the other in-flight expansion settled: `'continuous'`. No
 * further call means it held the barrier: `'round'`.
 *
 * @returns {Promise<'round' | 'continuous'>}
 */
export async function probeDispatchMode(search, mode) {
  const { Chess } = await resolveFrontendModule('chess.js');
  const grader = makeDeferredGrader();
  const providers = { policy: makeProbePolicy(Chess), grade: grader.grade };
  const budget = {
    maxNodes: PROBE_MAX_NODES,
    maxPlies: PROBE_MAX_PLIES,
    concurrency: PROBE_CONCURRENCY,
    elo: { w: PROBE_ELO, b: PROBE_ELO },
    dispatchMode: mode,
  };
  const abort = new AbortController();
  const searchDone = search(START_FEN, budget, providers, () => {}, abort.signal);
  try {
    await settleTurns(PROBE_SETTLE_TURNS);
    if (grader.calls.length !== 1) throw exitError(DISPATCH_PROBE_UNEXPECTED_MESSAGE, DISPATCH_MODE_ERROR_EXIT);
    grader.settle(0); // root grade
    await settleTurns(PROBE_SETTLE_TURNS);
    if (grader.calls.length !== 1 + PROBE_CONCURRENCY) {
      throw exitError(DISPATCH_PROBE_UNEXPECTED_MESSAGE, DISPATCH_MODE_ERROR_EXIT);
    }
    grader.settle(1); // ONE of the two in-flight expansions; the other stays pending
    await settleTurns(PROBE_SETTLE_TURNS);
    // The probe must really have settled the root and exactly one in-flight
    // expansion; a probe edited to skip the settle would otherwise read "round"
    // for ANY engine, which is the label-only failure this module exists to stop.
    if (grader.settledCount() !== 2) throw exitError(DISPATCH_PROBE_UNEXPECTED_MESSAGE, DISPATCH_MODE_ERROR_EXIT);
    const observed = grader.calls.length > 1 + PROBE_CONCURRENCY ? 'continuous' : 'round';
    grader.autoResolve();
    await searchDone;
    return observed;
  } catch (err) {
    // Drain the dangling search so a probe failure never leaves a pending run.
    abort.abort();
    grader.autoResolve();
    await searchDone.catch(() => {});
    throw err;
  }
}

/**
 * Throw (carrying `exitCode`) unless `search` really ran the requested `mode`.
 * Every harness gate script calls this at startup.
 */
export async function assertDispatchModeLive(search, mode) {
  const observed = await probeDispatchMode(search, mode);
  if (mode === 'continuous' && observed === 'round') {
    throw exitError(DISPATCH_MODE_NOT_LIVE_MESSAGE, DISPATCH_MODE_NOT_LIVE_EXIT);
  }
  if (mode === 'round' && observed === 'continuous') {
    throw exitError(DISPATCH_MODE_MISMATCH_MESSAGE, DISPATCH_MODE_ERROR_EXIT);
  }
  return observed;
}
