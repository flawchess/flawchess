/**
 * styleOpeningLines.ts unit tests (Phase 182, STYLE-01/D-05).
 *
 * Two independent things are proven here:
 * 1. Corpus validation: EVERY curated prefix string across all 4 styles x 2
 *    colors is a genuine member of the real `frontend/public/openings.tsv`
 *    prefix set — a curated string absent from the corpus could never be
 *    booked (D-05). Mirrors `openings.test.ts`'s real-TSV fetch-stub +
 *    `vi.resetModules()` pattern so this test reads the SAME asset the
 *    production `openings.ts` module parses, not a hand-written fixture.
 * 2. `styleLinesFor(style, side)` resolves the color-correct set per style
 *    and never returns `undefined` — including defensively, for a style
 *    value that has slipped past TypeScript via an external cast.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  styleLinesFor,
  ATTACKER_WHITE_LINES,
  ATTACKER_BLACK_LINES,
  TRICKSTER_WHITE_LINES,
  TRICKSTER_BLACK_LINES,
  GRINDER_WHITE_LINES,
  GRINDER_BLACK_LINES,
  WALL_WHITE_LINES,
  WALL_BLACK_LINES,
  type Style,
} from '../styleOpeningLines';

const REAL_TSV = readFileSync(new URL('../../../../public/openings.tsv', import.meta.url), 'utf8');

const ALL_CURATED_SETS: { label: string; set: ReadonlySet<string> }[] = [
  { label: 'ATTACKER_WHITE_LINES', set: ATTACKER_WHITE_LINES },
  { label: 'ATTACKER_BLACK_LINES', set: ATTACKER_BLACK_LINES },
  { label: 'TRICKSTER_WHITE_LINES', set: TRICKSTER_WHITE_LINES },
  { label: 'TRICKSTER_BLACK_LINES', set: TRICKSTER_BLACK_LINES },
  { label: 'GRINDER_WHITE_LINES', set: GRINDER_WHITE_LINES },
  { label: 'GRINDER_BLACK_LINES', set: GRINDER_BLACK_LINES },
  { label: 'WALL_WHITE_LINES', set: WALL_WHITE_LINES },
  { label: 'WALL_BLACK_LINES', set: WALL_BLACK_LINES },
];

function stubFetch(text: string): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ text: () => Promise.resolve(text) })),
  );
}

async function loadRealPrefixSet(): Promise<ReadonlySet<string>> {
  vi.resetModules();
  stubFetch(REAL_TSV);
  const { loadOpeningPrefixSet } = await import('../../openings');
  return loadOpeningPrefixSet();
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe('curated prefixes are genuine ECO-corpus members (D-05)', () => {
  it('every curated prefix string, across all 4 styles x 2 colors, is a member of the real openings.tsv prefix set', async () => {
    const prefixSet = await loadRealPrefixSet();

    const missing: { label: string; line: string }[] = [];
    for (const { label, set } of ALL_CURATED_SETS) {
      for (const line of set) {
        if (!prefixSet.has(line)) missing.push({ label, line });
      }
    }

    // Array assertion (not a boolean) so a regression NAMES the offending
    // style/line instead of just printing `false`.
    expect(missing).toEqual([]);
  });

  it('sanity: the membership check itself is discriminating — a bogus prefix is correctly reported absent', async () => {
    const prefixSet = await loadRealPrefixSet();

    // Proves the test technique above would catch a genuinely unbookable
    // curated string (e.g. a typo'd SAN token) rather than passing
    // vacuously — this string is never inserted into any real curated set.
    expect(prefixSet.has('e4 e5 Zz9')).toBe(false);
  });

  it('every curated set is non-empty (no accidental empty style/color pairing)', () => {
    for (const { label, set } of ALL_CURATED_SETS) {
      expect(set.size, `${label} should be non-empty`).toBeGreaterThan(0);
    }
  });
});

describe('styleLinesFor', () => {
  const cases: { style: Style; side: 'w' | 'b'; expected: ReadonlySet<string> }[] = [
    { style: 'Attacker', side: 'w', expected: ATTACKER_WHITE_LINES },
    { style: 'Attacker', side: 'b', expected: ATTACKER_BLACK_LINES },
    { style: 'Trickster', side: 'w', expected: TRICKSTER_WHITE_LINES },
    { style: 'Trickster', side: 'b', expected: TRICKSTER_BLACK_LINES },
    { style: 'Grinder', side: 'w', expected: GRINDER_WHITE_LINES },
    { style: 'Grinder', side: 'b', expected: GRINDER_BLACK_LINES },
    { style: 'Wall', side: 'w', expected: WALL_WHITE_LINES },
    { style: 'Wall', side: 'b', expected: WALL_BLACK_LINES },
  ];

  it.each(cases)('resolves the color-correct set for $style / $side', ({ style, side, expected }) => {
    expect(styleLinesFor(style, side)).toBe(expected);
  });

  it('returns an empty ReadonlySet, not undefined, for an unrecognized style value (defensive runtime fallback)', () => {
    const bogusStyle = 'NotAStyle' as Style;

    const result = styleLinesFor(bogusStyle, 'w');

    expect(result).toBeDefined();
    expect(result).toBeInstanceOf(Set);
    expect(result.size).toBe(0);
  });
});
