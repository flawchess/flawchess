/**
 * useFlawFilterStore unit tests.
 *
 * Asserts that:
 * 1. DEFAULT_FLAW_FILTER includes tacticOrientation='either' + depth range {0, 11}
 * 2. isFlawFilterNonDefault returns false at the defaults
 * 3. Each off-default value flips isFlawFilterNonDefault to true
 *
 * Depth is now a [min, max] range in depth units;
 * default changed from Intermediate {0, 5} to High/full range {0, 11}.
 */

import { describe, expect, it } from 'vitest';
import {
  DEFAULT_FLAW_FILTER,
  isFlawFilterNonDefault,
} from '../useFlawFilterStore';
import type { FlawFilterState } from '../useFlawFilterStore';
import {
  FLAW_SEVERITY_FILTER_VALUES,
  isSeverityNarrowed,
  parseSeverityFilterParams,
} from '@/lib/flawSeverityFilter';

describe('flawSeverityFilter helpers', () => {
  it('lists the three tags in D-08 order', () => {
    expect([...FLAW_SEVERITY_FILTER_VALUES]).toEqual(['facepalm', 'blunder', 'mistake']);
  });

  it.each([
    [[], false],
    [['facepalm'], true],
    [['blunder'], true],
    [['mistake'], true],
    [['blunder', 'mistake'], true],
    [['facepalm', 'blunder'], true],
    [['mistake', 'facepalm', 'blunder'], false],
  ] as const)('isSeverityNarrowed(%j) is %s', (selection, expected) => {
    expect(isSeverityNarrowed([...selection])).toBe(expected);
  });

  it('parseSeverityFilterParams keeps known values, de-duplicated, in input order', () => {
    expect(
      parseSeverityFilterParams(['facepalm', 'inaccuracy', 'fatal', 'blunder', 'facepalm']),
    ).toEqual(['facepalm', 'blunder']);
    expect(parseSeverityFilterParams([])).toEqual([]);
    expect(parseSeverityFilterParams(['bogus', 'Blunder', ''])).toEqual([]);
  });
});

describe('removed facepalm range fields', () => {
  it('has no facepalm keys in the default filter', () => {
    expect(Object.keys(DEFAULT_FLAW_FILTER).filter((k) => k.startsWith('facepalm'))).toEqual([]);
  });

  it('is default for an object without the facepalm fields (partial mocks)', () => {
    const partial = { severity: [], tags: [] } as unknown as FlawFilterState;
    expect(isFlawFilterNonDefault(partial)).toBe(false);
  });

  it('loads a stale object still carrying range fields as the default filter (D-14)', () => {
    const stale = { ...DEFAULT_FLAW_FILTER, facepalmMin: 70, facepalmMax: 100 } as unknown as FlawFilterState;
    expect(isFlawFilterNonDefault(stale)).toBe(false);
  });
});

describe('DEFAULT_FLAW_FILTER', () => {
  it('includes tacticOrientation = either', () => {
    expect(DEFAULT_FLAW_FILTER.tacticOrientation).toBe('either');
  });

  it('includes the High/full depth range {0, 11}', () => {
    expect(DEFAULT_FLAW_FILTER.tacticDepthMin).toBe(0);
    expect(DEFAULT_FLAW_FILTER.tacticDepthMax).toBe(11);
  });

  it('includes empty severity', () => {
    expect(DEFAULT_FLAW_FILTER.severity).toEqual([]);
  });

  it('includes empty tags', () => {
    expect(DEFAULT_FLAW_FILTER.tags).toEqual([]);
  });

  it('includes empty tacticFamilies', () => {
    expect(DEFAULT_FLAW_FILTER.tacticFamilies).toEqual([]);
  });

  it('includes hasGem = false and hasGreat = false', () => {
    expect(DEFAULT_FLAW_FILTER.hasGem).toBe(false);
    expect(DEFAULT_FLAW_FILTER.hasGreat).toBe(false);
  });
});

describe('isFlawFilterNonDefault', () => {
  it('returns false for the full default filter', () => {
    expect(isFlawFilterNonDefault(DEFAULT_FLAW_FILTER)).toBe(false);
  });

  it('returns false when tacticOrientation=either and depth range is {0, 11}', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticOrientation: 'either',
        tacticDepthMin: 0,
        tacticDepthMax: 11,
      }),
    ).toBe(false);
  });

  it('returns true when tacticOrientation = missed', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, tacticOrientation: 'missed' }),
    ).toBe(true);
  });

  it('returns true when tacticOrientation = allowed', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, tacticOrientation: 'allowed' }),
    ).toBe(true);
  });

  it('returns true for the Low range {0, 1}', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthMin: 0,
        tacticDepthMax: 1,
      }),
    ).toBe(true);
  });

  it('returns true for the Medium range {0, 5}', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthMin: 0,
        tacticDepthMax: 5,
      }),
    ).toBe(true);
  });

  it('returns true for a custom range with a non-zero min ({2, 11})', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthMin: 2,
        tacticDepthMax: 11,
      }),
    ).toBe(true);
  });

  it('returns true when severity is narrowed to one tag', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: ['blunder'] }),
    ).toBe(true);
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: ['facepalm'] }),
    ).toBe(true);
  });

  it('returns true for two tags, including blunder + mistake (which excludes facepalms)', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: ['blunder', 'mistake'] }),
    ).toBe(true);
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: ['facepalm', 'mistake'] }),
    ).toBe(true);
  });

  it.each([
    [['facepalm', 'blunder', 'mistake']],
    [['mistake', 'facepalm', 'blunder']],
    [[]],
  ] as const)('returns false when severity is %j (shows everything)', (severity) => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: [...severity] }),
    ).toBe(false);
  });

  it('returns true when tags is non-empty', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, tags: ['miss'] }),
    ).toBe(true);
  });

  it('returns true when tacticFamilies is non-empty', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, tacticFamilies: ['fork'] }),
    ).toBe(true);
  });

  it('returns true when hasGem is true', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, hasGem: true }),
    ).toBe(true);
  });

  it('returns true when hasGreat is true', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, hasGreat: true }),
    ).toBe(true);
  });

  it('returns false when both hasGem and hasGreat are false (default)', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, hasGem: false, hasGreat: false }),
    ).toBe(false);
  });

  it('returns true when only the max differs from the default {0, 11} (custom {0, 10})', () => {
    // Non-default is now driven by the actual range, not a
    // preset label — a custom range narrows the result set and lights the dot.
    // Default is now High {0, 11}, so Medium {0, 5} is non-default.
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthMin: 0,
        tacticDepthMax: 10,
      }),
    ).toBe(true);
  });
});
