#!/usr/bin/env node
/**
 * stockfish-pool.check.mjs — fast real-engine check of `stockfish-pool.mjs`'s
 * pool features (Phase 226 Plan 01).
 *
 * Real Stockfish processes, no Maia/ONNX — this is a fast structural check
 * (a handful of grade() calls on a small pool), not a calibration harness.
 * Every section spawns its own pool and ALWAYS `quitAll()`s it in a
 * `finally`, so a failed assertion never leaks a live child process.
 *
 * Default section (Phase 226 Plan 01 Task 1, D-03; Task 2, D-18) on a fixed
 * middlegame FEN with a handful of legal candidates —
 *   (a) a default pool sends exactly one `setoption name Clear Hash` per grade()
 *   (b) a `clearHash: false` pool sends zero such lines over two grade() calls
 *   (c) `freeCount()` equals the pool size when idle
 *   (d) `gradeRoot` with one candidate equals `grade`, `rootSplitStats().splits` stays 0
 *   (e) a size-1 pool: `gradeRoot` with 4 candidates equals `grade` (k=1, no rootSplit import)
 *   (f) `makeNodeProviders` without `gradeRootFn` has no `gradeRoot` key; with it, the key IS that function
 *
 * `abort` section (Phase 227 D-09/N-2, runs in the default invocation) — the Node pool honors the
 * grade signal the way the browser WorkerPool does:
 *   (g) a pre-aborted grade resolves an empty Map and no `go` is ever sent
 *   (h) a request queued behind a busy size-1 pool and then aborted resolves empty at once, leaves
 *       the waiter list, and the busy request still completes with its own correct grade
 *   (i) an in-flight long search aborted mid-way sends `stop`, settles empty within
 *       ABORT_SETTLE_MAX_MS, whenIdle() resolves within WHEN_IDLE_MAX_MS, and a following grade on
 *       the same pool is correct
 *   (j) one AbortSignal reused across LISTENER_REUSE_COUNT completed grades holds no abort listener
 *   (k) a fanned-out gradeRoot aborted mid-search resolves an empty Map (L-2, never a partial merge)
 *
 * `--root-split` section (Task 2, D-18/D-08): on a size-4 Clear-Hash pool with
 * >= 8 legal candidates, `gradeRoot`'s result matches a manual round-robin
 * merge of per-shard `grade` calls, `splits` is 1, `premiseViolations` is 0.
 * Before Plan 226-10 lands `frontend/src/lib/engine/rootSplit.ts`, this
 * EXPECTEDLY exits 3 with `ROOT_SPLIT_ABSENT_MESSAGE` — that is the passing
 * outcome for every arm A0..A21; exit 0 only becomes the passing outcome
 * from A21S on.
 *
 * Run via:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/stockfish-pool.check.mjs --root-split
 */
import { getEventListeners } from 'node:events';

import { createStockfishPool, ROOT_SPLIT_MODULE_SPECIFIER, ROOT_SPLIT_ABSENT_MESSAGE } from './stockfish-pool.mjs';
import { makeNodeProviders } from './calibration-providers.mjs';
import { resolveFrontendModule } from './node-engine-providers.mjs';
import { OPENING_BOOK } from './calibration-openings.mjs';

/** Grading depth used by every section below — shallow, fast, deterministic under Clear Hash. */
const CHECK_GRADING_DEPTH = 10;

/** Number of legal moves taken as candidates for the default section's grade() calls. */
const CHECK_CANDIDATE_COUNT = 4;

/** Pool size for the default section — exercises real acquire/release across more than one engine. */
const CHECK_POOL_SIZE = 2;

/** Pool size for the `--root-split` section — must be > `ROOT_SPLIT_MIN_CANDIDATES`'s implied k to actually fan out. */
const ROOT_SPLIT_POOL_SIZE = 4;

/** Minimum legal candidates required for the `--root-split` section's position. */
const ROOT_SPLIT_MIN_CANDIDATES = 8;

/** Depth of the deliberately unfinishable search the abort section interrupts (never reached within the check). */
const ABORT_LONG_DEPTH = 30;

/** Max wall time (ms) between `abort()` and the aborted caller settling (the browser settles synchronously). */
const ABORT_SETTLE_MAX_MS = 500;

/** Max wall time (ms) between `abort()` and `whenIdle()` resolving (stop -> bestmove round trip plus release). */
const WHEN_IDLE_MAX_MS = 2_000;

/** Completed grades sharing ONE AbortSignal in the listener-hygiene case (mctsSearch threads one signal per search). */
const LISTENER_REUSE_COUNT = 20;

/** Settle time (ms) given to a `go` before the in-flight abort, so the search is genuinely running. */
const ABORT_AFTER_GO_MS = 200;

/** Exact UCI command `nodeGrade` sends to clear the transposition table (calibration-providers.mjs). */
const CLEAR_HASH_COMMAND = 'setoption name Clear Hash';

/** A known-legal, reachable middlegame-ish FEN (Italian Game) — reused from the harness's own opening book. */
const CHECK_FEN = OPENING_BOOK[0].fen;

/** Converts a chess.js verbose move object to a UCI string (`from` + `to` + optional `promotion`). */
function toUci(move) {
  return `${move.from}${move.to}${move.promotion ?? ''}`;
}

/** Deep-compares two `Map<string, MoveGrade>` results field-by-field (never reference/identity). */
function gradesEqual(a, b) {
  if (a.size !== b.size) return false;
  for (const [uci, grade] of a) {
    const other = b.get(uci);
    if (other === undefined) return false;
    if (grade.evalCp !== other.evalCp || grade.evalMate !== other.evalMate || grade.depth !== other.depth) {
      return false;
    }
  }
  return true;
}

/** Runs the default section: (a) Clear-Hash-per-grade, (b) clearHash:false skips it, (c) freeCount() at idle. */
async function runDefaultSection(candidateUcis) {
  let ok = true;
  const check = (cond, label) => {
    if (cond) {
      console.log(`PASS: ${label}`);
    } else {
      console.error(`FAIL: ${label}`);
      ok = false;
    }
  };

  // (a) + (c): a default (Clear-Hash) pool.
  let poolA;
  try {
    const sentLinesA = [];
    poolA = await createStockfishPool({
      size: CHECK_POOL_SIZE,
      sendObserver: (command) => sentLinesA.push(command),
    });
    await poolA.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    const clearHashCount = sentLinesA.filter((line) => line === CLEAR_HASH_COMMAND).length;
    check(
      clearHashCount === 1,
      `(a) default pool sends exactly one "${CLEAR_HASH_COMMAND}" per grade() call (got ${clearHashCount})`,
    );
    check(
      poolA.freeCount() === CHECK_POOL_SIZE,
      `(c) freeCount() equals pool size (${CHECK_POOL_SIZE}) when idle (got ${poolA.freeCount()})`,
    );
  } finally {
    poolA?.quitAll();
  }

  // (b) a clearHash:false pool, over two grade() calls.
  let poolB;
  try {
    const sentLinesB = [];
    poolB = await createStockfishPool({
      size: CHECK_POOL_SIZE,
      clearHash: false,
      sendObserver: (command) => sentLinesB.push(command),
    });
    await poolB.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    await poolB.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    const clearHashCountB = sentLinesB.filter((line) => line === CLEAR_HASH_COMMAND).length;
    check(
      clearHashCountB === 0,
      `(b) clearHash:false pool sends zero "${CLEAR_HASH_COMMAND}" lines over two grade() calls (got ${clearHashCountB})`,
    );
  } finally {
    poolB?.quitAll();
  }

  // (d) gradeRoot with ONE candidate must equal grade (k<=1 OR a single
  // candidate always takes the plain, undivided path — splits stays 0).
  let poolD;
  try {
    poolD = await createStockfishPool({ size: CHECK_POOL_SIZE });
    const singleCandidate = [candidateUcis[0]];
    const gradeResult = await poolD.grade(CHECK_FEN, singleCandidate, undefined, CHECK_GRADING_DEPTH);
    const rootResult = await poolD.gradeRoot(CHECK_FEN, singleCandidate, undefined, CHECK_GRADING_DEPTH);
    check(gradesEqual(gradeResult, rootResult), '(d) gradeRoot with one candidate equals grade');
    check(
      poolD.rootSplitStats().splits === 0,
      `(d) rootSplitStats().splits stays 0 for a one-candidate gradeRoot (got ${poolD.rootSplitStats().splits})`,
    );
  } finally {
    poolD?.quitAll();
  }

  // (e) a size-1 pool: gradeRoot with 4 candidates equals grade (k=1 — never
  // imports the rootSplit module, so this passes even before Plan 226-10).
  let poolE;
  try {
    poolE = await createStockfishPool({ size: 1 });
    const gradeResultE = await poolE.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    const rootResultE = await poolE.gradeRoot(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    check(gradesEqual(gradeResultE, rootResultE), '(e) size-1 pool: gradeRoot with 4 candidates equals grade (k=1)');
    check(
      poolE.rootSplitStats().splits === 0,
      `(e) size-1 pool gradeRoot never increments splits (got ${poolE.rootSplitStats().splits})`,
    );
  } finally {
    poolE?.quitAll();
  }

  // (f) makeNodeProviders's conditional gradeRoot key (no live engines needed).
  const noopGrade = () => {};
  const providersWithout = makeNodeProviders({}, {}, noopGrade);
  check('gradeRoot' in providersWithout === false, '(f) makeNodeProviders without gradeRootFn has no gradeRoot key');
  const fakeGradeRootFn = () => {};
  const providersWith = makeNodeProviders({}, {}, noopGrade, { gradeRootFn: fakeGradeRootFn });
  check(
    'gradeRoot' in providersWith && providersWith.gradeRoot === fakeGradeRootFn,
    '(f) makeNodeProviders with gradeRootFn exposes it verbatim as gradeRoot',
  );

  return ok;
}

/** Resolves `{ timedOut: false, value }` when `promise` settles within `ms`, else `{ timedOut: true }`. */
async function settleWithin(promise, ms) {
  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => resolve({ timedOut: true }), ms);
  });
  try {
    return await Promise.race([promise.then((value) => ({ timedOut: false, value })), timeout]);
  } finally {
    clearTimeout(timer);
  }
}

/** `pool.whenIdle()` when the pool has it; otherwise polls `freeCount()` so a pool without it FAILS the bound instead of throwing. */
function idlePromise(pool, size) {
  if (typeof pool.whenIdle === 'function') return pool.whenIdle();
  return new Promise((resolve) => {
    const poll = setInterval(() => {
      if (pool.freeCount() === size) {
        clearInterval(poll);
        resolve();
      }
    }, 20);
  });
}

/** Lines the send observer saw that start a search (`go ...`). */
const goLines = (sent) => sent.filter((line) => line.startsWith('go '));

/** Phase 227 N-2 `abort` section: see the file header for the four behaviors. */
async function runAbortSection(candidateUcis, rootCandidateUcis) {
  let ok = true;
  const check = (cond, label) => {
    if (cond) {
      console.log(`PASS: ${label}`);
    } else {
      console.error(`FAIL: ${label}`);
      ok = false;
    }
  };

  // Reference grade (no signal) every case below compares against; Clear Hash makes it reproducible.
  let referencePool;
  let reference;
  try {
    referencePool = await createStockfishPool({ size: 1 });
    reference = await referencePool.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
  } finally {
    referencePool?.quitAll();
  }

  // (g) a pre-aborted signal never reaches an engine.
  let poolG;
  try {
    const sent = [];
    poolG = await createStockfishPool({ size: 1, sendObserver: (command) => sent.push(command) });
    const controller = new AbortController();
    controller.abort();
    const result = await poolG.grade(CHECK_FEN, candidateUcis, controller.signal, CHECK_GRADING_DEPTH);
    check(result instanceof Map && result.size === 0, `(g) pre-aborted grade resolves an empty Map (got size ${result?.size})`);
    check(goLines(sent).length === 0, `(g) pre-aborted grade sends no "go" (got ${goLines(sent).length})`);
    check(poolG.freeCount() === 1, '(g) pre-aborted grade leaves the engine free');
  } finally {
    poolG?.quitAll();
  }

  // (h) queued request aborted while the only engine is busy with another request.
  let poolH;
  try {
    const sent = [];
    poolH = await createStockfishPool({ size: 1, sendObserver: (command) => sent.push(command) });
    const busy = poolH.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
    const controller = new AbortController();
    const queued = poolH.grade(CHECK_FEN, candidateUcis, controller.signal, CHECK_GRADING_DEPTH);
    const queuedCountBefore = typeof poolH.queuedCount === 'function' ? poolH.queuedCount() : -1;
    check(queuedCountBefore === 1, `(h) the second request waits in the pool queue before the abort (queuedCount ${queuedCountBefore})`);
    controller.abort();
    const queuedOutcome = await settleWithin(queued, ABORT_SETTLE_MAX_MS);
    check(
      !queuedOutcome.timedOut && queuedOutcome.value.size === 0,
      `(h) queued request aborted resolves an empty Map within ${ABORT_SETTLE_MAX_MS} ms (timedOut=${queuedOutcome.timedOut})`,
    );
    const queuedCountAfter = typeof poolH.queuedCount === 'function' ? poolH.queuedCount() : -1;
    check(queuedCountAfter === 0, `(h) aborted request left the waiter list (queuedCount ${queuedCountAfter})`);
    const busyResult = await busy;
    check(gradesEqual(busyResult, reference), '(h) the busy request still completes with its own correct grade');
    check(goLines(sent).length === 1, `(h) the aborted queued request never sent a "go" (got ${goLines(sent).length})`);
    const idle = await settleWithin(idlePromise(poolH, 1), WHEN_IDLE_MAX_MS);
    check(!idle.timedOut && poolH.freeCount() === 1, '(h) the engine is free again after the busy request completes');
  } finally {
    poolH?.quitAll();
  }

  // (i) in-flight long search aborted mid-way.
  let poolI;
  try {
    const sent = [];
    poolI = await createStockfishPool({ size: 1, sendObserver: (command) => sent.push(command) });
    const controller = new AbortController();
    const longGrade = poolI.grade(CHECK_FEN, candidateUcis, controller.signal, ABORT_LONG_DEPTH);
    await new Promise((resolve) => setTimeout(resolve, ABORT_AFTER_GO_MS));
    check(goLines(sent).length === 1, `(i) the long search is running before the abort (got ${goLines(sent).length} "go")`);
    const abortedAt = performance.now();
    controller.abort();
    const outcome = await settleWithin(longGrade, ABORT_SETTLE_MAX_MS);
    check(
      !outcome.timedOut && outcome.value.size === 0,
      `(i) aborted in-flight grade settles an empty Map within ${ABORT_SETTLE_MAX_MS} ms (timedOut=${outcome.timedOut})`,
    );
    check(sent.includes('stop'), '(i) abort sends "stop" to the searching engine');
    const idle = await settleWithin(idlePromise(poolI, 1), WHEN_IDLE_MAX_MS);
    const idleMs = performance.now() - abortedAt;
    check(!idle.timedOut, `(i) whenIdle() resolves within ${WHEN_IDLE_MAX_MS} ms of the abort (${idleMs.toFixed(0)} ms, timedOut=${idle.timedOut})`);
    if (!idle.timedOut) {
      const followUp = await poolI.grade(CHECK_FEN, candidateUcis, undefined, CHECK_GRADING_DEPTH);
      check(followUp.size > 0 && gradesEqual(followUp, reference), '(i) a grade after the abort on the same pool is correct and non-empty');
    }
  } finally {
    poolI?.quitAll();
  }

  // (j) listener hygiene: one signal across many completed grades must not accumulate abort listeners.
  let poolJ;
  try {
    poolJ = await createStockfishPool({ size: 1 });
    const controller = new AbortController();
    for (let i = 0; i < LISTENER_REUSE_COUNT; i++) {
      await poolJ.grade(CHECK_FEN, [candidateUcis[0]], controller.signal, CHECK_GRADING_DEPTH);
    }
    const remaining = getEventListeners(controller.signal, 'abort').length;
    check(remaining === 0, `(j) one AbortSignal across ${LISTENER_REUSE_COUNT} completed grades holds no abort listener (got ${remaining})`);
  } finally {
    poolJ?.quitAll();
  }

  // (k) L-2: a fanned-out gradeRoot aborted mid-search resolves empty, never a partial merge.
  let poolK;
  try {
    poolK = await createStockfishPool({ size: ROOT_SPLIT_POOL_SIZE });
    const controller = new AbortController();
    const rootGrade = poolK.gradeRoot(CHECK_FEN, rootCandidateUcis, controller.signal, ABORT_LONG_DEPTH);
    await new Promise((resolve) => setTimeout(resolve, ABORT_AFTER_GO_MS));
    controller.abort();
    const outcome = await settleWithin(rootGrade, ABORT_SETTLE_MAX_MS);
    check(
      !outcome.timedOut && outcome.value.size === 0,
      `(k) aborted gradeRoot resolves an empty Map within ${ABORT_SETTLE_MAX_MS} ms (timedOut=${outcome.timedOut})`,
    );
    const idle = await settleWithin(idlePromise(poolK, ROOT_SPLIT_POOL_SIZE), WHEN_IDLE_MAX_MS);
    check(!idle.timedOut, `(k) whenIdle() resolves within ${WHEN_IDLE_MAX_MS} ms after an aborted gradeRoot (timedOut=${idle.timedOut})`);
  } finally {
    poolK?.quitAll();
  }

  return ok;
}

/**
 * `--root-split` section: on a size-4 Clear-Hash pool with >= 8 legal
 * candidates, verifies `gradeRoot`'s result structurally and against a
 * manual round-robin merge of per-shard `grade` calls, built from the SAME
 * `partitionCandidates`/`mergeShardGrades`/`ROOT_SPLIT_MAX_SHARDS` the pool
 * itself would use — never a hand-rolled reimplementation that could drift
 * from the real partitioning scheme. Before Plan 226-10 lands
 * `frontend/src/lib/engine/rootSplit.ts`, `gradeRoot` itself throws
 * `ROOT_SPLIT_ABSENT_MESSAGE` and this function exits the WHOLE process with
 * code 3 — the expected, PASSING outcome for arms A0..A21 (never a "FAIL:").
 */
async function runRootSplitSection(rootCandidateUcis) {
  let ok = true;
  const check = (cond, label) => {
    if (cond) {
      console.log(`PASS: ${label}`);
    } else {
      console.error(`FAIL: ${label}`);
      ok = false;
    }
  };

  let pool;
  try {
    pool = await createStockfishPool({ size: ROOT_SPLIT_POOL_SIZE });

    let rootResult;
    try {
      rootResult = await pool.gradeRoot(CHECK_FEN, rootCandidateUcis, undefined, CHECK_GRADING_DEPTH);
    } catch (err) {
      if (err instanceof Error && err.message === ROOT_SPLIT_ABSENT_MESSAGE) {
        console.log(`ROOT-SPLIT: ${err.message}`);
        pool.quitAll();
        process.exit(3); // expected pre-A21S outcome — never treated as a check failure
      }
      throw err;
    }

    // Module present (A21S) — verify structure + a manual round-robin merge
    // built from the SAME partition/merge helpers the pool itself used.
    const keysMatch =
      rootResult.size === rootCandidateUcis.length && rootCandidateUcis.every((uci) => rootResult.has(uci));
    check(keysMatch, '--root-split: gradeRoot result key set equals the candidate set');

    const { partitionCandidates, mergeShardGrades, ROOT_SPLIT_MAX_SHARDS } = await import(ROOT_SPLIT_MODULE_SPECIFIER);
    const k = Math.min(pool.freeCount(), ROOT_SPLIT_MAX_SHARDS);
    const shards = partitionCandidates(rootCandidateUcis, k);
    const perShardGrades = await Promise.all(
      shards.map((shard) => pool.grade(CHECK_FEN, shard, undefined, CHECK_GRADING_DEPTH)),
    );
    const manualMerge = mergeShardGrades(rootCandidateUcis, perShardGrades);
    check(
      gradesEqual(rootResult, manualMerge),
      '--root-split: gradeRoot equals a manual round-robin merge of per-shard grade calls (bit-identical under Clear Hash)',
    );

    const stats = pool.rootSplitStats();
    check(stats.splits === 1, `--root-split: rootSplitStats().splits is 1 (got ${stats.splits})`);
    check(
      stats.premiseViolations === 0,
      `--root-split: rootSplitStats().premiseViolations is 0 (got ${stats.premiseViolations})`,
    );
  } finally {
    pool?.quitAll();
  }

  return ok;
}

async function main() {
  const { Chess } = await resolveFrontendModule('chess.js');
  const chess = new Chess(CHECK_FEN);
  const legalUcis = chess.moves({ verbose: true }).map(toUci);
  if (legalUcis.length < CHECK_CANDIDATE_COUNT) {
    throw new Error(`CHECK_FEN has fewer than ${CHECK_CANDIDATE_COUNT} legal moves — pick a richer position`);
  }
  const candidateUcis = legalUcis.slice(0, CHECK_CANDIDATE_COUNT);

  if (process.argv.includes('--root-split')) {
    if (legalUcis.length < ROOT_SPLIT_MIN_CANDIDATES) {
      throw new Error(`CHECK_FEN has fewer than ${ROOT_SPLIT_MIN_CANDIDATES} legal moves — pick a richer position`);
    }
    const rootCandidateUcis = legalUcis.slice(0, ROOT_SPLIT_MIN_CANDIDATES);
    const ok = await runRootSplitSection(rootCandidateUcis);
    process.exit(ok ? 0 : 1);
  }

  const defaultOk = await runDefaultSection(candidateUcis);
  const abortOk = await runAbortSection(candidateUcis, legalUcis.slice(0, ROOT_SPLIT_MIN_CANDIDATES));
  process.exit(defaultOk && abortOk ? 0 : 1);
}

main().catch((err) => {
  console.error(`FAIL: unexpected error — ${err.stack ?? err}`);
  process.exit(1);
});
