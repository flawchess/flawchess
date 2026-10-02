#!/usr/bin/env node
/**
 * engine-root-split-content.mjs — D-16's grade-content bound and projected
 * gain instrument for the root grade split (Phase 226 Plan 06).
 *
 * SEED-171's "+/-20 cp" was measured on two hand-picked positions with
 * cleared hashes only (RESEARCH Pattern 2). This tool re-measures on REAL
 * root candidate sets (captured from a live `mctsSearch` at `maxNodes: 1`,
 * so the candidates are exactly what a real search would grade, never a
 * hand-picked list) under BOTH the Clear-Hash mode (an absolute bound: a
 * single-vs-single comparison under Clear Hash is exactly 0, so any
 * divergence is entirely the split's own content effect) and the shipped
 * warm-hash mode (which also needs its own single-vs-single noise floor,
 * since two differently-warmed engines already disagree before any split —
 * D-03/F-5: the browser sets `Hash` once at `uciok` and never clears it
 * again for the pool's lifetime).
 *
 * Two split sources:
 *   --split-source prototype   Partitions candidates round-robin IN THIS
 *                              TOOL (`prototypeSplit`/`partitionRoundRobin`),
 *                              usable from step 0 onward — `rootSplit.ts`
 *                              does not exist yet (Plan 226-10, arm A21S).
 *   --split-source pool        Calls the harness pool's OWN `gradeRoot`
 *                              (`scripts/lib/stockfish-pool.mjs`) — the real
 *                              implementation this tool re-measures at arm
 *                              A21S. Before A21S, `rootSplit.ts` is absent,
 *                              so this path is EXPECTED to print the
 *                              absent-module message and exit
 *                              `EXIT_MODULE_ABSENT` (3) — never a failure.
 *
 * Warm-mode measurement order (D-16 warm leg, per position, documented here
 * because it is load-bearing and easy to get backwards):
 *   1. `captureRootCandidates` — a throwaway `mctsSearch` at `maxNodes: 1`
 *      whose `grade` wrapper records the candidate list and returns an
 *      EMPTY map (no engine touched, no hash effect).
 *   2. Warm-up — ONE real `mctsSearch` at `WARMUP_NODES`/`WARMUP_CONCURRENCY`
 *      whose grade closure runs through THIS run's warm pool
 *      (`nodeGrade(..., { clearHash: false })` via `pool.run`), so the
 *      engines' transposition tables end up populated the way shipped play
 *      would leave them — never cleared afterward.
 *   3. TWO single grades of the SAME captured candidate set, launched
 *      CONCURRENTLY so they land on two DIFFERENT (differently-warmed)
 *      engines. Their divergence is `noise_mean_abs_des`/`noise_max_abs_des`
 *      — the shipped warm-hash noise floor BEFORE any split exists.
 *   4. The split, compared against the FIRST of the two singles (never the
 *      second, which exists only to measure noise).
 * CONTAMINATION CAVEAT: step 3's second single grade itself runs on an
 * engine whose hash the SAME position may have just touched via a sibling
 * shard in a PRIOR position's split — this is intentional (it reproduces
 * the shipped pool's never-cleared table across the whole run, positions
 * processed in order with no `newGameAll` between them) but means the noise
 * floor is a property of THIS RUN'S position ordering, not a universal
 * constant.
 *
 * Usage (the four step-0/gate command lines):
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
 *     --split-source prototype --hash clear --openings 12 --out-dir reports/data
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
 *     --split-source prototype --hash warm --openings 12 --out-dir reports/data
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
 *     --split-source pool --hash clear --openings 12 --out-dir reports/data   # exits 3 before A21S
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs \
 *     --split-source pool --hash warm --openings 12 --out-dir reports/data   # A21S-only, real measurement
 *
 *   --split-source   REQUIRED. "prototype" or "pool" — see above.
 *   --hash           REQUIRED. "clear" or "warm" — see above.
 *   --procs          Stockfish pool size AND max split fan-out width (default 4)
 *   --openings       additionally draw N positions from `calibration-openings.mjs`'s
 *                     OPENING_BOOK, added to the built-in 4-position set (default 12,
 *                     position_set "throughput" — same set `engine-grading-depth-ab.mjs` uses)
 *   --fens           newline-delimited FEN file (`#` comments allowed), REPLACES the
 *                     built-in set (position_set "throughput")
 *   --fixture        `id fen correct_move eval_gap_cp note source` TSV (the
 *                     `fixtures/engine/maia-blindness.tsv` shape) — every row's FEN is
 *                     ADDED as position_set "fixture"
 *   --elo            symmetric per-side ELO for the practical model (default 1500)
 *   --depth          grading depth for both single and split calls (default GRADING_ROOT_DEPTH)
 *   --out-dir        emit a TSV here; omit to print only
 *   --self-test      exercise parseArgs + partitionRoundRobin + candidateWeightedMean
 *                    only (no engines spawned); exits non-zero on failure
 *
 * Prohibitions (D-16 must_haves): this tool never runs the full 16 +
 * fixture position set itself — that is Plan 226-07/226-12 orchestrator
 * work. It only proves the one-position smoke works end to end.
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

import {
  createStockfishPool,
  ROOT_SPLIT_ABSENT_MESSAGE,
} from './lib/stockfish-pool.mjs';
import { createMaiaSession } from './lib/node-engine-providers.mjs';
import { makeNodeProviders, nodeGrade } from './lib/calibration-providers.mjs';
import { BUILTIN_POSITIONS, resolvePositions } from './engine-grading-depth-ab.mjs';

import { mctsSearch } from '@/lib/engine/mctsSearch';
import { GRADING_ROOT_DEPTH } from '@/lib/engine/gradingLadder';
import { FLAWCHESS_BOT_MAX_NODES, FLAWCHESS_BOT_MAX_PLIES, FLAWCHESS_BOT_CONCURRENCY } from '@/lib/engine/botBudget';
import { WORKER_HASH_MB } from '@/lib/engine/workerPoolState';
import { evalToExpectedScore } from '@/lib/liveFlaw';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '..');

// ─── Defaults / constants ────────────────────────────────────────────────────

export const DEFAULT_PROCS = 4;
export const DEFAULT_OPENINGS = 12;
/** Bot-shaped warm-up search (D-16 warm leg): mirrors the shipped bot's own node budget. */
export const WARMUP_NODES = FLAWCHESS_BOT_MAX_NODES;
/** Bot-shaped warm-up search concurrency: mirrors the shipped bot's own concurrency. */
export const WARMUP_CONCURRENCY = FLAWCHESS_BOT_CONCURRENCY;
/** Symmetric per-side ELO default for both candidate capture and the warm-up search. */
const DEFAULT_ELO = 1500;
/** Exit code for "rootSplit.ts absent" (expected before arm A21S) — never a check failure. */
export const EXIT_MODULE_ABSENT = 3;

/** The verdict script's content TSV contract (`_CONTENT_REQUIRED_COLUMNS`), same order. */
const CONTENT_TSV_COLUMNS = [
  'position', 'position_set', 'hash_mode', 'split_source', 'k', 'n_candidates',
  'single_ms', 'split_wall_ms', 'split_cpu_ms', 'mean_abs_dcp', 'max_abs_dcp',
  'mean_abs_des', 'max_abs_des', 'noise_mean_abs_des', 'noise_max_abs_des',
  'root_argmax_flip',
];

// ─── Arg parsing (mirrors engine-grading-depth-ab.mjs's flag conventions) ────

function requireFlagValue(value, key) {
  if (value === undefined || value.startsWith('--')) {
    throw new Error(`Missing value for --${key}`);
  }
  return value;
}

function parsePositiveIntFlag(value, key, min = 1) {
  const parsed = Number.parseInt(requireFlagValue(value, key), 10);
  if (!Number.isInteger(parsed) || parsed < min) {
    throw new Error(`Invalid --${key}: expected an integer >= ${min}, got ${JSON.stringify(value)}`);
  }
  return parsed;
}

function parseEnumFlag(value, key, allowed) {
  const raw = requireFlagValue(value, key);
  if (!allowed.includes(raw)) {
    throw new Error(`Invalid --${key} ${JSON.stringify(raw)}: expected one of ${allowed.join('|')}`);
  }
  return raw;
}

export function parseArgs(argv) {
  const args = {
    splitSource: null,
    hash: null,
    procs: DEFAULT_PROCS,
    openings: DEFAULT_OPENINGS,
    fens: null,
    fixture: null,
    elo: DEFAULT_ELO,
    depth: GRADING_ROOT_DEPTH,
    outDir: null,
    selfTest: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (token === '--help' || token === '-h') {
      args.help = true;
      continue;
    }
    if (token === '--self-test') {
      args.selfTest = true;
      continue;
    }
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1];
    switch (key) {
      case 'split-source': args.splitSource = parseEnumFlag(value, key, ['prototype', 'pool']); i++; break;
      case 'hash': args.hash = parseEnumFlag(value, key, ['clear', 'warm']); i++; break;
      case 'procs': args.procs = parsePositiveIntFlag(value, key); i++; break;
      case 'openings': args.openings = parsePositiveIntFlag(value, key, 0); i++; break;
      case 'fens': args.fens = requireFlagValue(value, key); i++; break;
      case 'fixture': args.fixture = requireFlagValue(value, key); i++; break;
      case 'elo': args.elo = parsePositiveIntFlag(value, key); i++; break;
      case 'depth': args.depth = parsePositiveIntFlag(value, key); i++; break;
      case 'out-dir': args.outDir = requireFlagValue(value, key); i++; break;
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  if (!args.help && !args.selfTest) {
    const missing = [];
    if (args.splitSource === null) missing.push('--split-source prototype|pool');
    if (args.hash === null) missing.push('--hash clear|warm');
    if (missing.length > 0) {
      throw new Error(`Missing required flag(s): ${missing.join(', ')}`);
    }
  }
  return args;
}

// ─── Fixture FEN reader (--fixture) ──────────────────────────────────────────

/**
 * Reads `--fixture PATH`'s FEN rows (position_set "fixture"). Mirrors the
 * `id fen correct_move eval_gap_cp note source` TSV shape shared by
 * `fixtures/engine/maia-blindness.tsv` and the D-14 widened fixture
 * (`fixtures/engine/move-quality-226.tsv`, not yet built) — only `id`/`fen`
 * are read here; this instrument measures grade content, not move quality,
 * so it does not reuse `engine-move-quality.mjs`'s `loadFixtureRows` (which
 * also parses/validates `correct_move`, irrelevant to this tool).
 */
function loadFixtureFens(filePath) {
  const resolved = path.isAbsolute(filePath) ? filePath : path.resolve(REPO_ROOT, filePath);
  const lines = fs.readFileSync(resolved, 'utf8').split('\n');
  const dataLines = lines.filter((line) => line.trim().length > 0 && !line.startsWith('#'));
  if (dataLines.length < 2) throw new Error(`--fixture ${filePath} has no data rows past its header`);
  const header = dataLines[0].split('\t');
  const fenIdx = header.indexOf('fen');
  const idIdx = header.indexOf('id');
  if (fenIdx === -1) throw new Error(`--fixture ${filePath} header is missing a 'fen' column`);
  return dataLines.slice(1).map((line, idx) => {
    const cells = line.split('\t');
    const fen = cells[fenIdx];
    if (!fen) throw new Error(`--fixture ${filePath} row ${idx + 2} has an empty fen`);
    return { label: idIdx !== -1 ? cells[idIdx] : `fixture${idx + 1}`, fen };
  });
}

// ─── Root candidate capture (captures the REAL root candidate set) ──────────

/**
 * Runs a real `mctsSearch` at `maxNodes: 1` (round 1 dispatches the root and
 * only the root, F-1) whose `grade` wrapper records the first call's
 * candidate list and resolves an EMPTY map — no engine is ever touched by
 * this call, so it has no hash effect in either mode. `providers.policy` is
 * the real Maia policy; `providers.grade` is discarded (the wrapper below
 * fully replaces it, never delegates to it).
 */
export async function captureRootCandidates(fen, providers, elo) {
  let captured = null;
  const wrappedProviders = {
    ...providers,
    grade: async (_fen, candidateUcis) => {
      if (captured === null) captured = candidateUcis;
      return new Map();
    },
  };
  const budget = {
    maxNodes: 1,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    concurrency: FLAWCHESS_BOT_CONCURRENCY,
    elo: { w: elo, b: elo },
  };
  await mctsSearch(fen, budget, wrappedProviders, () => {}, new AbortController().signal);
  if (captured === null) {
    throw new Error(`captureRootCandidates: no grade() call observed for ${fen} — degenerate root?`);
  }
  return captured;
}

// ─── Prototype split (round-robin partition, built HERE — no rootSplit.ts) ──

/**
 * Round-robin partition (`i % k`), matching `.planning/research/perf-profiling-2026-09-28/split_root.mjs`
 * and the eventual `rootSplit.ts` `partitionCandidates`. A pure function so
 * `--self-test` can exercise it for k > n, k == n, and k < n without
 * spawning any engine.
 */
export function partitionRoundRobin(candidateUcis, k) {
  const shards = Array.from({ length: k }, () => []);
  candidateUcis.forEach((uci, i) => shards[i % k].push(uci));
  return shards;
}

/**
 * Partitions `candidateUcis` round-robin across `min(procs, n)` shards and
 * grades each shard on the pool CONCURRENTLY (`Promise.all`), mirroring
 * `split_root.mjs`'s prototype exactly but reusing the shared `stockfish-pool.mjs`
 * (dead-engine recovery, retry-in-place) instead of a private pool. Returns
 * the merged grades plus `k` (shard count) and `splitCpuMs` (sum of each
 * shard's OWN elapsed time — the total engine CPU this split cost, distinct
 * from the wall-clock time the caller measures around this call).
 */
export async function prototypeSplit(pool, fen, candidateUcis, depth, procs) {
  const k = Math.min(procs, candidateUcis.length);
  const shards = partitionRoundRobin(candidateUcis, k);
  const timedShards = await Promise.all(
    shards.map(async (shard) => {
      if (shard.length === 0) return { grades: new Map(), ms: 0 };
      const startedAt = performance.now();
      const grades = await pool.grade(fen, shard, undefined, depth);
      return { grades, ms: performance.now() - startedAt };
    }),
  );
  const merged = new Map();
  for (const { grades } of timedShards) {
    for (const [uci, grade] of grades) merged.set(uci, grade);
  }
  const splitCpuMs = timedShards.reduce((sum, shard) => sum + shard.ms, 0);
  return { grades: merged, k, splitCpuMs };
}

/**
 * `--split-source pool`: calls the harness pool's OWN `gradeRoot` (the real
 * implementation this tool re-measures at arm A21S). Before A21S,
 * `rootSplit.ts` does not exist, so `pool.gradeRoot` throws
 * `ROOT_SPLIT_ABSENT_MESSAGE` — this is the EXPECTED, PASSING outcome
 * (mirrors `scripts/lib/stockfish-pool.check.mjs`'s own `--root-split`
 * section verbatim): print the message, quit the pool, exit `EXIT_MODULE_ABSENT`.
 * Once the module lands, `pool.rootSplitStats().splits` must rise by
 * exactly one for this call when k > 1 (and stay put when k <= 1, the
 * single-grade path), or the split silently did not happen — exit 1.
 * `k` is read from `pool.freeCount()` immediately before the call as a
 * best-effort snapshot of what `gradeRoot` itself will compute internally.
 */
async function runPoolGradeRoot(pool, fen, candidateUcis, depth) {
  const k = Math.min(pool.freeCount(), candidateUcis.length);
  const splitsBefore = pool.rootSplitStats().splits;
  let grades;
  try {
    grades = await pool.gradeRoot(fen, candidateUcis, undefined, depth);
  } catch (err) {
    if (err instanceof Error && err.message === ROOT_SPLIT_ABSENT_MESSAGE) {
      console.log(`ROOT-SPLIT: ${err.message}`);
      pool.quitAll();
      process.exit(EXIT_MODULE_ABSENT); // expected pre-A21S outcome — never a check failure
    }
    throw err;
  }
  // BUG (226-12 gate run): this asserted +1 split unconditionally, but
  // `splitAcrossFreeEngines` by design takes the single-grade path when
  // k <= 1 (one free engine or a single root candidate), so the first
  // one-legal-move root (HEzVd) aborted the run. Expect a split only when k > 1.
  const splitsAfter = pool.rootSplitStats().splits;
  const expectedSplits = splitsBefore + (k > 1 ? 1 : 0);
  if (splitsAfter !== expectedSplits) {
    console.error(
      `FAILURE: pool.rootSplitStats().splits did not rise by ${expectedSplits - splitsBefore} for ${fen} ` +
        `(k=${k} before=${splitsBefore} after=${splitsAfter})`,
    );
    pool.quitAll();
    process.exit(1);
  }
  return { grades, k };
}

// ─── Grade comparison ────────────────────────────────────────────────────────

/**
 * Per-candidate comparison of two grade maps (single vs split, or single vs
 * single for the noise floor): |delta cp| over non-mate pairs only,
 * |delta es| (mover POV, via `evalToExpectedScore`) over every pair
 * including mates, and whether the argmax (highest mover-POV expected
 * score) candidate differs between the two maps. `desList` is the raw
 * per-candidate |delta es| array, kept for the caller's own aggregate
 * percentile computation across the whole run.
 */
export function compareGrades(gradesA, gradesB, fen) {
  const mover = fen.split(' ')[1] === 'b' ? 'black' : 'white';
  let dcpSum = 0;
  let dcpCount = 0;
  let maxAbsDcp = 0;
  let desSum = 0;
  const desList = [];
  let maxAbsDes = 0;
  let bestAUci = null;
  let bestAEs = -Infinity;
  let bestBUci = null;
  let bestBEs = -Infinity;

  const allUcis = new Set([...gradesA.keys(), ...gradesB.keys()]);
  for (const uci of allUcis) {
    const a = gradesA.get(uci);
    const b = gradesB.get(uci);
    if (a !== undefined) {
      const esA = evalToExpectedScore(a.evalCp, a.evalMate, mover);
      if (esA > bestAEs) {
        bestAEs = esA;
        bestAUci = uci;
      }
    }
    if (b !== undefined) {
      const esB = evalToExpectedScore(b.evalCp, b.evalMate, mover);
      if (esB > bestBEs) {
        bestBEs = esB;
        bestBUci = uci;
      }
    }
    if (a === undefined || b === undefined) continue;

    if (a.evalMate == null && b.evalMate == null && a.evalCp != null && b.evalCp != null) {
      const absDcp = Math.abs(a.evalCp - b.evalCp);
      dcpSum += absDcp;
      dcpCount++;
      maxAbsDcp = Math.max(maxAbsDcp, absDcp);
    }

    const esA = evalToExpectedScore(a.evalCp, a.evalMate, mover);
    const esB = evalToExpectedScore(b.evalCp, b.evalMate, mover);
    const absDes = Math.abs(esA - esB);
    desSum += absDes;
    desList.push(absDes);
    maxAbsDes = Math.max(maxAbsDes, absDes);
  }

  return {
    meanAbsDcp: dcpCount > 0 ? dcpSum / dcpCount : 0,
    maxAbsDcp,
    meanAbsDes: desList.length > 0 ? desSum / desList.length : 0,
    maxAbsDes,
    rootArgmaxFlip: bestAUci !== null && bestBUci !== null && bestAUci !== bestBUci,
    desList,
  };
}

/**
 * Candidate-weighted mean over TSV row objects — the SAME definition as
 * `scripts/engine_throughput_226_verdict.py`'s `_candidate_weighted_mean`,
 * reimplemented here (not imported — this is a `.mjs` tool, that a Python
 * module) so a row's contribution scales with how many candidates it
 * actually compared, matching exactly how the verdict script will later
 * read these TSVs back.
 */
export function candidateWeightedMean(rows, column) {
  const totalWeight = rows.reduce((sum, row) => sum + Number(row.n_candidates), 0);
  if (totalWeight <= 0) {
    throw new Error(`candidateWeightedMean: total n_candidates is zero over ${rows.length} rows`);
  }
  const weightedSum = rows.reduce((sum, row) => sum + Number(row.n_candidates) * Number(row[column]), 0);
  return weightedSum / totalWeight;
}

/** Nearest-rank percentile over a flat numeric array (report-only, not a TSV column). */
function percentile(values, p) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.floor(p * sorted.length));
  return sorted[idx];
}

// ─── Row builder ──────────────────────────────────────────────────────────

function buildRow({
  label, positionSet, hashMode, splitSource, k, nCandidates,
  singleMs, splitWallMs, splitCpuMs, cmp, noiseMeanAbsDes, noiseMaxAbsDes,
}) {
  return {
    position: label,
    position_set: positionSet,
    hash_mode: hashMode,
    split_source: splitSource,
    k: String(k),
    n_candidates: String(nCandidates),
    single_ms: singleMs.toFixed(1),
    split_wall_ms: splitWallMs.toFixed(1),
    split_cpu_ms: splitCpuMs === '' ? '' : splitCpuMs.toFixed(1),
    mean_abs_dcp: cmp.meanAbsDcp.toFixed(2),
    max_abs_dcp: cmp.maxAbsDcp.toFixed(2),
    mean_abs_des: cmp.meanAbsDes.toFixed(6),
    max_abs_des: cmp.maxAbsDes.toFixed(6),
    noise_mean_abs_des: noiseMeanAbsDes === '' ? '' : noiseMeanAbsDes.toFixed(6),
    noise_max_abs_des: noiseMaxAbsDes === '' ? '' : noiseMaxAbsDes.toFixed(6),
    root_argmax_flip: cmp.rootArgmaxFlip ? 'true' : 'false',
  };
}

/** Times an async thunk; returns `{ result, ms }`. */
async function timed(fn) {
  const startedAt = performance.now();
  const result = await fn();
  return { result, ms: performance.now() - startedAt };
}

/** Resolves the split for either `--split-source`, sharing the same call shape both row builders use. */
async function runSplit(pool, fen, candidateUcis, args) {
  if (args.splitSource === 'prototype') {
    const timedSplit = await timed(() => prototypeSplit(pool, fen, candidateUcis, args.depth, args.procs));
    return { grades: timedSplit.result.grades, k: timedSplit.result.k, splitCpuMs: timedSplit.result.splitCpuMs, splitWallMs: timedSplit.ms };
  }
  const timedSplit = await timed(() => runPoolGradeRoot(pool, fen, candidateUcis, args.depth));
  return { grades: timedSplit.result.grades, k: timedSplit.result.k, splitCpuMs: '', splitWallMs: timedSplit.ms };
}

/** Clear-Hash row: single vs split, exact (single-vs-single would be 0 under Clear Hash, so noise columns are empty). */
async function runClearRow(pool, session, ort, fen, label, positionSet, args) {
  const captureProviders = makeNodeProviders(session, ort, async () => new Map());
  const candidateUcis = await captureRootCandidates(fen, captureProviders, args.elo);

  const single = await timed(() => pool.grade(fen, candidateUcis, undefined, args.depth));
  const split = await runSplit(pool, fen, candidateUcis, args);

  const cmp = compareGrades(single.result, split.grades, fen);
  const row = buildRow({
    label, positionSet, hashMode: 'clear', splitSource: args.splitSource, k: split.k,
    nCandidates: candidateUcis.length, singleMs: single.ms, splitWallMs: split.splitWallMs,
    splitCpuMs: split.splitCpuMs, cmp, noiseMeanAbsDes: '', noiseMaxAbsDes: '',
  });
  return { row, desList: cmp.desList };
}

/** Warm-Hash row: see the module header's numbered warm-mode measurement order. */
async function runWarmRow(pool, session, ort, warmupProviders, fen, label, positionSet, args) {
  const captureProviders = makeNodeProviders(session, ort, async () => new Map());
  const candidateUcis = await captureRootCandidates(fen, captureProviders, args.elo);

  const warmupBudget = {
    maxNodes: WARMUP_NODES,
    maxPlies: FLAWCHESS_BOT_MAX_PLIES,
    concurrency: WARMUP_CONCURRENCY,
    elo: { w: args.elo, b: args.elo },
  };
  await mctsSearch(fen, warmupBudget, warmupProviders, () => {}, new AbortController().signal);

  const [single1, single2] = await Promise.all([
    timed(() => pool.grade(fen, candidateUcis, undefined, args.depth)),
    timed(() => pool.grade(fen, candidateUcis, undefined, args.depth)),
  ]);
  const noise = compareGrades(single1.result, single2.result, fen);

  const split = await runSplit(pool, fen, candidateUcis, args);

  // Content is measured against single1 ONLY — single2 exists purely to
  // measure the noise floor above (module header's numbered order).
  const cmp = compareGrades(single1.result, split.grades, fen);
  const row = buildRow({
    label, positionSet, hashMode: 'warm', splitSource: args.splitSource, k: split.k,
    nCandidates: candidateUcis.length, singleMs: single1.ms, splitWallMs: split.splitWallMs,
    splitCpuMs: split.splitCpuMs, cmp, noiseMeanAbsDes: noise.meanAbsDes, noiseMaxAbsDes: noise.maxAbsDes,
  });
  return { row, desList: cmp.desList };
}

// ─── Self-test (parseArgs + partitionRoundRobin + candidateWeightedMean only, no engines) ──

function runSelfTest() {
  let ok = true;
  const check = (cond, label) => {
    if (cond) {
      console.log(`SELF-TEST ok: ${label}`);
    } else {
      console.error(`SELF-TEST FAILED: ${label}`);
      ok = false;
    }
  };

  // Unknown flag throws.
  try {
    parseArgs(['--bogus-flag']);
    check(false, 'unknown flag should throw');
  } catch (err) {
    check(err.message.includes('Unknown flag'), 'unknown flag throws with a named-flag message');
  }

  // Missing --split-source/--hash throws for a real run.
  try {
    parseArgs([]);
    check(false, 'omitting --split-source and --hash should throw');
  } catch (err) {
    check(
      /split-source/.test(err.message) && /hash/.test(err.message),
      'missing --split-source/--hash throws naming both',
    );
  }

  // --self-test and --help bypass the requirement.
  const selfTestArgs = parseArgs(['--self-test']);
  check(selfTestArgs.selfTest === true, '--self-test bypasses the --split-source/--hash requirement');
  const helpArgs = parseArgs(['--help']);
  check(helpArgs.help === true, '--help bypasses the --split-source/--hash requirement');

  // Invalid enum values throw.
  try {
    parseArgs(['--split-source', 'bogus', '--hash', 'clear']);
    check(false, 'an invalid --split-source value should throw');
  } catch (err) {
    check(/split-source/.test(err.message), 'invalid --split-source throws mentioning split-source');
  }
  try {
    parseArgs(['--split-source', 'prototype', '--hash', 'bogus']);
    check(false, 'an invalid --hash value should throw');
  } catch (err) {
    check(/hash/.test(err.message), 'invalid --hash throws mentioning hash');
  }

  // Defaults resolve as documented.
  const defaultArgs = parseArgs(['--split-source', 'prototype', '--hash', 'clear']);
  check(defaultArgs.procs === DEFAULT_PROCS, `--procs defaults to ${DEFAULT_PROCS}, got ${defaultArgs.procs}`);
  check(defaultArgs.openings === DEFAULT_OPENINGS, `--openings defaults to ${DEFAULT_OPENINGS}, got ${defaultArgs.openings}`);
  check(defaultArgs.depth === GRADING_ROOT_DEPTH, `--depth defaults to GRADING_ROOT_DEPTH (${GRADING_ROOT_DEPTH}), got ${defaultArgs.depth}`);

  // --openings 0 with no --fens resolves only the 4 built-in positions.
  const zeroOpeningsPositions = resolvePositions({ fens: null, openings: 0 });
  check(
    zeroOpeningsPositions.length === BUILTIN_POSITIONS.length,
    `--openings 0 resolves ${BUILTIN_POSITIONS.length} built-in positions, got ${zeroOpeningsPositions.length}`,
  );

  // partitionRoundRobin: k < n, k == n, k > n.
  const cands5 = ['a', 'b', 'c', 'd', 'e'];
  const kLess = partitionRoundRobin(cands5, 2);
  check(
    kLess.length === 2 && kLess.flat().length === 5 && kLess[0].join(',') === 'a,c,e' && kLess[1].join(',') === 'b,d',
    `partitionRoundRobin(5 cands, k=2) round-robins i%2, got ${JSON.stringify(kLess)}`,
  );
  const kEqual = partitionRoundRobin(cands5, 5);
  check(
    kEqual.length === 5 && kEqual.every((shard) => shard.length === 1),
    `partitionRoundRobin(5 cands, k=5) gives 5 singleton shards, got ${JSON.stringify(kEqual)}`,
  );
  const kMore = partitionRoundRobin(['a', 'b'], 5);
  check(
    kMore.length === 5 && kMore.filter((shard) => shard.length > 0).length === 2 && kMore.flat().length === 2,
    `partitionRoundRobin(2 cands, k=5) gives 2 non-empty + 3 empty shards, got ${JSON.stringify(kMore)}`,
  );

  // candidateWeightedMean: weighted by n_candidates, matching the Python twin.
  const weightedRows = [
    { n_candidates: '2', mean_abs_des: '0.10' },
    { n_candidates: '8', mean_abs_des: '0.20' },
  ];
  const weighted = candidateWeightedMean(weightedRows, 'mean_abs_des');
  check(Math.abs(weighted - 0.18) < 1e-9, `candidateWeightedMean weights by n_candidates, got ${weighted} expected 0.18`);
  try {
    candidateWeightedMean([{ n_candidates: '0', mean_abs_des: '0' }], 'mean_abs_des');
    check(false, 'candidateWeightedMean with zero total weight should throw');
  } catch (err) {
    check(/total n_candidates is zero/.test(err.message), 'zero-weight candidateWeightedMean throws naming the cause');
  }

  // compareGrades: exact-match maps give zero deltas and no argmax flip.
  const gradesA = new Map([
    ['e2e4', { evalCp: 50, evalMate: null, depth: 14 }],
    ['d2d4', { evalCp: 30, evalMate: null, depth: 14 }],
  ]);
  const identical = compareGrades(gradesA, gradesA, 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  check(
    identical.meanAbsDcp === 0 && identical.meanAbsDes === 0 && identical.rootArgmaxFlip === false,
    `compareGrades(same map, same map) gives zero deltas and no flip, got ${JSON.stringify(identical)}`,
  );

  return ok;
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(fs.readFileSync(new URL(import.meta.url), 'utf8').split('*/')[0]);
    return 0;
  }
  if (args.selfTest) {
    const passed = runSelfTest();
    console.log(passed ? '\nSelf-test: ALL CHECKS PASSED' : '\nSelf-test: FAILURES ABOVE');
    return passed ? 0 : 1;
  }

  const throughputPositions = resolvePositions({ fens: args.fens, openings: args.openings }).map((p) => ({
    ...p,
    positionSet: 'throughput',
  }));
  const fixturePositions =
    args.fixture !== null
      ? loadFixtureFens(args.fixture).map((p) => ({ ...p, positionSet: 'fixture' }))
      : [];
  const positions = [...throughputPositions, ...fixturePositions];

  console.log(
    `\nRoot-split content — hash=${args.hash} source=${args.splitSource} procs=${args.procs} ` +
      `elo=${args.elo} depth=${args.depth} positions=${positions.length}\n`,
  );

  const { session, ort } = await createMaiaSession();
  const pool = await createStockfishPool({
    size: args.procs,
    hashMb: WORKER_HASH_MB,
    clearHash: args.hash === 'clear',
  });

  const rows = [];
  const allDesDeltas = [];

  if (args.hash === 'clear') {
    for (const { label, fen, positionSet } of positions) {
      const { row, desList } = await runClearRow(pool, session, ort, fen, label, positionSet, args);
      rows.push(row);
      allDesDeltas.push(...desList);
      console.log(
        `   ${label}: n=${row.n_candidates} k=${row.k} single=${row.single_ms}ms ` +
          `split_wall=${row.split_wall_ms}ms mean|de_s|=${row.mean_abs_des} flip=${row.root_argmax_flip}`,
      );
    }
  } else {
    const warmupGradeFn = (fen, candidateUcis, signal, depth) =>
      pool.run((engine) => nodeGrade(engine, fen, candidateUcis, depth, { clearHash: false }));
    const warmupProviders = makeNodeProviders(session, ort, warmupGradeFn);
    for (const { label, fen, positionSet } of positions) {
      const { row, desList } = await runWarmRow(pool, session, ort, warmupProviders, fen, label, positionSet, args);
      rows.push(row);
      allDesDeltas.push(...desList);
      console.log(
        `   ${label}: n=${row.n_candidates} k=${row.k} single=${row.single_ms}ms ` +
          `split_wall=${row.split_wall_ms}ms mean|de_s|=${row.mean_abs_des} noise=${row.noise_mean_abs_des} flip=${row.root_argmax_flip}`,
      );
    }
  }

  const meanAbsDes = candidateWeightedMean(rows, 'mean_abs_des');
  const p95AbsDes = percentile(allDesDeltas, 0.95);
  // Clear-Hash mode's single-vs-single is exactly 0 by construction (D-16
  // must_haves) — never measured directly in clear mode, so the summary
  // reports it as 'n/a' rather than a fabricated 0.000000.
  const noiseMeanAbsDes = args.hash === 'warm' ? candidateWeightedMean(rows, 'noise_mean_abs_des') : null;
  const totalSingleMs = rows.reduce((sum, row) => sum + Number(row.single_ms), 0);
  const totalSplitWallMs = rows.reduce((sum, row) => sum + Number(row.split_wall_ms), 0);
  const hasCpuTiming = rows.every((row) => row.split_cpu_ms !== '');
  const totalSplitCpuMs = hasCpuTiming ? rows.reduce((sum, row) => sum + Number(row.split_cpu_ms), 0) : null;

  console.log(
    `\nCONTENT hash=${args.hash} source=${args.splitSource} rows=${rows.length} ` +
      `mean_abs_des=${meanAbsDes.toFixed(6)} p95_abs_des=${p95AbsDes.toFixed(6)} ` +
      `noise_mean_abs_des=${noiseMeanAbsDes !== null ? noiseMeanAbsDes.toFixed(6) : 'n/a'} ` +
      `single_ms=${totalSingleMs.toFixed(1)} split_wall_ms=${totalSplitWallMs.toFixed(1)} ` +
      `split_cpu_ms=${totalSplitCpuMs !== null ? totalSplitCpuMs.toFixed(1) : 'n/a'}`,
  );

  if (args.outDir !== null) {
    const outDir = path.isAbsolute(args.outDir) ? args.outDir : path.resolve(REPO_ROOT, args.outDir);
    fs.mkdirSync(outDir, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outPath = path.join(outDir, `engine-root-split-content-${args.hash}-${args.splitSource}-${stamp}.tsv`);
    const tsv = [
      CONTENT_TSV_COLUMNS.join('\t'),
      ...rows.map((row) => CONTENT_TSV_COLUMNS.map((c) => row[c] ?? '').join('\t')),
    ].join('\n');
    fs.writeFileSync(outPath, `${tsv}\n`);
    console.log(`\nWrote ${outPath}`);
  }

  pool.quitAll();
  return 0;
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const code = await main();
  process.exit(code);
}
