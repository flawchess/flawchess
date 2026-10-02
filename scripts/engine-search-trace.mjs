#!/usr/bin/env node
/**
 * engine-search-trace.mjs — D-13's cBFTV diagnosis tool (Phase 226).
 *
 * Runs the LIVE `mctsSearch` in the move-quality gate's own configuration
 * (`createGradePool` warm hash, `newGameAll()`/`resetMaiaRunMemo()` before
 * each position, elo 1500, 50 nodes, concurrency 4, `--stop-rule off` by
 * default) with `policy`/`grade`/`gradeRoot` wrapped by `makeTracingProviders`,
 * so every expansion and every snapshot the search produces is written to a
 * per-round TSV. This is what lets the A0 vs A2 trees at `cBFTV` (225-RESEARCH
 * "Pattern 3") be compared expansion by expansion instead of by final
 * `rankedLines` alone.
 *
 * Round id rule (mirrors `mctsSearch.roundFill.test.ts`'s header comment,
 * `d428a0194`): `policy()` is the first `await` in `dispatchExpansion`, so
 * every expansion dispatched in one round calls `policy()` before any of that
 * round's `onSnapshot` events fire (the apply loop runs strictly after
 * `Promise.all` resolves). The run length of consecutive `policy()` calls
 * between `onSnapshot` events is therefore exactly one round's dispatch
 * size — this tool increments its own round counter at the first `policy()`
 * call after any `onSnapshot` (and at the very first call), needing zero
 * production instrumentation.
 *
 * Two mechanical bug signatures are flagged automatically (`TRACE-ANOMALY`
 * lines), the two the D-08 round-fill bug and any regression of it would
 * produce: a round dispatching more expansions than the concurrency, or the
 * same leaf (by its root-to-leaf UCI path) graded twice.
 *
 * MUST run from a detached worktree when comparing A0 vs A2 (RESEARCH Pattern
 * 3/9): `@/` resolves relative to the alias hook's own location, so this
 * script always measures whatever `mctsSearch.ts` is checked out in the
 * process's own repo — never a fixed comparison commit.
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-search-trace.mjs \
 *     --ids cBFTV --label a0 \
 *     [--fixture fixtures/engine/maia-blindness.tsv] \
 *     [--elo 1500] [--nodes 50] [--concurrency 4] [--procs 4] [--plies 8] \
 *     [--stop-rule on|off] [--out-dir reports/data] [--self-test] [--help]
 *
 * Worked cBFTV command (the D-13 measurement):
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-search-trace.mjs \
 *     --ids cBFTV --label a0
 *
 *   --fixture      tab-separated fixture (id/fen/correct_move/eval_gap_cp/
 *                  note/source). Default fixtures/engine/maia-blindness.tsv.
 *   --ids          comma-separated fixture row ids to trace. Default: every
 *                  row in the fixture.
 *   --label        REQUIRED for a real run. Stamped onto every row and into
 *                  the output filenames — the operator states which
 *                  detached-worktree commit this run measures (mirrors
 *                  engine-move-quality.mjs's `--arm`).
 *   --elo          symmetric per-side ELO (default 1500)
 *   --nodes        node-expansion budget (default 50)
 *   --concurrency  SearchBudget.concurrency (default 4)
 *   --procs        Stockfish pool size (default = --concurrency)
 *   --plies        search-tree ply cap (default 8)
 *   --stop-rule    "on" or "off" (default off — the D-13 measurement wants
 *                  the full 50-node tree, not an early-stopped one)
 *   --out-dir      emit the two TSVs here (default reports/data)
 *   --self-test    exercise parseArgs + a stubbed real mctsSearch run (fake
 *                  policy/grade, no engines spawned); exits non-zero on failure
 *   --help         print this header and exit
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

import { createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { makeNodeProviders, resetMaiaRunMemo } from './lib/calibration-providers.mjs';
import { createGradePool } from './engine-dispatch-stop-rule.mjs';
import { loadFixtureRows } from './engine-move-quality.mjs';

import { mctsSearch } from '@/lib/engine/mctsSearch';
import { argmaxLine } from '@/lib/engine/botSampling';
import {
  FLAWCHESS_BOT_MAX_NODES,
  FLAWCHESS_BOT_MAX_PLIES,
  FLAWCHESS_BOT_CONCURRENCY,
  FLAWCHESS_BOT_STOP_RULE,
} from '@/lib/engine/botBudget';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '..');

// ─── Defaults ────────────────────────────────────────────────────────────────

const DEFAULT_FIXTURE = 'fixtures/engine/maia-blindness.tsv';
const DEFAULT_ELO = 1500;
const DEFAULT_OUT_DIR = 'reports/data';

// ─── Arg parsing (mirrors engine-move-quality.mjs's conventions) ────────────

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

export function parseArgs(argv) {
  const args = {
    fixture: DEFAULT_FIXTURE,
    ids: null,
    label: null,
    elo: DEFAULT_ELO,
    nodes: FLAWCHESS_BOT_MAX_NODES,
    concurrency: FLAWCHESS_BOT_CONCURRENCY,
    procs: null,
    plies: FLAWCHESS_BOT_MAX_PLIES,
    stopRule: 'off',
    outDir: DEFAULT_OUT_DIR,
    help: false,
    selfTest: false,
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
      case 'fixture': args.fixture = requireFlagValue(value, key); i++; break;
      case 'ids': {
        const raw = requireFlagValue(value, key);
        args.ids = raw.split(',').map((s) => s.trim()).filter((s) => s.length > 0);
        i++;
        break;
      }
      case 'label': args.label = requireFlagValue(value, key); i++; break;
      case 'elo': args.elo = parsePositiveIntFlag(value, key); i++; break;
      case 'nodes': args.nodes = parsePositiveIntFlag(value, key); i++; break;
      case 'concurrency': args.concurrency = parsePositiveIntFlag(value, key); i++; break;
      case 'procs': args.procs = parsePositiveIntFlag(value, key); i++; break;
      case 'plies': args.plies = parsePositiveIntFlag(value, key); i++; break;
      case 'stop-rule': {
        const raw = requireFlagValue(value, key);
        if (raw !== 'on' && raw !== 'off') {
          throw new Error(`Invalid --stop-rule ${JSON.stringify(raw)}: expected "on" or "off"`);
        }
        args.stopRule = raw;
        i++;
        break;
      }
      case 'out-dir': args.outDir = requireFlagValue(value, key); i++; break;
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  // --label is REQUIRED for a real run (mirrors engine-move-quality.mjs's
  // --arm): the operator states which detached-worktree commit this run
  // measures. --help and --self-test both bypass it.
  if (!args.help && !args.selfTest && args.label === null) {
    throw new Error('Missing required --label LABEL — states which arm/commit this run measures');
  }
  if (args.procs === null) args.procs = args.concurrency;
  return args;
}

function resolvePath(p) {
  return path.isAbsolute(p) ? p : path.resolve(REPO_ROOT, p);
}

// ─── Chess helper (child FEN from a leaf FEN + UCI, chess.js) ───────────────

/** Splits a UCI move string into `{from, to, promotion}` (mirrors engine-move-quality.mjs's parseUciMove). */
function parseUciMove(uci) {
  return { from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.length > 4 ? uci.slice(4) : undefined };
}

/** Applies `uci` to `fen` via chess.js, returning the resulting FEN or null if the move is illegal/malformed. */
function applyUciMove(Chess, fen, uci) {
  try {
    const board = new Chess(fen);
    const { from, to, promotion } = parseUciMove(uci);
    board.move({ from, to, promotion });
    return board.fen();
  } catch {
    return null;
  }
}

// ─── reconstructPath (root -> leaf UCI path from the recorded edge map) ────

/**
 * Walks `edges` (childFen -> {parentFen, uci}) backward from `leafFen` to
 * `rootFen`, returning the root-to-leaf path as space-separated UCIs (empty
 * string for the root itself). Defensive: an unknown fen or a cycle stops the
 * walk early and returns whatever was reconstructed so far, rather than
 * looping or throwing — a missing edge is a tracer bug, not a search bug, and
 * must never crash the measurement.
 */
export function reconstructPath(rootFen, leafFen, edges) {
  if (leafFen === rootFen) return '';
  const ucis = [];
  let current = leafFen;
  const guard = new Set();
  while (current !== rootFen) {
    const edge = edges.get(current);
    if (edge === undefined) break;
    if (guard.has(current)) break;
    guard.add(current);
    ucis.unshift(edge.uci);
    current = edge.parentFen;
  }
  return ucis.join(' ');
}

// ─── makeTracingProviders (wraps policy/grade/gradeRoot) ────────────────────

/**
 * Wraps `providers.policy`, `providers.grade`, and `providers.gradeRoot` (when
 * present) so every expansion this search dispatches is recorded into `sink`.
 * `sink` carries the mutable round-counter state AND the chess.js `Chess`
 * constructor (`sink.Chess`) needed to compute child FENs — kept off this
 * function's own parameter list so its signature stays exactly
 * `(providers, rootFen, sink)` per the tool's own header contract, and so the
 * caller-supplied `onSnapshot` (which also needs to read/reset the SAME round
 * counter) can be wired directly into `mctsSearch` without a second wrapping
 * layer here.
 *
 * grade/gradeRoot forward all four `EngineProviders.grade`-shaped params
 * (`fen, candidateUcis, signal, gradingDepth`) unchanged — never truncated to
 * fewer parameters (Phase 195 T-195-09 landmine).
 */
export function makeTracingProviders(providers, rootFen, sink) {
  const wrappedPolicy = async (fen, elo, side, signal) => {
    if (sink.sinceSnapshot) {
      sink.round += 1;
      sink.sinceSnapshot = false;
    }
    return providers.policy(fen, elo, side, signal);
  };

  let expansionIndex = 0;

  const wrapGrade = (gradeFn) => async (fen, candidateUcis, signal, gradingDepth) => {
    const leafPath = fen === rootFen ? '' : reconstructPath(rootFen, fen, sink.edges);
    // Record this leaf's OWN children's edges synchronously, before awaiting
    // the grade — a later round's grade() call for one of these children
    // needs the edge already present, and edge recording never depends on
    // whether the grade itself resolves to anything useful.
    for (const uci of candidateUcis) {
      const childFen = applyUciMove(sink.Chess, fen, uci);
      if (childFen !== null && !sink.edges.has(childFen)) {
        sink.edges.set(childFen, { parentFen: fen, uci });
      }
    }
    const grades = await gradeFn(fen, candidateUcis, signal, gradingDepth);
    const gradesStr = candidateUcis
      .map((uci) => {
        const g = grades.get(uci);
        if (g === undefined) return `${uci}:`;
        return g.evalMate !== null ? `${uci}:#${g.evalMate}` : `${uci}:${g.evalCp}`;
      })
      .join(';');
    sink.expansions.push({
      round: sink.round,
      expansionIndex: expansionIndex++,
      leafFen: fen,
      leafPath,
      gradeDepth: gradingDepth ?? null,
      nCandidates: candidateUcis.length,
      gradesStr,
    });
    return grades;
  };

  const wrapped = { policy: wrappedPolicy, grade: wrapGrade(providers.grade) };
  if (providers.gradeRoot) wrapped.gradeRoot = wrapGrade(providers.gradeRoot);
  return wrapped;
}

// ─── detectAnomalies (the two D-08 bug signatures) ───────────────────────────

/**
 * Scans `sink.expansions` for the two externally-visible bug signatures
 * RESEARCH Pattern 3 names: a round dispatching more expansions than the
 * concurrency (`round-over-concurrency`), and the same leaf (by its
 * root-to-leaf UCI path) graded more than once (`duplicate-expansion`, which
 * would mean a node was expanded twice — WR-01's whole point is that this
 * never happens). Pure and side-effect-free so `--self-test` can assert on it
 * directly; `main()` prints each returned anomaly as a `TRACE-ANOMALY` line.
 */
export function detectAnomalies(sink, concurrency) {
  const anomalies = [];
  const countByRound = new Map();
  for (const exp of sink.expansions) {
    countByRound.set(exp.round, (countByRound.get(exp.round) ?? 0) + 1);
  }
  for (const [round, count] of countByRound) {
    if (count > concurrency) anomalies.push({ kind: 'round-over-concurrency', round });
  }
  const seenPaths = new Set();
  for (const exp of sink.expansions) {
    if (seenPaths.has(exp.leafPath)) {
      anomalies.push({ kind: 'duplicate-expansion', round: exp.round });
    } else {
      seenPaths.add(exp.leafPath);
    }
  }
  return anomalies;
}

/** Round sizes as a dense array indexed by round id (0..maxRound), 0 for a round with no expansions recorded. */
function computeRoundSizes(expansions) {
  const counts = new Map();
  for (const exp of expansions) counts.set(exp.round, (counts.get(exp.round) ?? 0) + 1);
  let maxRound = -1;
  for (const round of counts.keys()) if (round > maxRound) maxRound = round;
  const sizes = [];
  for (let r = 0; r <= maxRound; r++) sizes.push(counts.get(r) ?? 0);
  return sizes;
}

function writeTsv(outPath, columns, rows) {
  const tsv = [
    columns.join('\t'),
    ...rows.map((row) => columns.map((c) => (row[c] === undefined ? '' : String(row[c]))).join('\t')),
  ].join('\n');
  fs.writeFileSync(outPath, `${tsv}\n`);
  console.log(`Wrote ${outPath}`);
}

// ─── Self-test (parseArgs + a stubbed real mctsSearch run, no engines) ─────

/**
 * `--self-test`: parseArgs cases, plus a REAL `mctsSearch` run (concurrency
 * 2, a fixed legal FEN, a deterministic fake policy over chess.js's own move
 * ordering, and a fake grade returning cp 0 for every candidate) driven
 * through `makeTracingProviders`. No Maia/Stockfish process is spawned —
 * chess.js itself is pure JS, not an engine. Asserts round 0 (the root's own
 * single expansion) has size 1, the recorded expansions equal the final
 * `nodesEvaluated`, and no anomaly fires on this bug-free stubbed run.
 */
async function runSelfTest() {
  let ok = true;
  const check = (cond, label) => {
    if (!cond) {
      console.error(`SELF-TEST FAILED: ${label}`);
      ok = false;
    } else {
      console.log(`SELF-TEST ok: ${label}`);
    }
  };

  // Unknown flag throws.
  try {
    parseArgs(['--label', 'a0', '--bogus-flag']);
    check(false, 'unknown flag should throw');
  } catch (err) {
    check(err.message.includes('Unknown flag'), 'unknown flag throws with a named-flag message');
  }

  // --label is required for a real run.
  try {
    parseArgs(['--ids', 'cBFTV']);
    check(false, 'omitting --label should throw');
  } catch (err) {
    check(/--label/.test(err.message), 'missing --label throws mentioning --label');
  }

  // --stop-rule rejects an unrecognized value.
  try {
    parseArgs(['--label', 'a0', '--stop-rule', 'sideways']);
    check(false, 'an invalid --stop-rule value should throw');
  } catch (err) {
    check(/stop-rule/i.test(err.message), 'invalid --stop-rule value throws mentioning stop-rule');
  }

  // --ids splits on commas and trims whitespace.
  const idsArgs = parseArgs(['--label', 'a0', '--ids', 'cBFTV, qFkqJ ,Mhfvi']);
  check(
    idsArgs.ids.length === 3 && idsArgs.ids[0] === 'cBFTV' && idsArgs.ids[1] === 'qFkqJ' && idsArgs.ids[2] === 'Mhfvi',
    `--ids splits and trims, got ${JSON.stringify(idsArgs.ids)}`,
  );

  // --help bypasses --label.
  try {
    const helpArgs = parseArgs(['--help']);
    check(helpArgs.help === true, '--help bypasses the --label requirement');
  } catch {
    check(false, '--help alone should not throw');
  }

  // --procs defaults to --concurrency when omitted.
  const procsArgs = parseArgs(['--label', 'a0', '--concurrency', '3']);
  check(procsArgs.procs === 3, `--procs defaults to --concurrency (3), got ${procsArgs.procs}`);

  // reconstructPath: a two-hop path reconstructs in root-to-leaf order.
  {
    const edges = new Map([
      ['fenB', { parentFen: 'fenRoot', uci: 'e2e4' }],
      ['fenC', { parentFen: 'fenB', uci: 'e7e5' }],
    ]);
    check(reconstructPath('fenRoot', 'fenRoot', edges) === '', 'reconstructPath of the root itself is empty');
    check(reconstructPath('fenRoot', 'fenC', edges) === 'e2e4 e7e5', 'reconstructPath walks two hops in order');
  }

  // detectAnomalies: over-concurrency and duplicate-path cases fire; a clean sink does not.
  {
    const overConcSink = {
      expansions: [
        { round: 0, leafPath: '' },
        { round: 1, leafPath: 'a' },
        { round: 1, leafPath: 'b' },
        { round: 1, leafPath: 'c' },
      ],
    };
    const overConcAnomalies = detectAnomalies(overConcSink, 2);
    check(
      overConcAnomalies.some((a) => a.kind === 'round-over-concurrency' && a.round === 1),
      `detectAnomalies flags round-over-concurrency, got ${JSON.stringify(overConcAnomalies)}`,
    );

    const dupSink = {
      expansions: [
        { round: 0, leafPath: '' },
        { round: 1, leafPath: 'e2e4' },
        { round: 2, leafPath: 'e2e4' },
      ],
    };
    const dupAnomalies = detectAnomalies(dupSink, 4);
    check(
      dupAnomalies.some((a) => a.kind === 'duplicate-expansion' && a.round === 2),
      `detectAnomalies flags duplicate-expansion, got ${JSON.stringify(dupAnomalies)}`,
    );

    const cleanSink = {
      expansions: [
        { round: 0, leafPath: '' },
        { round: 1, leafPath: 'e2e4' },
        { round: 1, leafPath: 'd2d4' },
      ],
    };
    check(detectAnomalies(cleanSink, 4).length === 0, 'detectAnomalies reports nothing on a clean sink');
  }

  // computeRoundSizes is dense and 0-filled for a skipped round id.
  {
    const sizes = computeRoundSizes([{ round: 0 }, { round: 2 }, { round: 2 }]);
    check(sizes.length === 3 && sizes[0] === 1 && sizes[1] === 0 && sizes[2] === 2, `computeRoundSizes is dense, got ${JSON.stringify(sizes)}`);
  }

  // Stubbed REAL mctsSearch run: concurrency 2, deterministic fake providers, no engines.
  {
    const { Chess } = await resolveFrontendModule('chess.js');
    const rootFen = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'; // italian opening
    const fakePolicy = async (fen) => {
      const board = new Chess(fen);
      const legal = board.moves({ verbose: true }).slice(0, 2); // deterministic chess.js ordering
      const dist = {};
      legal.forEach((m, i) => {
        dist[`${m.from}${m.to}${m.promotion ?? ''}`] = i === 0 ? 0.7 : 0.3;
      });
      return dist;
    };
    const fakeGrade = async (fen, candidateUcis) => {
      const grades = new Map();
      for (const uci of candidateUcis) grades.set(uci, { evalCp: 0, evalMate: null, depth: 1 });
      return grades;
    };

    const sink = { Chess, round: -1, sinceSnapshot: true, edges: new Map(), expansions: [] };
    const providers = makeTracingProviders({ policy: fakePolicy, grade: fakeGrade }, rootFen, sink);
    const budget = { maxNodes: 6, maxPlies: 4, concurrency: 2, elo: { w: 1500, b: 1500 } };
    const onSnapshot = () => {
      sink.sinceSnapshot = true;
    };
    const finalSnapshot = await mctsSearch(rootFen, budget, providers, onSnapshot, new AbortController().signal);

    const roundSizes = computeRoundSizes(sink.expansions);
    check(roundSizes[0] === 1, `round 0 (the root) has size 1, got round_sizes=${JSON.stringify(roundSizes)}`);
    check(
      sink.expansions.length === finalSnapshot.nodesEvaluated,
      `recorded expansions (${sink.expansions.length}) equal nodesEvaluated (${finalSnapshot.nodesEvaluated})`,
    );
    const anomalies = detectAnomalies(sink, 2);
    check(anomalies.length === 0, `no anomaly fires on the stubbed bug-free run, got ${JSON.stringify(anomalies)}`);
  }

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
    const passed = await runSelfTest();
    console.log(passed ? '\nSelf-test: ALL CHECKS PASSED' : '\nSelf-test: FAILURES ABOVE');
    return passed ? 0 : 1;
  }

  const allRows = loadFixtureRows(resolvePath(args.fixture));
  const rows = args.ids === null ? allRows : allRows.filter((row) => args.ids.includes(row.id));
  if (rows.length === 0) {
    throw new Error(`No fixture rows matched --ids ${args.ids ? args.ids.join(',') : '(none)'}`);
  }

  const { session, ort } = await createMaiaSession();
  const { Chess } = await resolveFrontendModule('chess.js');
  const pool = await createGradePool(args.procs);

  const outDir = resolvePath(args.outDir);
  fs.mkdirSync(outDir, { recursive: true });
  // Timestamp read once here, after engine bring-up and before any measurement.
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');

  const expansionRows = [];
  const snapshotRows = [];

  try {
    for (const row of rows) {
      await pool.resetAll();
      resetMaiaRunMemo();

      const baseProviders = makeNodeProviders(session, ort, pool.grade);
      const sink = { Chess, round: -1, sinceSnapshot: true, edges: new Map(), expansions: [] };
      const tracedProviders = makeTracingProviders(baseProviders, row.fen, sink);

      const budget = {
        maxNodes: args.nodes,
        maxPlies: args.plies,
        concurrency: args.concurrency,
        elo: { w: args.elo, b: args.elo },
        ...(args.stopRule === 'on' ? { stopRule: FLAWCHESS_BOT_STOP_RULE } : {}),
      };

      const onSnapshot = (snapshot) => {
        snapshotRows.push({
          id: row.id,
          label: args.label,
          concurrency: args.concurrency,
          round: sink.round,
          nodes_evaluated: snapshot.nodesEvaluated,
          root_lines: snapshot.rankedLines.map((l) => `${l.rootMove}:${l.visits}:${l.practicalScore}`).join(';'),
        });
        sink.sinceSnapshot = true;
      };

      const finalSnapshot = await mctsSearch(row.fen, budget, tracedProviders, onSnapshot, new AbortController().signal);

      const pick = argmaxLine(finalSnapshot.rankedLines);
      const roundSizes = computeRoundSizes(sink.expansions);
      console.log(`TRACE id=${row.id} label=${args.label} rounds=${roundSizes.length} round_sizes=${roundSizes.join(',')} pick=${pick}`);

      for (const anomaly of detectAnomalies(sink, args.concurrency)) {
        console.log(`TRACE-ANOMALY id=${row.id} kind=${anomaly.kind} round=${anomaly.round}`);
      }

      for (const exp of sink.expansions) {
        expansionRows.push({
          id: row.id,
          label: args.label,
          concurrency: args.concurrency,
          round: exp.round,
          expansion_index: exp.expansionIndex,
          leaf_fen: exp.leafFen,
          grade_depth: exp.gradeDepth,
          n_candidates: exp.nCandidates,
          grades: exp.gradesStr,
        });
      }
    }
  } finally {
    pool.quitAll();
  }

  const expColumns = ['id', 'label', 'concurrency', 'round', 'expansion_index', 'leaf_fen', 'grade_depth', 'n_candidates', 'grades'];
  const snapColumns = ['id', 'label', 'concurrency', 'round', 'nodes_evaluated', 'root_lines'];
  writeTsv(path.join(outDir, `engine-search-trace-expansions-${args.label}-c${args.concurrency}-${stamp}.tsv`), expColumns, expansionRows);
  writeTsv(path.join(outDir, `engine-search-trace-snapshots-${args.label}-c${args.concurrency}-${stamp}.tsv`), snapColumns, snapshotRows);

  return 0;
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const code = await main();
  process.exit(code);
}
