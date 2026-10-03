#!/usr/bin/env node
/**
 * calibration-ledger-schema.check.mjs — structural check that D-08's ledger
 * schema change (`elapsed_ms`/`mean_move_ms` columns appended to
 * `RAW_LEDGER_COLUMNS`) round-trips through `ledgerRowLine` ->
 * `parsePriorLedgerRow`, that a pre-D-08 (19-column) ledger header is
 * REFUSED loudly by `readPriorLedgerRows` rather than silently mis-parsed
 * into shifted fields, and that the existing `--resume` anchor-pool guard
 * (`applyPriorLedgerRows`, exercised end-to-end via the real CLI) survives
 * the D-08 append unweakened (Phase 199, Plan 01, Task 2).
 *
 * Phase 227 (D-15, T-227-09) extends the contract to 22 columns: `dispatch_mode`
 * is appended LAST, round-trips, and `--resume` under a different
 * `--dispatch-mode` is refused (scenario e) before any engine bring-up.
 *
 * No real Maia/Stockfish session anywhere in this file — scenarios (a)-(c)
 * are pure in-process function calls against small synthetic fixtures;
 * scenario (d) spawns the harness CLI itself with `--resume`, which throws
 * on the anchor-pool guard BEFORE any engine bring-up (see `main()`:
 * `readPriorLedgerRows`/`applyPriorLedgerRows` run before
 * `setupHarnessEngines`), so no engine process is ever started.
 *
 * Run via: node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-ledger-schema.check.mjs
 */
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { RAW_LEDGER_COLUMNS, ledgerRowLine, openLedgerWriter, parsePriorLedgerRow, readPriorLedgerRows } from '../calibration-harness.mjs';
import { OPENING_BOOK } from './calibration-openings.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS_PATH = path.join(__dirname, '..', 'calibration-harness.mjs');
const ALIAS_HOOK_PATH = path.join(__dirname, 'frontend-alias-hook.mjs');

// ─── (a) Column contract: exactly 22 columns, D-08's two + D-15's one at the END ─

// The pre-D-08 19-column list, asserted in full (not just spot-checked) so a
// future mid-list insertion of `elapsed_ms`/`mean_move_ms` fails HERE rather
// than silently corrupting --resume at run time.
const PRE_D08_COLUMNS = [
  'pass',
  'bot_elo',
  'bot_blend',
  'anchor',
  'result',
  'reason',
  'plies',
  'game_index',
  'bot_is_white',
  'opening',
  'seed',
  'git_sha',
  'bot_eval_count',
  'cp_loss_sum',
  'blunder_count',
  'sf_comparable',
  'sf_agree',
  'maia_comparable',
  'maia_agree',
];

assert.equal(RAW_LEDGER_COLUMNS.length, 22, `RAW_LEDGER_COLUMNS must have exactly 22 columns, got ${RAW_LEDGER_COLUMNS.length}`);
assert.deepEqual(
  RAW_LEDGER_COLUMNS.slice(0, 19),
  PRE_D08_COLUMNS,
  'the first 19 RAW_LEDGER_COLUMNS entries must be byte-identical to the pre-D-08 list (D-08 appends, never inserts)',
);
assert.equal(RAW_LEDGER_COLUMNS[19], 'elapsed_ms', `index 19 must be elapsed_ms, got ${RAW_LEDGER_COLUMNS[19]}`);
assert.equal(RAW_LEDGER_COLUMNS[20], 'mean_move_ms', `index 20 must be mean_move_ms, got ${RAW_LEDGER_COLUMNS[20]}`);
assert.equal(RAW_LEDGER_COLUMNS[21], 'dispatch_mode', `index 21 (the LAST column) must be dispatch_mode, got ${RAW_LEDGER_COLUMNS[21]}`);
console.log('PASS: column contract — RAW_LEDGER_COLUMNS is 22 columns, elapsed_ms/mean_move_ms/dispatch_mode appended at the end');

// ─── (b) Round trip: ledgerRowLine -> parsePriorLedgerRow preserves timing ─────

/** A fully-populated synthetic ledger row carrying every field ledgerRowLine reads. */
function fixtureRow(overrides = {}) {
  return {
    pass: 'measure',
    botElo: 1500,
    botBlend: 0.5,
    anchor: 'maia1500',
    result: 'win',
    reason: 'checkmate',
    plies: 42,
    gameIndex: 3,
    botIsWhite: true,
    opening: 'Italian Game',
    seed: 1,
    gitSha: 'fixturesha',
    nearFree: {
      botEvalCount: 10,
      cpLossSum: 123.45,
      blunderCount: 1,
      sfComparable: 10,
      sfAgree: 5,
      maiaComparable: 10,
      maiaAgree: 7,
    },
    elapsedMs: 12345,
    meanMoveMs: 678.9,
    dispatchMode: 'round',
    ...overrides,
  };
}

{
  const row = fixtureRow();
  const line = ledgerRowLine(row);
  const parsed = parsePriorLedgerRow(line, 'fixture.tsv');
  assert.equal(parsed.elapsedMs, row.elapsedMs, `round-tripped elapsedMs mismatch: expected ${row.elapsedMs}, got ${parsed.elapsedMs}`);
  assert.equal(parsed.meanMoveMs, row.meanMoveMs, `round-tripped meanMoveMs mismatch: expected ${row.meanMoveMs}, got ${parsed.meanMoveMs}`);
  assert.equal(parsed.dispatchMode, 'round', `round-tripped dispatchMode mismatch: expected round, got ${parsed.dispatchMode}`);
  const continuousRow = fixtureRow({ dispatchMode: 'continuous' });
  const continuousParsed = parsePriorLedgerRow(ledgerRowLine(continuousRow), 'fixture.tsv');
  assert.equal(continuousParsed.dispatchMode, 'continuous', `round-tripped dispatchMode mismatch: expected continuous, got ${continuousParsed.dispatchMode}`);
  assert.throws(
    () => ledgerRowLine(fixtureRow({ dispatchMode: undefined })),
    /Invalid dispatch mode/,
    'a row without a valid dispatchMode must never be written to the ledger (D-15)',
  );
  console.log('PASS: round trip — a populated elapsedMs/meanMoveMs/dispatchMode row round-trips through ledgerRowLine -> parsePriorLedgerRow');
}

{
  // A blend-0 null-control game with zero bot moves reconstructs meanMoveMs
  // as null, not NaN (Number.parseFloat('') is NaN — the reconstruction must
  // special-case the empty cell).
  const row = fixtureRow({ meanMoveMs: null });
  const line = ledgerRowLine(row);
  // mean_move_ms is no longer the last column (dispatch_mode is), so the empty
  // cell sits between two tabs directly before the mode.
  assert.ok(line.endsWith('\t\tround'), `a null meanMoveMs must render as an EMPTY TSV cell before dispatch_mode, got line ending ${JSON.stringify(line.slice(-12))}`);
  const parsed = parsePriorLedgerRow(line, 'fixture.tsv');
  assert.equal(parsed.meanMoveMs, null, `a null meanMoveMs must reconstruct as null, got ${parsed.meanMoveMs} (NaN would be the un-special-cased bug)`);
  console.log('PASS: round trip — a null meanMoveMs renders as an empty cell and reconstructs as null (never NaN)');
}

// ─── (c) Deliberate schema-drift refusal: a pre-D-08 header is REFUSED loudly ──
// This refusal is INTENTIONAL (T-199-01) — the --resume header check is a
// by-POSITION, exact-order comparison against the current RAW_LEDGER_COLUMNS,
// not a by-name lookup, so a pre-D-08 (19-column) ledger CANNOT silently
// mis-parse into shifted fields. A future reader must not "fix" this by
// making the check name-tolerant — the fail-loud behavior is the point.
{
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-ledger-schema-check-'));
  const preD08Path = path.join(tmpDir, 'pre-d08.tsv');
  try {
    const preD08Row = [
      'measure', '1500', '0.5', 'maia1500', 'win', 'checkmate', '42', '3', '1',
      'Italian Game', '1', 'fixturesha', '10', '123.45', '1', '10', '5', '10', '7',
    ].join('\t');
    fs.writeFileSync(preD08Path, `${PRE_D08_COLUMNS.join('\t')}\n${preD08Row}\n`, 'utf8');

    assert.throws(
      () => readPriorLedgerRows(preD08Path),
      /header does not match the current schema/,
      'readPriorLedgerRows must THROW (not silently mis-parse) a pre-D-08 19-column ledger header',
    );
    console.log('PASS: schema-drift refusal — a pre-D-08 19-column header throws rather than silently mis-parsing (T-199-01)');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

{
  // Phase 227 D-15 (Pitfall 10): a 21-column (pre-227) ledger lacks dispatch_mode,
  // so its games cannot be attributed to an arm. Refused loudly, naming the column.
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-ledger-schema-check-'));
  const pre227Path = path.join(tmpDir, 'pre-227.tsv');
  try {
    fs.writeFileSync(pre227Path, `${RAW_LEDGER_COLUMNS.slice(0, 21).join('\t')}\n`, 'utf8');
    assert.throws(
      () => readPriorLedgerRows(pre227Path),
      /dispatch_mode column/,
      'a pre-227 21-column ledger must be refused with a message naming the dispatch_mode column',
    );
    console.log('PASS: pre-227 refusal — a 21-column ledger without dispatch_mode is refused loudly (D-15)');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

// ─── (d) Anchor-pool guard survives the D-08 append ────────────────────────────
// Exercised end-to-end via the real CLI (not a parallel re-implementation of
// the guard) because the anchor-pool check lives in `applyPriorLedgerRows`,
// which is internal to main()'s --resume path, not one of the five names
// this phase exports. `main()` calls `readPriorLedgerRows` then
// `applyPriorLedgerRows` BEFORE `setupHarnessEngines` (calibration-harness.mjs
// ~line 1648-1677), so this throws fast, before any engine process starts.
{
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-ledger-schema-check-'));
  const anchorMismatchPath = path.join(tmpDir, 'anchor-mismatch.tsv');
  try {
    const gameIndex = 0;
    const opening = OPENING_BOOK[gameIndex % OPENING_BOOK.length].name;
    const botIsWhite = gameIndex % 2 === 0;
    const rowLine = ledgerRowLine({
      pass: 'measure',
      botElo: 1500,
      botBlend: 0.5,
      anchor: 'not_in_the_anchor_pool',
      result: 'win',
      reason: 'checkmate',
      plies: 10,
      gameIndex,
      botIsWhite,
      opening,
      seed: 1,
      gitSha: 'fixturesha',
      nearFree: { botEvalCount: 5, cpLossSum: 10, blunderCount: 0, sfComparable: 5, sfAgree: 3, maiaComparable: 5, maiaAgree: 4 },
      elapsedMs: 1000,
      meanMoveMs: 100,
      dispatchMode: 'round',
    });
    fs.writeFileSync(anchorMismatchPath, `${RAW_LEDGER_COLUMNS.join('\t')}\n${rowLine}\n`, 'utf8');

    let threw = false;
    let stderr = '';
    try {
      execFileSync(
        process.execPath,
        ['--import', ALIAS_HOOK_PATH, HARNESS_PATH, '--elo', '1500', '--blends', '0.5', '--anchors', 'maia1500', '--seed', '1', '--resume', anchorMismatchPath],
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 5000 },
      );
    } catch (err) {
      threw = true;
      stderr = `${err.stderr ?? ''}${err.message ?? ''}`;
    }
    assert.ok(threw, '--resume against a ledger whose anchor is absent from --anchors must make the CLI exit non-zero');
    assert.match(
      stderr,
      /not in the current --anchors set/,
      `--resume must refuse with the anchor-pool guard message, got stderr: ${stderr}`,
    );
    console.log('PASS: anchor-pool guard survives — --resume refuses a ledger row whose anchor is outside the current --anchors set (T-199-02)');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

// ─── (e) Dispatch-mode guard: --resume under a different mode is REFUSED ───────
// Phase 227 D-15 / T-227-09. The ledger's only row used dispatch_mode=round; the
// CLI is run with `--dispatch-mode continuous --resume <ledger>`. ORDER (chosen
// so the check does not depend on Plan 227-10): main() runs the --resume
// refusals (readPriorLedgerRows/applyPriorLedgerRows) BEFORE
// assertDispatchModeLive and before setupHarnessEngines, so the mode-mismatch
// refusal fires first, and today's probe (exit 3 for continuous until 227-10
// lands the loop) is never reached. The assertion is on the message naming the
// mode mismatch, so a different pre-engine refusal cannot satisfy it.
{
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-ledger-schema-check-'));
  const modeMismatchPath = path.join(tmpDir, 'mode-mismatch.tsv');
  try {
    const gameIndex = 0;
    const rowLine = ledgerRowLine(
      fixtureRow({
        anchor: 'maia1500',
        gameIndex,
        botIsWhite: gameIndex % 2 === 0,
        opening: OPENING_BOOK[gameIndex % OPENING_BOOK.length].name,
        dispatchMode: 'round',
      }),
    );
    fs.writeFileSync(modeMismatchPath, `${RAW_LEDGER_COLUMNS.join('\t')}\n${rowLine}\n`, 'utf8');

    let threw = false;
    let stderr = '';
    try {
      execFileSync(
        process.execPath,
        [
          '--import', ALIAS_HOOK_PATH, HARNESS_PATH,
          '--elo', '1500', '--blends', '0.5', '--anchors', 'maia1500', '--seed', '1',
          '--dispatch-mode', 'continuous', '--resume', modeMismatchPath,
        ],
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 5000 },
      );
    } catch (err) {
      threw = true;
      stderr = `${err.stderr ?? ''}${err.message ?? ''}`;
    }
    assert.ok(threw, '--resume --dispatch-mode continuous against a round ledger must make the CLI exit non-zero');
    assert.match(
      stderr,
      /dispatch_mode mismatch/,
      `--resume must refuse with the dispatch-mode mismatch message, got stderr: ${stderr}`,
    );
    console.log('PASS: dispatch-mode guard — --resume refuses a ledger whose rows used a different dispatch_mode before engine bring-up (T-227-09)');

    // Control: the fixture row reads back as round, so the requested continuous
    // mode above is the only difference between the ledger and the CLI call.
    assert.equal(
      parsePriorLedgerRow(rowLine, modeMismatchPath).dispatchMode,
      'round',
      'the fixture ledger row must read back as round so the mismatch above is the only difference',
    );
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

// Sanity: openLedgerWriter is importable (per this phase's five newly-exported names) —
// a minimal smoke exercise, not a full round trip (covered by scenario (b) above).
{
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'calibration-ledger-schema-check-'));
  const writerPath = path.join(tmpDir, 'writer-smoke.tsv');
  try {
    const writer = openLedgerWriter(writerPath);
    writer.writeRow(fixtureRow());
    await writer.close();
    const content = fs.readFileSync(writerPath, 'utf8');
    assert.equal(content.split('\n')[0], RAW_LEDGER_COLUMNS.join('\t'), 'openLedgerWriter must write the current RAW_LEDGER_COLUMNS header');
    console.log('PASS: openLedgerWriter smoke — writes the current 22-column header + a row');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

console.log('OK: calibration-ledger-schema.check.mjs — all D-08 ledger schema invariants pinned.');
process.exit(0);
