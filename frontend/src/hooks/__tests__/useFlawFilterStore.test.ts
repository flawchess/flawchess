/**
 * useFlawFilterStore unit tests — Phase 129 TACUI-06.
 *
 * Asserts that:
 * 1. DEFAULT_FLAW_FILTER includes tacticOrientation='either', tacticDepthPreset='intermediate'
 * 2. isFlawFilterNonDefault returns false at the defaults
 * 3. Each off-default value flips isFlawFilterNonDefault to true
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

  it('includes tacticDepthPreset = intermediate', () => {
    expect(DEFAULT_FLAW_FILTER.tacticDepthPreset).toBe('intermediate');
  });

  it('includes tacticDepthMax = DEPTH_PRESET_INTERMEDIATE_MAX (6)', () => {
    expect(DEFAULT_FLAW_FILTER.tacticDepthMax).toBe(6);
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

  it('returns false when tacticOrientation=either and tacticDepthPreset=intermediate', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticOrientation: 'either',
        tacticDepthPreset: 'intermediate',
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

  it('returns true when tacticDepthPreset = beginner', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthPreset: 'beginner',
        tacticDepthMax: 2,
      }),
    ).toBe(true);
  });

  it('returns true when tacticDepthPreset = advanced', () => {
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthPreset: 'advanced',
        tacticDepthMax: null,
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

  it('returns false even when tacticDepthMax differs from INTERMEDIATE_MAX but preset is intermediate', () => {
    // CRITICAL (D-02): non-default = NOT Intermediate / NOT Either preset.
    // The depth filter is always-on, so Intermediate with any maxMoves is still "default".
    expect(
      isFlawFilterNonDefault({
        ...DEFAULT_FLAW_FILTER,
        tacticDepthPreset: 'intermediate',
        tacticDepthMax: 4,
      }),
    ).toBe(false);
  });
});
