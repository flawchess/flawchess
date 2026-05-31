/**
 * Phase 98: Unit tests for the computePrimaryTc shared utility.
 *
 * Covers D-09/D-10 behaviour:
 * - argmax picks the time-weighted TC (games × NOMINAL_DURATION).
 * - TCs below the minGames floor are excluded from the argmax.
 * - Returns null when all TCs are below the floor.
 * - Iterates in bullet/blitz/rapid/classical order (ties go to the earlier TC
 *   since the loop uses strict `>` for replacement).
 */

import { describe, expect, it } from 'vitest';
import { NOMINAL_DURATION, computePrimaryTc } from '../primaryTc';

function makeTc(
  totals: Partial<Record<'bullet' | 'blitz' | 'rapid' | 'classical', number>>,
): Record<string, { total: number }[]> {
  const result: Record<string, { total: number }[]> = {};
  for (const [tc, total] of Object.entries(totals)) {
    // Each TC entry is a list of category stats; here a single aggregate entry.
    result[tc] = [{ total: total as number }];
  }
  return result;
}

describe('NOMINAL_DURATION constants', () => {
  it('exports the user-chosen ratios 1:3:10:15', () => {
    expect(NOMINAL_DURATION.bullet).toBe(60);
    expect(NOMINAL_DURATION.blitz).toBe(180);
    expect(NOMINAL_DURATION.rapid).toBe(600);
    expect(NOMINAL_DURATION.classical).toBe(900);
  });
});

describe('computePrimaryTc — argmax of games × NOMINAL_DURATION', () => {
  it('picks rapid over bullet when rapid×600 > bullet×60', () => {
    // 500 rapid × 600 = 300 000 > 2000 bullet × 60 = 120 000
    const data = makeTc({ bullet: 2000, rapid: 500 });
    expect(computePrimaryTc(data, 1)).toBe('rapid');
  });

  it('picks blitz when blitz×180 is the highest score', () => {
    // bullet: 100×60=6000; blitz: 200×180=36000; rapid: 50×600=30000
    const data = makeTc({ bullet: 100, blitz: 200, rapid: 50 });
    expect(computePrimaryTc(data, 1)).toBe('blitz');
  });

  it('picks classical when classical has the highest time-weighted count', () => {
    // classical: 30×900=27000 > rapid: 40×600=24000
    const data = makeTc({ classical: 30, rapid: 40 });
    expect(computePrimaryTc(data, 1)).toBe('classical');
  });

  it('returns the first TC in bullet/blitz/rapid/classical order on an exact tie', () => {
    // bullet: 1×60=60 vs blitz: 0.33×180≈60 → in practice integer totals;
    // here bullet gets it because it's first and >bestScore (-1) initially.
    // bullet: 3×60=180; blitz: 1×180=180 — exact tie, bullet wins (earlier in order).
    const data = makeTc({ bullet: 3, blitz: 1 });
    expect(computePrimaryTc(data, 1)).toBe('bullet');
  });
});

describe('computePrimaryTc — games floor', () => {
  it('excludes TCs with total < minGames from the argmax', () => {
    // bullet: 5 games (below floor of 20), rapid: 25 games (above floor).
    // Even though bullet×60=300 > rapid×600=15000 is wrong, bullet is excluded.
    const data = makeTc({ bullet: 5, rapid: 25 });
    expect(computePrimaryTc(data, 20)).toBe('rapid');
  });

  it('returns null when all TCs are below the floor', () => {
    const data = makeTc({ bullet: 5, blitz: 3, rapid: 1 });
    expect(computePrimaryTc(data, 20)).toBeNull();
  });

  it('returns null for an empty categoriesByTc', () => {
    expect(computePrimaryTc({}, 20)).toBeNull();
  });

  it('returns null when all TCs are missing from the map', () => {
    const data = makeTc({ bullet: 100 });
    // Only bullet has data; minGames = 200 > 100 → excluded.
    expect(computePrimaryTc(data, 200)).toBeNull();
  });
});

describe('computePrimaryTc — multiple categories per TC', () => {
  it('sums all category totals for a TC before comparing', () => {
    // rapid has 3 categories totalling 60 games; blitz has 1 category with 50.
    // rapid: 60×600=36000; blitz: 50×180=9000 → rapid wins.
    const data: Record<string, { total: number }[]> = {
      rapid: [{ total: 20 }, { total: 20 }, { total: 20 }],
      blitz: [{ total: 50 }],
    };
    expect(computePrimaryTc(data, 1)).toBe('rapid');
  });
});
