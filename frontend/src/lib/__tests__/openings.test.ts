/**
 * openings.ts unit tests (PLAY-11 / 169.5-01).
 *
 * Two independent things are tested here:
 * 1. A standing property test that every line in the REAL shipped
 *    frontend/public/openings.tsv corpus replays legally through chess.js
 *    with byte-identical canonical SAN — the guard against a book that
 *    silently matches nothing (see 169.5-RESEARCH.md's empirical
 *    verification and 169.5-VALIDATION.md non-inferable check #4). This
 *    reads the TSV directly off disk and replays it through chess.js
 *    independently of openings.ts — it validates the ASSET against
 *    chess.js, not the module's own parsing.
 * 2. openings.ts's buildLookup()-derived prefixSet/fullLineMap, exercised
 *    both against a synthetic two-row TSV (pins the prefix-expansion logic
 *    itself, corpus-independent) and against the real shipped TSV (proves
 *    the real asset produces the expected prefix membership and that
 *    findOpening() — Task 1's refactor target — still works).
 *
 * buildLookup() caches its promise at module scope, so a synthetic-TSV test
 * must not be poisoned by a prior real-TSV test's cached promise (or vice
 * versa). Each test re-imports openings.ts fresh via vi.resetModules() +
 * dynamic import AFTER installing that test's own fetch stub (mirrors the
 * resetModules precedent in sounds.test.ts) — never reuse a static
 * top-of-file `import { ... } from '../openings'`.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { Chess } from 'chess.js';

const REAL_TSV = readFileSync(new URL('../../../public/openings.tsv', import.meta.url), 'utf8');

function stubFetch(text: string): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ text: () => Promise.resolve(text) })),
  );
}

async function loadOpenings(text: string): Promise<typeof import('../openings')> {
  vi.resetModules();
  stubFetch(text);
  return import('../openings');
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

/** Mirrors openings.ts's own pgnToSanSequence — reimplemented here (not
 * imported) because this test validates the raw TSV asset against chess.js,
 * independently of openings.ts's own parsing. */
function pgnToSanTokens(pgn: string): string[] {
  return pgn
    .replace(/\d+\./g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .filter(Boolean);
}

interface ParityFailure {
  line: number;
  eco: string;
  ply: number;
  tsvSan: string;
  chessJsSan: string | null;
}

// This whole-corpus replay is pure synchronous CPU work over 3000+ opening
// lines (~2s in isolation). Under the full parallel `vitest run` all cores are
// saturated, so its wall-clock can blow past Vitest's 5s default testTimeout
// and flake with "Test timed out" — even though nothing is actually wrong. Give
// it generous headroom (15x the isolated runtime) rather than trimming coverage.
const CORPUS_PARITY_TIMEOUT_MS = 30_000;

describe('SAN parity (whole corpus)', () => {
  it('every line in the shipped openings.tsv replays legally through chess.js with byte-identical SAN', () => {
    const lines = REAL_TSV.split('\n');
    const failures: ParityFailure[] = [];
    let rowCount = 0;

    for (let i = 1; i < lines.length; i++) {
      // safe: loop bound guarantees i < lines.length
      const line = lines[i]!.trim();
      if (!line) continue;
      const parts = line.split('\t');
      const eco = parts[0];
      const name = parts[1];
      const pgn = parts[2];
      if (!eco || !name || !pgn) continue;
      rowCount++;

      const tokens = pgnToSanTokens(pgn);
      const chess = new Chess();
      for (let ply = 0; ply < tokens.length; ply++) {
        const tsvSan = tokens[ply]!;
        let move;
        try {
          move = chess.move(tsvSan);
        } catch {
          failures.push({ line: i + 1, eco, ply, tsvSan, chessJsSan: null });
          break;
        }
        if (move.san !== tsvSan) {
          failures.push({ line: i + 1, eco, ply, tsvSan, chessJsSan: move.san });
          break;
        }
      }
    }

    // A truncated/empty asset (broken fetch stub, moved file) must fail
    // loudly, not pass vacuously on zero rows.
    expect(rowCount).toBeGreaterThan(3000);
    // Array assertion (not a boolean) so a regression NAMES the offending
    // ECO line instead of just printing `false`.
    expect(failures).toEqual([]);
  }, CORPUS_PARITY_TIMEOUT_MS);
});

describe('prefix set', () => {
  it('derives exactly the expected prefixes from a synthetic two-row TSV', async () => {
    const synthetic = [
      'eco\tname\tpgn',
      'X01\tTest Line One\t1. e4 c6 2. d4 d5',
      'X02\tTest Line Two\t1. d4',
    ].join('\n');
    const { loadOpeningPrefixSet } = await loadOpenings(synthetic);

    const prefixSet = await loadOpeningPrefixSet();

    // Exact set-equality, not a has()-only spot-check — a bug that inserts
    // only the full line (today's pre-Task-1 behavior) must make this red.
    expect(prefixSet).toEqual(new Set(['e4', 'e4 c6', 'e4 c6 d4', 'e4 c6 d4 d5', 'd4']));
  });

  it('the real shipped TSV contains common ECO prefixes and omits an absent knight-shuffle line', async () => {
    const { loadOpeningPrefixSet } = await loadOpenings(REAL_TSV);
    const prefixSet = await loadOpeningPrefixSet();

    expect(prefixSet.has('e4')).toBe(true);
    expect(prefixSet.has('e4 e5')).toBe(true);
    expect(prefixSet.has('d4 d5')).toBe(true);
    // Verified absent from the corpus: `grep -c "Nf3 Nf6 Ng1" frontend/public/openings.tsv` -> 0
    expect(prefixSet.has('Nf3 Nf6 Ng1 Ng8')).toBe(false);
  });

  it('findOpening still resolves a non-null opening against the real TSV (proves Task 1s refactor did not break name lookup)', async () => {
    const { findOpening } = await loadOpenings(REAL_TSV);

    const opening = await findOpening(['e4', 'c6']);

    expect(opening).not.toBeNull();
    expect(opening?.eco).toEqual(expect.any(String));
    expect(opening?.name).toEqual(expect.any(String));
  });
});
