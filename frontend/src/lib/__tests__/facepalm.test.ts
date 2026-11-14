/**
 * facepalm.ts unit tests.
 *
 * Handles are whole percents 0..100 in steps of 5; the upper handle covers its
 * whole bucket, so the API upper bound is handle + 4 except at 100.
 */

import { describe, expect, it } from 'vitest';
import {
  DEFAULT_FACEPALM_VALUE,
  FACEPALM_DEFAULT_PRESET,
  FACEPALM_PCT_MAX,
  FACEPALM_PCT_MIN,
  FACEPALM_STEP,
  PRESET_LABELS,
  PRESET_ORDER,
  derivePreset,
  displayUpper,
  facepalmToQueryParams,
  formatFacepalmSummary,
  isFacepalmNarrowed,
  presetToRange,
  sliderToRange,
  toFacepalmPct,
} from '../facepalm';

describe('named constants', () => {
  it('slider domain is 0..100 in steps of 5, default preset All', () => {
    expect(FACEPALM_PCT_MIN).toBe(0);
    expect(FACEPALM_PCT_MAX).toBe(100);
    expect(FACEPALM_STEP).toBe(5);
    expect(FACEPALM_DEFAULT_PRESET).toBe('all');
    expect(DEFAULT_FACEPALM_VALUE).toEqual({ min: 0, max: 100 });
  });

  it('chips read All, Low, Mid, High in that order', () => {
    expect(PRESET_ORDER.map((p) => PRESET_LABELS[p])).toEqual(['All', 'Low', 'Mid', 'High']);
  });
});

describe('presetToRange', () => {
  it('maps the four presets to handle positions', () => {
    expect(presetToRange('all')).toEqual({ min: 0, max: 100 });
    expect(presetToRange('low')).toEqual({ min: 0, max: 25 });
    expect(presetToRange('mid')).toEqual({ min: 30, max: 65 });
    expect(presetToRange('high')).toEqual({ min: 70, max: 100 });
  });
});

describe('facepalmToQueryParams', () => {
  it('is empty at All (D-04)', () => {
    expect(facepalmToQueryParams(presetToRange('all'))).toEqual({});
    expect(facepalmToQueryParams(sliderToRange(0, 100))).toEqual({});
  });

  it('sends inclusive floored percents for the presets', () => {
    expect(facepalmToQueryParams(presetToRange('low'))).toEqual({
      min_facepalm_pct: 0,
      max_facepalm_pct: 29,
    });
    expect(facepalmToQueryParams(presetToRange('mid'))).toEqual({
      min_facepalm_pct: 30,
      max_facepalm_pct: 69,
    });
    expect(facepalmToQueryParams(presetToRange('high'))).toEqual({
      min_facepalm_pct: 70,
      max_facepalm_pct: 100,
    });
  });

  it('covers the whole 5% bucket of the upper handle for custom ranges', () => {
    expect(facepalmToQueryParams({ min: 40, max: 40 })).toEqual({
      min_facepalm_pct: 40,
      max_facepalm_pct: 44,
    });
    expect(facepalmToQueryParams({ min: 95, max: 100 })).toEqual({
      min_facepalm_pct: 95,
      max_facepalm_pct: 100,
    });
  });
});

describe('displayUpper', () => {
  it('adds STEP - 1 below 100 and stays 100 at the top', () => {
    expect(displayUpper(25)).toBe(29);
    expect(displayUpper(65)).toBe(69);
    expect(displayUpper(95)).toBe(99);
    expect(displayUpper(100)).toBe(100);
  });
});

describe('derivePreset', () => {
  it('finds each preset and returns null for a custom range', () => {
    expect(derivePreset(0, 100)).toBe('all');
    expect(derivePreset(0, 25)).toBe('low');
    expect(derivePreset(30, 65)).toBe('mid');
    expect(derivePreset(70, 100)).toBe('high');
    expect(derivePreset(40, 45)).toBeNull();
  });
});

describe('sliderToRange', () => {
  it('clamps into the domain and orders the handles', () => {
    expect(sliderToRange(-5, 105)).toEqual({ min: 0, max: 100 });
    expect(sliderToRange(60, 20)).toEqual({ min: 20, max: 60 });
  });
});

describe('isFacepalmNarrowed', () => {
  it('is false only at 0/100', () => {
    expect(isFacepalmNarrowed({ min: 0, max: 100 })).toBe(false);
    expect(isFacepalmNarrowed({ min: 5, max: 100 })).toBe(true);
    expect(isFacepalmNarrowed({ min: 0, max: 95 })).toBe(true);
  });
});

describe('formatFacepalmSummary', () => {
  it('reads All, 0-29%, 30-69%, 70-100% for the presets', () => {
    expect(formatFacepalmSummary(presetToRange('all'))).toBe('All');
    expect(formatFacepalmSummary(presetToRange('low'))).toBe('0-29%');
    expect(formatFacepalmSummary(presetToRange('mid'))).toBe('30-69%');
    expect(formatFacepalmSummary(presetToRange('high'))).toBe('70-100%');
  });

  it('reads custom ranges in the same units', () => {
    expect(formatFacepalmSummary({ min: 40, max: 40 })).toBe('40-44%');
    expect(formatFacepalmSummary({ min: 100, max: 100 })).toBe('100%');
  });
});

describe('toFacepalmPct', () => {
  it('floors the score to a whole percent', () => {
    expect(toFacepalmPct(0.946)).toBe(94);
    expect(toFacepalmPct(0.697)).toBe(69);
    expect(toFacepalmPct(0.27)).toBe(27);
  });

  it('floors the float4 0.70 as the API serves it to 69', () => {
    expect(toFacepalmPct(0.699999988079071)).toBe(69);
  });

  it('keeps the domain edges', () => {
    expect(toFacepalmPct(1)).toBe(100);
    expect(toFacepalmPct(0)).toBe(0);
  });

  it('clamps out-of-range scores into 0..100', () => {
    expect(toFacepalmPct(1.2)).toBe(100);
    expect(toFacepalmPct(-0.1)).toBe(0);
  });
});
