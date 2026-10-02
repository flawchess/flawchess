#!/usr/bin/env node
/**
 * build-move-quality-fixture.mjs — D-14 widened move-quality fixture builder
 * (Phase 226).
 *
 * The 12-row `fixtures/engine/maia-blindness.tsv` gate is too small to trust
 * a paired-regression verdict on its own (226-RESEARCH Pattern 4). This tool
 * builds a widened fixture: the 12 maia-blindness rows PLUS `PER_BAND_QUOTA`
 * lichess CC0 puzzles per `BAND_EDGES`-wide rating band, drawn from
 * `fixtures/tagger/detector_fixture_test.csv` and independently verified at
 * `GROUND_TRUTH_DEPTH`/`GROUND_TRUTH_MULTIPV` Stockfish.
 *
 * SELECTION RULE (fixed here, before any generation run — T-226-03):
 *   1. Parse `SOURCE_CSV`; drop any PuzzleId already present in
 *      `BASE_FIXTURE`'s own `source` column (never re-select a base row).
 *   2. Drop rows whose Rating falls outside `[BAND_EDGES[0], BAND_EDGES.at(-1))`.
 *   3. Assign each remaining row a rating band from `BAND_EDGES`.
 *   4. Within each band, order candidates by `sha1Hex(PuzzleId)` ascending
 *      (node:crypto SHA-1 — NEVER Python `hash()` or any per-process-salted
 *      ordering, per the tagger re-seed memory note).
 *   5. Evaluate candidates in that SHA-1 order on a pooled Stockfish
 *      (`createStockfishPool({ size: procs })`), each evaluation starting
 *      from a CLEARED hash table (`setoption name Clear Hash`) so the result
 *      never depends on which pool engine ran it: `setoption name MultiPV
 *      value 2`, `position fen <FEN>`, `go depth <depth>` over ALL legal
 *      moves (no `searchmoves` restriction). Positions with fewer than two
 *      legal moves are skipped.
 *   6. A candidate is KEPT iff the depth-`GROUND_TRUTH_DEPTH` MultiPV-1 move
 *      equals the puzzle's own first solution move (`PV[0]`) AND
 *      `mateAwareGapCp(top, second) >= MIN_GAP_CP` (mover-POV, mate scores
 *      substituted at +/- `MATE_CP_EQUIVALENT`, mirroring `maia-blindness
 *      .tsv`'s own header convention).
 *   7. The first `PER_BAND_QUOTA` keepers per band, IN SHA-1 ORDER,
 *      regardless of completion order — candidates within a band are
 *      evaluated in bounded parallel batches of size `procs` for throughput,
 *      but which ones are KEPT is decided by walking each batch's results in
 *      SHA-1 order and stopping the moment the quota is reached, so the
 *      output is identical no matter how the parallel batch happens to
 *      settle (T-226-03: deterministic regardless of engine scheduling).
 *
 * `--check PATH` re-verifies a generated (or hand-edited) fixture file
 * against the gate's OWN reader/validator (`loadFixtureRows`/
 * `validateFixtureIntegrity` from engine-move-quality.mjs, T-226-04) plus two
 * structural invariants: every maia-blindness base row is still present, and
 * the file has at least `--min-rows` (default `MIN_FIXTURE_ROWS`) rows.
 *
 * Usage:
 *   node --import ./scripts/lib/frontend-alias-hook.mjs scripts/build-move-quality-fixture.mjs \
 *     [--out fixtures/engine/move-quality-226.tsv] [--procs 6] \
 *     [--depth 20] [--per-band 8] \
 *     [--check PATH [--min-rows 50]] \
 *     [--self-test] [--help]
 *
 *   --out         output fixture path (default fixtures/engine/move-quality-226.tsv)
 *   --procs       Stockfish pool size for the d20 verification pass (default 6)
 *   --depth       ground-truth search depth (default 20 — override only for a
 *                 fast smoke run, e.g. --depth 10)
 *   --per-band    keepers per rating band (default 8 — override only for a
 *                 fast smoke run, e.g. --per-band 1)
 *   --check PATH  re-verify an existing fixture file instead of generating one
 *   --min-rows N  minimum row count for --check (default MIN_FIXTURE_ROWS = 50)
 *   --self-test   exercise parseArgs, sha1Hex/ratingBand/mateAwareGapCp/
 *                 parsePuzzleCsv/formatFixtureRow only (no engines spawned)
 *   --help        print this header and exit
 *
 * Full-depth generation (`--depth 20 --per-band 8`, ~55 rows) is orchestrator
 * work for Plan 226-07 — this plan runs only the smoke configuration
 * (`--depth 10 --per-band 1`, 18 rows) to prove the tool end-to-end.
 */
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';

import { createStockfishPool } from './lib/stockfish-pool.mjs';
import { resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { loadFixtureRows, validateFixtureIntegrity } from './engine-move-quality.mjs';

import { parseInfoLine } from '@/hooks/uciParser';
import { MATE_CP_EQUIVALENT } from '@/generated/flawThresholds';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(__dirname, '..');

// ─── Frozen selection-rule constants (T-226-03 — never CLI-reachable except the documented smoke overrides) ──

export const SOURCE_CSV = 'fixtures/tagger/detector_fixture_test.csv';
export const BASE_FIXTURE = 'fixtures/engine/maia-blindness.tsv';
export const BAND_EDGES = [1000, 1200, 1400, 1600, 1800, 2000, 2200];
export const PER_BAND_QUOTA = 8;
export const MIN_GAP_CP = 150;
export const GROUND_TRUTH_DEPTH = 20;
export const GROUND_TRUTH_MULTIPV = 2;
export const MIN_FIXTURE_ROWS = 50;
export const DEFAULT_PROCS = 6;
export const DEFAULT_OUT = 'fixtures/engine/move-quality-226.tsv';

/** Watchdog for the ground-truth `go` (mirrors the other engine harnesses' own convention). */
const GRADE_WATCHDOG_MS = 60_000;

/** The fixture's own tab-separated column header (must match maia-blindness.tsv's). */
const FIXTURE_HEADER = 'id\tfen\tcorrect_move\teval_gap_cp\tnote\tsource';

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
    out: DEFAULT_OUT,
    procs: DEFAULT_PROCS,
    depth: GROUND_TRUTH_DEPTH,
    perBand: PER_BAND_QUOTA,
    check: null,
    minRows: null,
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
      case 'out': args.out = requireFlagValue(value, key); i++; break;
      case 'procs': args.procs = parsePositiveIntFlag(value, key); i++; break;
      case 'depth': args.depth = parsePositiveIntFlag(value, key); i++; break;
      case 'per-band': args.perBand = parsePositiveIntFlag(value, key); i++; break;
      case 'check': args.check = requireFlagValue(value, key); i++; break;
      case 'min-rows': args.minRows = parsePositiveIntFlag(value, key, 0); i++; break;
      default:
        throw new Error(`Unknown flag --${key}`);
    }
  }
  return args;
}

function resolvePath(p) {
  return path.isAbsolute(p) ? p : path.resolve(REPO_ROOT, p);
}

// ─── Pure selection-rule helpers ─────────────────────────────────────────────

/** node:crypto SHA-1 hex digest — NEVER Python `hash()` (per-process-salted, tagger re-seed memory note). */
export function sha1Hex(str) {
  return createHash('sha1').update(str).digest('hex');
}

/** Rating -> `"lo-hi"` band label from `edges`, or `null` when `rating` falls outside `[edges[0], edges.at(-1))`. */
export function ratingBand(rating, edges = BAND_EDGES) {
  for (let i = 0; i < edges.length - 1; i++) {
    const lo = edges[i];
    const hi = edges[i + 1];
    if (rating >= lo && rating < hi) return `${lo}-${hi}`;
  }
  return null;
}

/** Mate-aware mover-POV cp-equivalent: a mate score substitutes +/- MATE_CP_EQUIVALENT, matching maia-blindness.tsv's own header convention. */
function toCpEquivalent(entry) {
  if (entry.mate !== null && entry.mate !== undefined) {
    return entry.mate > 0 ? MATE_CP_EQUIVALENT : -MATE_CP_EQUIVALENT;
  }
  return entry.cp;
}

/** `top`/`second` are `{cp, mate}` in mover POV (raw UCI `info` fields — never white-POV-converted). */
export function mateAwareGapCp(top, second) {
  return toCpEquivalent(top) - toCpEquivalent(second);
}

/** One line of RFC-4180-ish CSV: quoted fields, `""` escaping a literal quote. */
function parseCsvLine(line) {
  const fields = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      fields.push(cur);
      cur = '';
    } else {
      cur += c;
    }
  }
  fields.push(cur);
  return fields;
}

/** Parses `SOURCE_CSV`'s schema (`PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating`) into row objects. */
export function parsePuzzleCsv(content) {
  const lines = content.split('\n').filter((line) => line.length > 0);
  if (lines.length === 0) return [];
  const header = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    const row = Object.fromEntries(header.map((col, i) => [col, cells[i]]));
    return {
      puzzleId: row.PuzzleId,
      fen: row.FEN,
      preFlawFen: row.PreFlawFEN,
      firstMove: row.FirstMove,
      pv: row.PV,
      themes: row.Themes,
      rating: Number.parseInt(row.Rating, 10),
    };
  });
}

/** Formats one output fixture row in maia-blindness.tsv's own column order. */
export function formatFixtureRow({ id, fen, correctMove, evalGapCp, note, source }) {
  return [id, fen, correctMove, evalGapCp, note, source].join('\t');
}

/** PuzzleIds already present in BASE_FIXTURE's `source` column (`PuzzleId=<id>`) — never re-select these. */
function excludedPuzzleIds(baseRows) {
  const ids = new Set();
  const pattern = /PuzzleId=([^\s,]+)/;
  for (const row of baseRows) {
    const match = pattern.exec(row.source);
    if (match) ids.add(match[1]);
  }
  return ids;
}

// ─── Engine evaluation (d`depth` MultiPV-2 over all legal moves, Clear Hash first) ──

/**
 * Runs ONE `go depth <depth>` with `MultiPV 2` over ALL legal moves (no
 * `searchmoves` restriction — unlike `buildGradeGoCommand`'s candidate-
 * restricted grading path, this needs the engine's own top-2 over the whole
 * position) on a pooled engine, starting from a cleared hash table so the
 * result never depends on which engine in the pool ran it. Lines are
 * collected keyed by MULTIPV RANK (not by move UCI): the engine's reported
 * top-2 moves can differ between depth iterations as the search deepens, so
 * keying by rank and overwriting on every iteration keeps only the FINAL
 * iteration's actual rank-1/rank-2 lines — keying by move would leave stale
 * lower-depth entries for moves no longer in the final top-2.
 */
async function runGroundTruthGo(engine, fen, depth) {
  const collected = new Map(); // multipv rank -> { uci, cp, mate }
  const off = engine.onLine((line) => {
    if (!line.startsWith('info ')) return;
    const parsed = parseInfoLine(line);
    if (parsed === null || parsed.bound !== 'exact') return;
    const uci = parsed.pv[0];
    if (uci === undefined) return;
    collected.set(parsed.multipv, { uci, cp: parsed.scoreCp, mate: parsed.scoreMate });
  });
  engine.send('setoption name Clear Hash');
  engine.send(`setoption name MultiPV value ${GROUND_TRUTH_MULTIPV}`);
  engine.send(`position fen ${fen}`);
  engine.send(`go depth ${depth}`);
  try {
    await engine.waitFor((line) => line.startsWith('bestmove'), GRADE_WATCHDOG_MS);
  } finally {
    off();
  }
  return collected;
}

/** One candidate's verdict: `{status: 'skip' | 'reject-top-move' | 'reject-gap' | 'keep', topUci, gap}`. */
async function evaluateCandidate(pool, Chess, candidate, depth) {
  const board = new Chess(candidate.fen);
  if (board.moves().length < 2) return { status: 'skip' };

  const collected = await pool.run((engine) => runGroundTruthGo(engine, candidate.fen, depth));
  const top = collected.get(1);
  const second = collected.get(2);
  if (top === undefined || second === undefined) return { status: 'skip' };

  const correctUci = candidate.pv.split(' ')[0];
  const gap = mateAwareGapCp(top, second);
  if (top.uci !== correctUci) return { status: 'reject-top-move', topUci: top.uci, gap };
  if (gap < MIN_GAP_CP) return { status: 'reject-gap', topUci: top.uci, gap };
  return { status: 'keep', topUci: top.uci, gap };
}

/**
 * Evaluates one band's SHA-1-ordered candidates in batches of `procs`,
 * keeping the first `quota` in SHA-1 order regardless of which batch member
 * finishes first (T-226-03). Stops issuing new batches once the quota is
 * reached, even mid-band.
 */
async function processBand(band, candidates, pool, Chess, depth, quota) {
  const stats = { band, evaluated: 0, skipped: 0, kept: 0, rejectedTopMove: 0, rejectedGap: 0 };
  const kept = [];
  for (let start = 0; start < candidates.length && kept.length < quota; start += pool.size) {
    const batch = candidates.slice(start, start + pool.size);
    const results = await Promise.all(batch.map((candidate) => evaluateCandidate(pool, Chess, candidate, depth)));
    // Decide IN SHA-1 (batch) ORDER, never completion order — this is what
    // makes the output independent of engine scheduling.
    for (let i = 0; i < batch.length; i++) {
      if (kept.length >= quota) break;
      const candidate = batch[i];
      const result = results[i];
      if (result.status === 'skip') {
        stats.skipped += 1;
        continue;
      }
      stats.evaluated += 1;
      if (result.status === 'reject-top-move') {
        stats.rejectedTopMove += 1;
      } else if (result.status === 'reject-gap') {
        stats.rejectedGap += 1;
      } else {
        stats.kept += 1;
        kept.push({ candidate, gap: result.gap });
      }
    }
  }
  return { stats, kept };
}

// ─── --check mode ─────────────────────────────────────────────────────────

async function runCheck(checkPath, minRows) {
  let rows;
  try {
    rows = loadFixtureRows(resolvePath(checkPath));
  } catch (err) {
    console.error(`FIXTURE-CHECK failed: ${err.message}`);
    return 1;
  }
  try {
    await validateFixtureIntegrity(rows);
  } catch (err) {
    console.error(`FIXTURE-CHECK failed: ${err.message}`);
    return 1;
  }
  const baseRows = loadFixtureRows(resolvePath(BASE_FIXTURE));
  const rowIds = new Set(rows.map((r) => r.id));
  const missingBaseIds = baseRows.map((r) => r.id).filter((id) => !rowIds.has(id));
  if (missingBaseIds.length > 0) {
    console.error(`FIXTURE-CHECK failed: missing base maia-blindness rows: ${missingBaseIds.join(', ')}`);
    return 1;
  }
  const effectiveMinRows = minRows ?? MIN_FIXTURE_ROWS;
  if (rows.length < effectiveMinRows) {
    console.error(`FIXTURE-CHECK failed: expected at least ${effectiveMinRows} rows, got ${rows.length}`);
    return 1;
  }
  console.log(`FIXTURE-CHECK rows=${rows.length} ok`);
  return 0;
}

// ─── Self-test (pure helpers only, no engines) ───────────────────────────────

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
    parseArgs(['--bogus-flag']);
    check(false, 'unknown flag should throw');
  } catch (err) {
    check(err.message.includes('Unknown flag'), 'unknown flag throws with a named-flag message');
  }

  // --help bypasses everything.
  const helpArgs = parseArgs(['--help']);
  check(helpArgs.help === true, '--help parses');

  // sha1Hex matches a well-known SHA-1 test vector.
  check(sha1Hex('abc') === 'a9993e364706816aba3e25717850c26c9cd0d89d', 'sha1Hex matches the NIST "abc" test vector');

  // SHA-1 ordering is stable across repeated sorts and differs from input order.
  {
    const ids = ['puzzleAlpha', 'puzzleBravo', 'puzzleCharlie'];
    const byHash = (a, b) => (sha1Hex(a) < sha1Hex(b) ? -1 : sha1Hex(a) > sha1Hex(b) ? 1 : 0);
    const sortedOnce = [...ids].sort(byHash);
    const sortedTwice = [...ids].sort(byHash);
    check(JSON.stringify(sortedOnce) === JSON.stringify(sortedTwice), 'SHA-1 ordering is stable across repeated sorts');
    check(JSON.stringify(sortedOnce) !== JSON.stringify(ids), `SHA-1 ordering differs from input order, got ${JSON.stringify(sortedOnce)}`);
  }

  // ratingBand: edges are half-open [lo, hi).
  check(ratingBand(1000) === '1000-1200', 'ratingBand(1000) is the first band (inclusive lower edge)');
  check(ratingBand(1199) === '1000-1200', 'ratingBand(1199) stays in the first band');
  check(ratingBand(1200) === '1200-1400', 'ratingBand(1200) rolls into the next band (exclusive upper edge)');
  check(ratingBand(999) === null, 'ratingBand(999) is out of range (below BAND_EDGES[0])');
  check(ratingBand(2200) === null, 'ratingBand(2200) is out of range (at BAND_EDGES.at(-1), exclusive)');

  // mateAwareGapCp: plain cp, and a mate substituted at MATE_CP_EQUIVALENT.
  check(mateAwareGapCp({ cp: 100, mate: null }, { cp: -50, mate: null }) === 150, 'mateAwareGapCp on plain cp values');
  check(
    mateAwareGapCp({ cp: null, mate: 3 }, { cp: 200, mate: null }) === MATE_CP_EQUIVALENT - 200,
    'mateAwareGapCp substitutes a winning mate at +MATE_CP_EQUIVALENT',
  );
  check(
    mateAwareGapCp({ cp: 200, mate: null }, { cp: null, mate: -2 }) === 200 - -MATE_CP_EQUIVALENT,
    'mateAwareGapCp substitutes a losing mate at -MATE_CP_EQUIVALENT',
  );

  // CSV parsing of a quoted row (comma inside a quoted field).
  {
    const csv = 'PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating\nid1,fen1,pre1,fm1,"d5e7 g8h7","theme,withcomma",1500\n';
    const rows = parsePuzzleCsv(csv);
    check(rows.length === 1, `parsePuzzleCsv parses exactly one data row, got ${rows.length}`);
    check(rows[0].themes === 'theme,withcomma', `quoted comma survives, got ${JSON.stringify(rows[0].themes)}`);
    check(rows[0].pv === 'd5e7 g8h7', `quoted space-containing field survives, got ${JSON.stringify(rows[0].pv)}`);
    check(rows[0].rating === 1500, `rating parses as a number, got ${rows[0].rating}`);
  }

  // formatFixtureRow round-trips through loadFixtureRows + validateFixtureIntegrity via a temp file.
  {
    const testFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const rowLine = formatFixtureRow({ id: 'rt1', fen: testFen, correctMove: 'e2e4', evalGapCp: 200, note: 'test note', source: 'test source' });
    const tmpFile = path.join(os.tmpdir(), `build-move-quality-fixture-self-test-${process.pid}.tsv`);
    fs.writeFileSync(tmpFile, `${FIXTURE_HEADER}\n${rowLine}\n`);
    try {
      const rtRows = loadFixtureRows(tmpFile);
      check(rtRows.length === 1 && rtRows[0].id === 'rt1' && rtRows[0].correctMove === 'e2e4', 'formatFixtureRow round-trips through loadFixtureRows');
      await validateFixtureIntegrity(rtRows);
      check(true, 'formatFixtureRow round-trip passes validateFixtureIntegrity');
    } catch (err) {
      check(false, `formatFixtureRow round-trip should pass validateFixtureIntegrity: ${err.message}`);
    } finally {
      fs.rmSync(tmpFile, { force: true });
    }
  }

  return ok;
}

// ─── Generation mode ──────────────────────────────────────────────────────

function fixtureHeaderComment() {
  return [
    '# move-quality-226.tsv — Phase 226 D-14 widened move-quality fixture.',
    '#',
    `# Built by scripts/build-move-quality-fixture.mjs from ${SOURCE_CSV} (lichess CC0`,
    '# puzzle corpus) plus the 12 fixtures/engine/maia-blindness.tsv rows verbatim.',
    '#',
    '# SELECTION RULE (fixed before generation, T-226-03 — see the script header for',
    '# the full rationale): drop PuzzleIds already in maia-blindness; drop Rating',
    `# outside [${BAND_EDGES[0]}, ${BAND_EDGES[BAND_EDGES.length - 1]}); band edges ${JSON.stringify(BAND_EDGES)};`,
    '# within each band order by sha1Hex(PuzzleId) ascending (node:crypto, never',
    `# Python hash()); keep iff the depth-${GROUND_TRUTH_DEPTH} MultiPV-${GROUND_TRUTH_MULTIPV} top move equals the`,
    `# puzzle's own PV[0] AND mateAwareGapCp(top, second) >= ${MIN_GAP_CP} (mover POV,`,
    '# mate substituted at +/- MATE_CP_EQUIVALENT); first PER_BAND_QUOTA keepers per',
    '# band in SHA-1 order, regardless of parallel-batch completion order.',
    '#',
    '# Columns (tab-separated), mirroring maia-blindness.tsv:',
    '#   id            PuzzleId (lichess CC0) or the maia-blindness base row id',
    '#   fen           the position to move from',
    '#   correct_move  the objectively-best move in UCI (PV[0] for a puzzle row)',
    '#   eval_gap_cp   |eval(correct_move) - eval(runner_up)| at the verification',
    '#                 depth, mover-POV cp-equivalent (mate substituted at',
    '#                 MATE_CP_EQUIVALENT)',
    '#   note          why the row is in the fixture',
    '#   source        provenance: lichess CC0 puzzle id + source file + rating, or',
    '#                 the verified maia-blindness anchor',
  ].join('\n');
}

async function runGenerate(args) {
  const baseFixturePath = resolvePath(BASE_FIXTURE);
  const baseRows = loadFixtureRows(baseFixturePath);
  const baseLines = fs
    .readFileSync(baseFixturePath, 'utf8')
    .split('\n')
    .filter((line) => line.trim().length > 0 && !line.startsWith('#') && line !== FIXTURE_HEADER);
  const excludedIds = excludedPuzzleIds(baseRows);

  const puzzleRows = parsePuzzleCsv(fs.readFileSync(resolvePath(SOURCE_CSV), 'utf8'))
    .filter((row) => !excludedIds.has(row.puzzleId))
    .filter((row) => Number.isFinite(row.rating))
    .map((row) => ({ ...row, band: ratingBand(row.rating, BAND_EDGES) }))
    .filter((row) => row.band !== null);

  const byBand = new Map();
  for (const row of puzzleRows) {
    const list = byBand.get(row.band) ?? [];
    list.push(row);
    byBand.set(row.band, list);
  }
  for (const list of byBand.values()) {
    list.sort((a, b) => {
      const ha = sha1Hex(a.puzzleId);
      const hb = sha1Hex(b.puzzleId);
      return ha < hb ? -1 : ha > hb ? 1 : 0;
    });
  }

  const pool = await createStockfishPool({ size: args.procs });
  const { Chess } = await resolveFrontendModule('chess.js');

  const bandOrder = [];
  for (let i = 0; i < BAND_EDGES.length - 1; i++) bandOrder.push(`${BAND_EDGES[i]}-${BAND_EDGES[i + 1]}`);

  const generatedLines = [];
  const allStats = [];
  try {
    for (const band of bandOrder) {
      const candidates = byBand.get(band) ?? [];
      const { stats, kept } = await processBand(band, candidates, pool, Chess, args.depth, args.perBand);
      allStats.push(stats);
      for (const { candidate, gap } of kept) {
        generatedLines.push(
          formatFixtureRow({
            id: candidate.puzzleId,
            fen: candidate.fen,
            correctMove: candidate.pv.split(' ')[0],
            evalGapCp: gap,
            note: `lichess puzzle, themes: ${candidate.themes}`,
            source: `lichess CC0 puzzle ${candidate.puzzleId}, ${SOURCE_CSV}, rating ${candidate.rating}`,
          }),
        );
      }
    }
  } finally {
    pool.quitAll();
  }

  console.log('\nband       evaluated  kept  rejected_top_move  rejected_gap  skipped');
  for (const s of allStats) {
    console.log(
      `${s.band.padEnd(11)}${String(s.evaluated).padEnd(11)}${String(s.kept).padEnd(6)}${String(s.rejectedTopMove).padEnd(20)}${String(s.rejectedGap).padEnd(14)}${s.skipped}`,
    );
  }

  const outPath = resolvePath(args.out);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  const content = [fixtureHeaderComment(), FIXTURE_HEADER, ...baseLines, ...generatedLines].join('\n');
  fs.writeFileSync(outPath, `${content}\n`);
  console.log(`\nWrote ${outPath} (${baseLines.length + generatedLines.length} rows)`);

  return 0;
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
  if (args.check !== null) {
    return runCheck(args.check, args.minRows);
  }
  return runGenerate(args);
}

if (process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const code = await main();
  process.exit(code);
}
