/**
 * Vitest unit tests for the shared signed-band gradient-stops algorithm.
 *
 * Covers the 6 algorithmic cases defined in Phase 87.6 Plan 02 + an
 * empty-rows edge case.
 *
 * The two critical invariants being tested:
 *   1. "First non-zero sign" initialisation (Phase 68 UAT bug 260424):
 *      sign=0 leading rows must not lock the initial color to positive.
 *   2. "colorA !== colorB" zero-endpoint handling: a sign=0 row followed by
 *      a non-zero sign of the opposite orientation must trigger a coincident
 *      flip pair at the segment boundary.
 */

import { describe, it, expect } from 'vitest';
import { signedBandGradient } from '../signedBandGradient';
import type { SignedBandRow } from '../signedBandGradient';

// Use string sentinels so tests are decoupled from actual theme constants.
const COLORS = { positive: 'green-test', negative: 'red-test' };
const DOMAIN: [number, number] = [0, 10]; // _xDomain is unused by the algorithm

// Helper to build rows quickly
function rows(signs: Array<1 | -1 | 0>): SignedBandRow[] {
  return signs.map((sign, i) => ({ x: i, sign }));
}

describe('signedBandGradient', () => {
  it('returns empty array for zero rows', () => {
    const result = signedBandGradient([], DOMAIN, COLORS);
    expect(result).toEqual([]);
  });

  it('monotone-positive: 3 rows all sign=1 → 2 stops both positive', () => {
    const result = signedBandGradient(rows([1, 1, 1]), DOMAIN, COLORS);
    // Monotone: only offset-0 and offset-100 stops, both positive
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ offset: 0, color: 'green-test' });
    expect(result[1]).toEqual({ offset: 100, color: 'green-test' });
  });

  it('monotone-negative: 3 rows all sign=-1 → 2 stops both negative', () => {
    const result = signedBandGradient(rows([-1, -1, -1]), DOMAIN, COLORS);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ offset: 0, color: 'red-test' });
    expect(result[1]).toEqual({ offset: 100, color: 'red-test' });
  });

  it('single-crossover: [sign=1, sign=-1] → 4 stops with coincident flip pair', () => {
    // N=2, denom=1. Segment 0→1: dA=1, dB=-1, t=1/(1-(-1))=0.5
    // offsetPct = (0 + 0.5) / 1 * 100 = 50
    // Stops: [0/positive, 50/positive, 50/negative, 100/negative]
    const result = signedBandGradient(rows([1, -1]), DOMAIN, COLORS);
    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({ offset: 0, color: 'green-test' });
    expect(result[1]).toEqual({ offset: 50, color: 'green-test' });
    expect(result[2]).toEqual({ offset: 50, color: 'red-test' });
    expect(result[3]).toEqual({ offset: 100, color: 'red-test' });
  });

  it('multiple-crossovers: [1, -1, 1] → 6 stops with two coincident flip pairs', () => {
    // N=3, denom=2.
    // Segment 0→1: dA=1, dB=-1, t=0.5; offsetPct=(0+0.5)/2*100=25
    // Segment 1→2: dA=-1, dB=1, t=(-1)/(-1-1)=(-1)/(-2)=0.5; offsetPct=(1+0.5)/2*100=75
    // Stops: [0/+, 25/+, 25/-, 75/-, 75/+, 100/+]
    const result = signedBandGradient(rows([1, -1, 1]), DOMAIN, COLORS);
    expect(result).toHaveLength(6);
    expect(result[0]).toEqual({ offset: 0, color: 'green-test' });
    expect(result[1]).toEqual({ offset: 25, color: 'green-test' });
    expect(result[2]).toEqual({ offset: 25, color: 'red-test' });
    expect(result[3]).toEqual({ offset: 75, color: 'red-test' });
    expect(result[4]).toEqual({ offset: 75, color: 'green-test' });
    expect(result[5]).toEqual({ offset: 100, color: 'green-test' });
  });

  it('sign-zero-leading: [0, 0, 1, 1] → initial color is positive (Phase 68 UAT fix)', () => {
    // First non-zero sign is +1 → currentColor = positive.
    // No crossovers within the all-positive-or-zero series.
    // Stops: [0/positive, 100/positive]
    const result = signedBandGradient(rows([0, 0, 1, 1]), DOMAIN, COLORS);
    // No crossovers: just start + end stops, both positive
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ offset: 0, color: 'green-test' });
    expect(result[1]).toEqual({ offset: 100, color: 'green-test' });
  });

  it('sign-zero-leading with all negatives: [0, 0, -1, -1] → initial color is negative', () => {
    // First non-zero sign is -1 → currentColor = negative.
    // The sign=0 segments map to colorFor(0)='green-test' in the loop, which differs
    // from currentColor='red-test'. This causes a redundant coincident pair at the
    // sign=0→sign=-1 boundary, but all stops are red — no green ever appears.
    const result = signedBandGradient(rows([0, 0, -1, -1]), DOMAIN, COLORS);
    // All stops should be red (negative) — green never appears
    const colors = new Set(result.map((s) => s.color));
    expect(colors).toEqual(new Set(['red-test']));
    // First stop at offset 0, last at offset 100, both red
    expect(result[0]).toEqual({ offset: 0, color: 'red-test' });
    expect(result[result.length - 1]).toEqual({ offset: 100, color: 'red-test' });
  });

  it('sign-zero-endpoint: [1, 0, -1] → colorA !== colorB fires at segment 1→2', () => {
    // N=3, denom=2.
    // Segment 0→1: dA=1, dB=0 → colorA=positive, colorB=positive (0 >= 0 → positive). Same color, no flip.
    // Segment 1→2: dA=0, dB=-1 → colorA=positive, colorB=negative. Different colors!
    //   t = 0 / (0 - (-1)) = 0; offsetPct = (1 + 0) / 2 * 100 = 50
    //   Two coincident stops at offset 50: [50/positive, 50/negative]
    // Stops: [0/positive, 50/positive, 50/negative, 100/negative]
    const result = signedBandGradient(rows([1, 0, -1]), DOMAIN, COLORS);
    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({ offset: 0, color: 'green-test' });
    expect(result[1]).toEqual({ offset: 50, color: 'green-test' });
    expect(result[2]).toEqual({ offset: 50, color: 'red-test' });
    expect(result[3]).toEqual({ offset: 100, color: 'red-test' });
  });
});
