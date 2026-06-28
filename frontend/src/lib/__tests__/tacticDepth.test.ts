/**
 * tacticDepth.ts unit tests — Quick 260620-l5k (Phase 130).
 *
 * The filter is a two-handle RANGE [min, max] over tactic depth (0-based ply,
 * domain 0..11). The slider domain IS the API/DB domain — no full-move ↔
 * half-ply conversion. Presets: Low 0–1, Medium 0–5, High 0–11.
 */

import { describe, expect, it } from 'vitest';
import {
  DEPTH_MIN,
  DEPTH_MAX,
  DEPTH_STEP,
  DEPTH_DEFAULT_PRESET,
  DEFAULT_TACTIC_DEPTH_VALUE,
  PRESET_RANGES,
  derivePreset,
  presetToRange,
  sliderToRange,
  formatDepthSummary,
  depthToQueryParams,
  toDisplayDepth,
  toDisplayDepthForOrientation,
  ALLOWED_DECISION_DEPTH_OFFSET,
} from '../tacticDepth';

// ── Named-constant sanity checks ────────────────────────────────────────────

describe('named constants', () => {
  it('DEPTH_MIN is 0 (0 selectable on both handles)', () => {
    expect(DEPTH_MIN).toBe(0);
  });

  it('DEPTH_MAX is 11 (dev-DB max tactic depth)', () => {
    expect(DEPTH_MAX).toBe(11);
  });

  it('DEPTH_STEP is 1', () => {
    expect(DEPTH_STEP).toBe(1);
  });

  it('DEPTH_DEFAULT_PRESET is high (full range — Quick 260621-sm8)', () => {
    expect(DEPTH_DEFAULT_PRESET).toBe('high');
  });

  it('preset ranges: Low 0–1, Medium 0–5, High 0–11', () => {
    expect(PRESET_RANGES.low).toEqual({ min: 0, max: 1 });
    expect(PRESET_RANGES.medium).toEqual({ min: 0, max: 5 });
    expect(PRESET_RANGES.high).toEqual({ min: 0, max: 11 });
  });

  it('DEFAULT_TACTIC_DEPTH_VALUE is the High/full range {0, 11} (Quick 260621-sm8)', () => {
    expect(DEFAULT_TACTIC_DEPTH_VALUE).toEqual({ min: 0, max: 11 });
  });

  it('ALLOWED_DECISION_DEPTH_OFFSET is 1 (allowed sits one ply deeper)', () => {
    expect(ALLOWED_DECISION_DEPTH_OFFSET).toBe(1);
  });
});

// ── derivePreset (operates on a {min, max} range) ───────────────────────────

describe('derivePreset', () => {
  it('derivePreset(0, 1) === low', () => {
    expect(derivePreset(0, 1)).toBe('low');
  });

  it('derivePreset(0, 5) === medium', () => {
    expect(derivePreset(0, 5)).toBe('medium');
  });

  it('derivePreset(0, 11) === high', () => {
    expect(derivePreset(0, 11)).toBe('high');
  });

  it('derivePreset(2, 4) === null (custom, no preset matches)', () => {
    expect(derivePreset(2, 4)).toBeNull();
  });

  it('derivePreset(0, 0) === null (custom — depth-0 only)', () => {
    expect(derivePreset(0, 0)).toBeNull();
  });

  it('derivePreset(3, 7) === null (custom)', () => {
    expect(derivePreset(3, 7)).toBeNull();
  });
});

// ── presetToRange ────────────────────────────────────────────────────────────

describe('presetToRange', () => {
  it('round-trips through derivePreset for every preset', () => {
    for (const preset of ['low', 'medium', 'high'] as const) {
      const r = presetToRange(preset);
      expect(derivePreset(r.min, r.max)).toBe(preset);
    }
  });
});

// ── sliderToRange (orders + clamps the handle tuple) ────────────────────────

describe('sliderToRange', () => {
  it('passes an in-domain tuple through unchanged', () => {
    expect(sliderToRange(0, 5)).toEqual({ min: 0, max: 5 });
  });

  it('allows min === max (0, 0)', () => {
    expect(sliderToRange(0, 0)).toEqual({ min: 0, max: 0 });
  });

  it('orders a reversed tuple', () => {
    expect(sliderToRange(7, 2)).toEqual({ min: 2, max: 7 });
  });

  it('clamps into the [0, 11] domain', () => {
    expect(sliderToRange(-3, 99)).toEqual({ min: 0, max: 11 });
  });
});

// ── formatDepthSummary ───────────────────────────────────────────────────────

describe('formatDepthSummary', () => {
  // Summary shows the 1-based display number (internal value + DEPTH_DISPLAY_OFFSET).
  it('preset ranges render "Label: min-max"', () => {
    expect(formatDepthSummary({ min: 0, max: 1 })).toBe('Low: 1-2');
    expect(formatDepthSummary({ min: 0, max: 5 })).toBe('Medium: 1-6');
    expect(formatDepthSummary({ min: 0, max: 11 })).toBe('High: 1-12');
  });

  it('custom ranges render a bare "a-b"', () => {
    expect(formatDepthSummary({ min: 2, max: 4 })).toBe('3-5');
  });

  it('min === max renders a single number', () => {
    expect(formatDepthSummary({ min: 0, max: 0 })).toBe('1');
    expect(formatDepthSummary({ min: 3, max: 3 })).toBe('4');
  });
});

// ── toDisplayDepth ───────────────────────────────────────────────────────────

describe('toDisplayDepth', () => {
  it('offsets internal 0-based depth to the 1-based display number', () => {
    expect(toDisplayDepth(0)).toBe(1);
    expect(toDisplayDepth(11)).toBe(12);
  });
});

// ── toDisplayDepthForOrientation (decision-anchored) ────────────────────────

describe('toDisplayDepthForOrientation', () => {
  it('missed equals the plain 1-based display (raw + 1)', () => {
    expect(toDisplayDepthForOrientation(0, 'missed')).toBe(1);
    expect(toDisplayDepthForOrientation(11, 'missed')).toBe(12);
  });

  it('allowed is one deeper than missed at the same raw depth (raw + 2)', () => {
    expect(toDisplayDepthForOrientation(0, 'allowed')).toBe(2);
    expect(toDisplayDepthForOrientation(11, 'allowed')).toBe(13);
  });

  it('allowed always reads exactly ALLOWED_DECISION_DEPTH_OFFSET above missed', () => {
    for (const raw of [0, 1, 5, 11]) {
      expect(toDisplayDepthForOrientation(raw, 'allowed')).toBe(
        toDisplayDepthForOrientation(raw, 'missed') + ALLOWED_DECISION_DEPTH_OFFSET,
      );
    }
  });

  // anchored=false (Quick 260628-1t5 DECISION 2): on the navigable surfaces the allowed
  // +1 decision-anchor offset is dropped, so allowed reads exactly like missed.
  it('anchored=false drops the allowed offset — allowed equals missed (raw + 1)', () => {
    expect(toDisplayDepthForOrientation(0, 'allowed', false)).toBe(1);
    expect(toDisplayDepthForOrientation(11, 'allowed', false)).toBe(12);
    for (const raw of [0, 1, 5, 11]) {
      expect(toDisplayDepthForOrientation(raw, 'allowed', false)).toBe(
        toDisplayDepthForOrientation(raw, 'missed', false),
      );
    }
  });

  it('anchored=false leaves missed unchanged (missed never carries the offset)', () => {
    expect(toDisplayDepthForOrientation(0, 'missed', false)).toBe(1);
    expect(toDisplayDepthForOrientation(11, 'missed', false)).toBe(12);
  });
});

// ── depthToQueryParams ───────────────────────────────────────────────────────

describe('depthToQueryParams', () => {
  it('always sends both bounds (including 0)', () => {
    expect(depthToQueryParams(0, 5)).toEqual({ min_tactic_depth: 0, max_tactic_depth: 5 });
    expect(depthToQueryParams(0, 0)).toEqual({ min_tactic_depth: 0, max_tactic_depth: 0 });
    expect(depthToQueryParams(2, 11)).toEqual({ min_tactic_depth: 2, max_tactic_depth: 11 });
  });
});
