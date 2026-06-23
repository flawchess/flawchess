/**
 * useFlawFilterStore unit tests — Phase 129 TACUI-06.
 *
 * Asserts that:
 * 1. DEFAULT_FLAW_FILTER includes tacticOrientation='either' + depth range {0, 11}
 * 2. isFlawFilterNonDefault returns false at the defaults
 * 3. Each off-default value flips isFlawFilterNonDefault to true
 *
 * Quick 260620-l5k (Phase 130): depth is now a [min, max] range in depth units;
 * Quick 260621-sm8: default changed from Intermediate {0, 5} to High/full range {0, 11}.
 */

import { describe, expect, it } from 'vitest';
import {
  DEFAULT_FLAW_FILTER,
  isFlawFilterNonDefault,
} from '../useFlawFilterStore';

describe('DEFAULT_FLAW_FILTER', () => {
  it('includes tacticOrientation = either', () => {
    expect(DEFAULT_FLAW_FILTER.tacticOrientation).toBe('either');
  });

  it('includes the High/full depth range {0, 11} (Quick 260621-sm8)', () => {
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

  it('returns true when severity is narrowed to one tier', () => {
    expect(
      isFlawFilterNonDefault({ ...DEFAULT_FLAW_FILTER, severity: ['blunder'] }),
    ).toBe(true);
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

  it('returns true when only the max differs from the default {0, 11} (custom {0, 10})', () => {
    // Quick 260620-l5k: non-default is now driven by the actual range, not a
    // preset label — a custom range narrows the result set and lights the dot.
    // Quick 260621-sm8: default is now High {0, 11}, so Medium {0, 5} is non-default.
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthMin: 0,
        tacticDepthMax: 10,
      }),
    ).toBe(true);
  });
});
