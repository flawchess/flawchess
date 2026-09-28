#!/usr/bin/env node
/**
 * engine-move-quality.mjs — Phase 225 D-13 (amended) move-quality gate.
 *
 * Sibling of the deleted `scripts/engine-wdl-leaf-quality.mjs` (Phase 197,
 * `b1764a83^`) — this script keeps that script's §4b substantive-quality
 * semantics (fixture loader, integrity precondition, `gradeChosenMoves`
 * pattern, `REGRESSION_MARGIN = 0.05`), but adapts them to a SINGLE arm
 * ("whatever `mctsSearch` is checked out") instead of a two-arm WDL-vs-
 * Stockfish-leaf comparison. Arms are selected by RUNNING THIS SCRIPT from
 * each arm's own detached worktree (D-12): `--arm LABEL` is a row label, not
 * a code-path switch.
 *
 * The judged selector is `argmaxLine(snapshot.rankedLines)` — the bot's
 * `blend=1` pick (`botSampling.ts`), reused directly rather than
 * re-implemented, since that is the ONLY selector the shipped bot ever
 * plays. `rankedLines[0]` (the findability-sorted analysis-board pick) is
 * emitted alongside, report-only: it is the pick item 3 (the findability
 * fallback fix) changes, so a regression there is a quantitative signal for
 * that item without being part of the bot-quality gate itself.
 *
 * `--stop-rule on|off` is REQUIRED and really switches the search budget
 * (on = the shipped `FLAWCHESS_BOT_STOP_RULE`, off = no `stopRule` at all —
 * the 2026-07-31 override procedure this fixture and margin come from). The
 * accept rule runs this script with `--stop-rule off` for A2 vs A0 (item 1
 * is invisible without the stop rule) and `--stop-rule on` for A21 vs A2.
 *
 * Reuses `scripts/lib/node-engine-providers.mjs` + `scripts/lib/
 * calibration-providers.mjs` for ALL engine bring-up, and imports
 * `createGradePool` straight from `scripts/engine-dispatch-stop-rule.mjs` —
 * the single mirror of `workerPool.ts`'s `sendGo` — rather than maintaining
 * a second copy (CAL-02).
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
 *     --arm LABEL --stop-rule on|off \
 *     [--fixture fixtures/engine/maia-blindness.tsv] \
 *     [--nodes 50] [--plies 8] [--elo 1500] [--procs 4] [--grade-depth 18] \
 *     [--out-dir reports/data] [--self-test] [--help]
 *
 *   --arm          REQUIRED for a real run. Label stamped onto every row —
 *                  the operator states which detached-worktree commit this
 *                  run measures (D-12); this script cannot infer it.
 *   --stop-rule    REQUIRED for a real run, "on" or "off". on = the shipped
 *                  FLAWCHESS_BOT_STOP_RULE; off = no stopRule at all (the
 *                  2026-07-31 override procedure this fixture/margin is from).
 *   --fixture      tab-separated fixture (id/fen/correct_move/eval_gap_cp/
 *                  note/source, `#`-prefixed preamble allowed). Default
 *                  fixtures/engine/maia-blindness.tsv.
 *   --nodes        node-expansion budget (default FLAWCHESS_BOT_MAX_NODES = 50)
 *   --plies        search-tree ply cap (default FLAWCHESS_BOT_MAX_PLIES = 8)
 *   --elo          symmetric per-side ELO (default 1500)
 *   --procs        Stockfish search-pool size; also SearchBudget.concurrency
 *                  (default FLAWCHESS_BOT_CONCURRENCY = 4)
 *   --grade-depth  independent Stockfish MultiPV grading depth (default 18)
 *   --out-dir      emit a TSV here; omit to print only
 *   --self-test    exercise parseArgs + fixture integrity only (no engines
 *                  spawned); exits non-zero on failure
 *   --help         print this header and exit
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

import { spawnStockfish, createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { makeNodeProviders, nodeGrade, resetMaiaRunMemo } from './lib/calibration-providers.mjs';
import { createGradePool } from './engine-dispatch-stop-rule.mjs';

import { mctsSearch } from '@/lib/engine/mctsSearch';
import { argmaxLine } from '@/lib/engine/botSampling';
import { evalToExpectedScore } from '@/lib/liveFlaw';
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
const DEFAULT_GRADE_DEPTH = 18;

/** Accept-rule §4b margin, expected-score units — same value as the deleted 2026-07-31 runner. */
const REGRESSION_MARGIN = 0.05;

/** Watchdog for the independent grading `go` (mirrors engine-dispatch-stop-rule.mjs's own convention). */
const GRADE_WATCHDOG_MS = 60_000;

// ─── Arg parsing (mirrors engine-dispatch-stop-rule.mjs's conventions) ──────

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
    arm: null,
    stopRule: null,
    nodes: FLAWCHESS_BOT_MAX_NODES,
    plies: FLAWCHESS_BOT_MAX_PLIES,
    elo: DEFAULT_ELO,
    procs: FLAWCHESS_BOT_CONCURRENCY,
    gradeDepth: DEFAULT_GRADE_DEPTH,
    outDir: null,
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
      case 'arm': args.arm = requireFlagValue(value, key); i++; break;
      case 'stop-rule': {
        const raw = requireFlagValue(value, key);
        if (raw !== 'on' && raw !== 'off') {
          throw new Error(`Invalid --stop-rule ${JSON.stringify(raw)}: expected "on" or "off"`);
        }
        args.stopRule = raw;
        i++;
        break;
      }
      case 'nodes': args.nodes = parsePositiveIntFlag(value, key); i++; break;
      case 'plies': args.plies = parsePositiveIntFlag(value, key); i++; break;
      case 'elo': args.elo = parsePositiveIntFlag(value, key); i++; break;
      case 'procs': args.procs = parsePositiveIntFlag(value, key); i++; break;
      case 'grade-depth': args.gradeDepth = parsePositiveIntFlag(value, key); i++; break;
      case 'out-dir': args.outDir = requireFlagValue(value, key); i++; break;
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  // --arm and --stop-rule are REQUIRED for a real run (D-12: the operator
  // states which detached-worktree commit this run measures, and which
  // budget mode — this cannot be inferred). --help and --self-test bypass both.
  if (!args.help && !args.selfTest) {
    if (args.arm === null) throw new Error('Missing required --arm LABEL — states which arm this run measures (D-12)');
    if (args.stopRule === null) {
      throw new Error('Missing required --stop-rule on|off — states which budget mode this run measures');
    }
  }
  return args;
}

function resolvePath(p) {
  return path.isAbsolute(p) ? p : path.resolve(REPO_ROOT, p);
}

// ─── Fixture loading + integrity precondition (T-225-01) ────────────────────

/** Splits a UCI move string into `{from, to, promotion}`, tolerating a trailing promotion letter. */
function parseUciMove(uci) {
  return { from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.length > 4 ? uci.slice(4) : undefined };
}

/**
 * Parses the maia-blindness fixture's tab-separated shape: `#`-prefixed
 * preamble lines, one header row, then data rows.
 */
export function loadFixtureRows(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  const dataLines = lines.filter((line) => line.trim().length > 0 && !line.startsWith('#'));
  if (dataLines.length < 2) throw new Error(`--fixture ${filePath} has no data rows past its header`);
  const header = dataLines[0].split('\t');
  return dataLines.slice(1).map((line, idx) => {
    const cells = line.split('\t');
    if (cells.length !== header.length) {
      throw new Error(`--fixture ${filePath} row ${idx + 2}: expected ${header.length} tab-separated fields, got ${cells.length}`);
    }
    const row = Object.fromEntries(header.map((col, i) => [col, cells[i]]));
    return {
      id: row.id,
      fen: row.fen,
      correctMove: row.correct_move,
      evalGapCp: row.eval_gap_cp,
      note: row.note,
      source: row.source,
    };
  });
}

/**
 * Every fixture row's FEN must be a legal position and its recorded move
 * legal in it, verified with `chess.js` — never by eye. THROWS (never calls
 * `process.exit`) so `--self-test` can observe the failure; `main()` catches
 * it, prints it, and returns exit code 1 BEFORE spawning any engine
 * (T-225-01) — a corrupted fixture row must never silently reach an engine.
 */
export async function validateFixtureIntegrity(rows) {
  const { Chess } = await resolveFrontendModule('chess.js');
  const problems = [];
  for (const row of rows) {
    let board;
    try {
      board = new Chess(row.fen);
    } catch (err) {
      problems.push(`${row.id}: illegal FEN (${err.message})`);
      continue;
    }
    const { from, to, promotion } = parseUciMove(row.correctMove);
    try {
      board.move({ from, to, promotion });
    } catch (err) {
      problems.push(`${row.id}: recorded move ${row.correctMove} is illegal in its FEN (${err.message})`);
    }
  }
  if (problems.length > 0) {
    throw new Error(`Fixture integrity failure (T-225-01):\n${problems.map((p) => `  ${p}`).join('\n')}`);
  }
}

// ─── One independent grading call over a deduped (pick, correct) pair ──────

/**
 * ONE `nodeGrade` MultiPV call over the deduped `{move, correctMove}` pair,
 * converted to mover-POV expected score via `evalToExpectedScore` (the same
 * conversion `liveFlaw.ts` and the deleted script's accept rule both use).
 * Called ONCE PER SELECTOR (never shared across bot/analysis) so a change in
 * the analysis pick can never perturb the judged bot grade through a
 * different MultiPV set. Throws (naming nothing itself — the caller adds the
 * row id) when `move` is null or either grade is missing: a null pick or an
 * absent grade must never silently read as a pass.
 */
async function gradePair(engine, fen, move, correctMove, gradeDepth) {
  if (move === null) throw new Error('pick is null');
  const candidateUcis = [...new Set([move, correctMove])];
  const grades = await nodeGrade(engine, fen, candidateUcis, gradeDepth);
  const mover = fen.split(' ')[1] === 'b' ? 'black' : 'white';
  const esFor = (uci) => {
    const grade = grades.get(uci);
    if (grade === undefined) return null;
    return evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
  };
  const esPick = esFor(move);
  const esCorrect = esFor(correctMove);
  if (esPick === null) throw new Error(`missing grade for pick ${move}`);
  if (esCorrect === null) throw new Error(`missing grade for correct move ${correctMove}`);
  return { esPick, esCorrect };
}

// ─── Self-test (parseArgs + fixture integrity only, no engines) ────────────

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
    parseArgs(['--arm', 'a0', '--stop-rule', 'on', '--bogus-flag']);
    check(false, 'unknown flag should throw');
  } catch (err) {
    check(err.message.includes('Unknown flag'), 'unknown flag throws with a named-flag message');
  }

  // --arm is required for a real run.
  try {
    parseArgs(['--stop-rule', 'on']);
    check(false, 'omitting --arm should throw');
  } catch (err) {
    check(/--arm/.test(err.message), 'missing --arm throws mentioning --arm');
  }

  // --stop-rule is required for a real run.
  try {
    parseArgs(['--arm', 'a0']);
    check(false, 'omitting --stop-rule should throw');
  } catch (err) {
    check(/--stop-rule/.test(err.message), 'missing --stop-rule throws mentioning --stop-rule');
  }

  // --stop-rule rejects an unrecognized value.
  try {
    parseArgs(['--arm', 'a0', '--stop-rule', 'sideways']);
    check(false, 'an invalid --stop-rule value should throw');
  } catch (err) {
    check(/stop-rule/i.test(err.message), 'invalid --stop-rule value throws mentioning stop-rule');
  }

  // --help bypasses both requirements.
  try {
    const helpArgs = parseArgs(['--help']);
    check(helpArgs.help === true, '--help bypasses the --arm/--stop-rule requirement');
  } catch {
    check(false, '--help alone should not throw');
  }

  // The default fixture loads exactly 12 rows and passes integrity.
  const defaultRows = loadFixtureRows(resolvePath(DEFAULT_FIXTURE));
  check(defaultRows.length === 12, `default fixture loads exactly 12 rows, got ${defaultRows.length}`);
  try {
    await validateFixtureIntegrity(defaultRows);
    check(true, 'default fixture passes validateFixtureIntegrity');
  } catch (err) {
    check(false, `default fixture should pass validateFixtureIntegrity: ${err.message}`);
  }

  // A corrupted temp copy (one row's correct_move replaced by an illegal
  // move) makes validateFixtureIntegrity throw a message containing that
  // row's id (T-225-01).
  const tmpFile = path.join(os.tmpdir(), `engine-move-quality-self-test-${process.pid}.tsv`);
  try {
    const lines = fs.readFileSync(resolvePath(DEFAULT_FIXTURE), 'utf8').split('\n');
    const dataLineIdx = lines.findIndex((line) => line.trim().length > 0 && !line.startsWith('#') && !line.startsWith('id\t'));
    const cells = lines[dataLineIdx].split('\t');
    const corruptedId = cells[0];
    cells[2] = 'a1a1'; // correct_move column -> illegal move
    lines[dataLineIdx] = cells.join('\t');
    fs.writeFileSync(tmpFile, lines.join('\n'));

    const corruptedRows = loadFixtureRows(tmpFile);
    try {
      await validateFixtureIntegrity(corruptedRows);
      check(false, 'corrupted fixture should throw');
    } catch (err) {
      check(err.message.includes(corruptedId), `corrupted fixture throws mentioning row id ${corruptedId}`);
    }
  } finally {
    fs.rmSync(tmpFile, { force: true });
  }

  return ok;
}

// ─── Main measurement loop ───────────────────────────────────────────────────

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

  const fixtureRows = loadFixtureRows(resolvePath(args.fixture));
  try {
    await validateFixtureIntegrity(fixtureRows); // T-225-01 — before any engine spawns
  } catch (err) {
    console.error(`\n${err.message}\n`);
    return 1;
  }
  console.log(`Fixture integrity: ${fixtureRows.length}/${fixtureRows.length} rows legal (FEN + recorded move).`);

  const { session, ort } = await createMaiaSession();
  const pool = await createGradePool(args.procs);
  const gradeEngine = await spawnStockfish();

  // Review fix (WR-02): a per-row grading error used to escape main() before
  // the cleanup below ran, leaving the Stockfish pool and the grading engine
  // running. The measurement now runs inside try/finally so both always stop.
  try {
    return await measureRows(args, fixtureRows, session, ort, pool, gradeEngine);
  } finally {
    gradeEngine.terminate();
    pool.quitAll();
  }
}

async function measureRows(args, fixtureRows, session, ort, pool, gradeEngine) {
  console.log(
    `\nengine-move-quality — arm=${args.arm} stop-rule=${args.stopRule} nodes=${args.nodes} plies=${args.plies} ` +
      `elo=${args.elo} procs=${args.procs} grade-depth=${args.gradeDepth} margin=${REGRESSION_MARGIN}\n` +
      `fixture=${args.fixture} rows=${fixtureRows.length}\n`,
  );

  const rows = [];
  let botRegressions = 0;
  let analysisRegressions = 0;
  let exactMatches = 0;

  for (const row of fixtureRows) {
    await pool.resetAll();
    resetMaiaRunMemo();
    const providers = makeNodeProviders(session, ort, pool.grade);
    const budget = {
      maxNodes: args.nodes,
      maxPlies: args.plies,
      concurrency: args.procs,
      elo: { w: args.elo, b: args.elo },
      ...(args.stopRule === 'on' ? { stopRule: FLAWCHESS_BOT_STOP_RULE } : {}),
    };

    const startedAt = performance.now();
    const snapshot = await mctsSearch(row.fen, budget, providers, () => {}, new AbortController().signal);
    const wallMs = performance.now() - startedAt;

    const botMove = argmaxLine(snapshot.rankedLines);
    const analysisMove = snapshot.rankedLines[0]?.rootMove ?? null;

    let botGraded;
    let analysisGraded;
    try {
      botGraded = await gradePair(gradeEngine, row.fen, botMove, row.correctMove, args.gradeDepth);
    } catch (err) {
      throw new Error(`row ${row.id} (bot pick): ${err.message}`);
    }
    try {
      analysisGraded = await gradePair(gradeEngine, row.fen, analysisMove, row.correctMove, args.gradeDepth);
    } catch (err) {
      throw new Error(`row ${row.id} (analysis pick): ${err.message}`);
    }

    // es_correct comes from the BOT pair (spec) — the analysis pair's own
    // es_correct is redundant (same fen/correctMove/depth) and discarded, so
    // the two per-selector grades never disagree on what "correct" scores.
    const esCorrect = botGraded.esCorrect;
    const esBot = botGraded.esPick;
    const deltaBot = esBot - esCorrect;
    const verdictBot = deltaBot <= -REGRESSION_MARGIN ? 'regression' : 'pass';

    const esAnalysis = analysisGraded.esPick;
    const deltaAnalysis = esAnalysis - esCorrect;
    const verdictAnalysis = deltaAnalysis <= -REGRESSION_MARGIN ? 'regression' : 'pass';

    if (verdictBot === 'regression') botRegressions++;
    if (verdictAnalysis === 'regression') analysisRegressions++;
    if (botMove === row.correctMove) exactMatches++;

    console.log(
      `  ${row.id.padEnd(14)} bot=${(botMove ?? '').padEnd(6)} analysis=${(analysisMove ?? '').padEnd(6)} ` +
        `es_bot=${esBot.toFixed(3)} es_correct=${esCorrect.toFixed(3)} delta_bot=${deltaBot.toFixed(3)} ${verdictBot}  ` +
        `es_analysis=${esAnalysis.toFixed(3)} delta_analysis=${deltaAnalysis.toFixed(3)} ${verdictAnalysis}`,
    );

    rows.push({
      arm: args.arm,
      stop_rule: args.stopRule,
      id: row.id,
      fen: row.fen,
      correct_move: row.correctMove,
      bot_move: botMove ?? '',
      es_bot: esBot.toFixed(6),
      es_correct: esCorrect.toFixed(6),
      delta_bot: deltaBot.toFixed(6),
      verdict_bot: verdictBot,
      analysis_move: analysisMove ?? '',
      es_analysis: esAnalysis.toFixed(6),
      delta_analysis: deltaAnalysis.toFixed(6),
      verdict_analysis: verdictAnalysis,
      nodes_evaluated: snapshot.nodesEvaluated,
      stop_reason: snapshot.stopReason ?? '',
      wall_ms: wallMs.toFixed(0),
      grade_depth: args.gradeDepth,
      elo: args.elo,
      max_nodes: args.nodes,
    });
  }

  console.log(
    `\nSummary over ${rows.length} rows: bot regressions ${botRegressions}/${rows.length}, ` +
      `analysis regressions ${analysisRegressions}/${rows.length}, bot exact matches ${exactMatches}/${rows.length}`,
  );

  if (args.outDir !== null) {
    const outDir = resolvePath(args.outDir);
    fs.mkdirSync(outDir, { recursive: true });
    const columns = [
      'arm', 'stop_rule', 'id', 'fen', 'correct_move', 'bot_move', 'es_bot', 'es_correct',
      'delta_bot', 'verdict_bot', 'analysis_move', 'es_analysis', 'delta_analysis', 'verdict_analysis',
      'nodes_evaluated', 'stop_reason', 'wall_ms', 'grade_depth', 'elo', 'max_nodes',
    ];
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outPath = path.join(outDir, `engine-move-quality-${args.arm}-stop${args.stopRule}-${stamp}.tsv`);
    const tsv = [
      columns.join('\t'),
      ...rows.map((row) => columns.map((c) => (row[c] === undefined ? '' : String(row[c]))).join('\t')),
    ].join('\n');
    fs.writeFileSync(outPath, `${tsv}\n`);
    console.log(`\nWrote ${outPath}`);
  }

  return 0;
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const code = await main();
  process.exit(code);
}
