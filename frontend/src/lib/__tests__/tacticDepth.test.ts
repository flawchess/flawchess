/**
 * tacticDepth.ts unit tests — Phase 129 TACUI-06 (D-03, locked contract).
 *
 * The slider operates and displays in FULL MOVES (domain 1..5).
 * The API value (maxMoves) is in HALF-PLIES (1:1 with the DB column).
 * sliderToMax / maxToSlider bridge the two via HALF_PLIES_PER_MOVE.
 */

import { describe, expect, it } from 'vitest';
import {
  DEPTH_PRESET_BEGINNER_MAX,
  DEPTH_PRESET_INTERMEDIATE_MAX,
  DEPTH_PRESET_ADVANCED_MAX,
  DEPTH_SLIDER_MIN_MOVES,
  DEPTH_SLIDER_MAX_MOVES,
  HALF_PLIES_PER_MOVE,
  DEPTH_DEFAULT_PRESET,
  derivePreset,
  presetToMax,
  sliderToMax,
  maxToSlider,
  formatDepthSummary,
  depthToQueryParam,
} from '../tacticDepth';

// ── Named-constant sanity checks ────────────────────────────────────────────

describe('named constants', () => {
  it('DEPTH_PRESET_BEGINNER_MAX is 2 (half-plies = 1 full move)', () => {
    expect(DEPTH_PRESET_BEGINNER_MAX).toBe(2);
  });

  it('DEPTH_PRESET_INTERMEDIATE_MAX is 6 (half-plies = 3 full moves)', () => {
    expect(DEPTH_PRESET_INTERMEDIATE_MAX).toBe(6);
  });

  it('DEPTH_PRESET_ADVANCED_MAX is null (no cap)', () => {
    expect(DEPTH_PRESET_ADVANCED_MAX).toBeNull();
  });

  it('DEPTH_SLIDER_MIN_MOVES is 1', () => {
    expect(DEPTH_SLIDER_MIN_MOVES).toBe(1);
  });

  it('DEPTH_SLIDER_MAX_MOVES is 5', () => {
    expect(DEPTH_SLIDER_MAX_MOVES).toBe(5);
  });

  it('HALF_PLIES_PER_MOVE is 2', () => {
    expect(HALF_PLIES_PER_MOVE).toBe(2);
  });

  it('DEPTH_DEFAULT_PRESET is intermediate', () => {
    expect(DEPTH_DEFAULT_PRESET).toBe('intermediate');
  });
});

// ── derivePreset (operates on half-ply maxMoves) ────────────────────────────

describe('derivePreset', () => {
  it('derivePreset(2) === beginner', () => {
    expect(derivePreset(2)).toBe('beginner');
  });

  it('derivePreset(6) === intermediate', () => {
    expect(derivePreset(6)).toBe('intermediate');
  });

  it('derivePreset(null) === advanced', () => {
    expect(derivePreset(null)).toBe('advanced');
  });

  it('derivePreset(4) === null (custom, no preset matches)', () => {
    expect(derivePreset(4)).toBeNull();
  });

  it('derivePreset(8) === null (custom)', () => {
    expect(derivePreset(8)).toBeNull();
  });

  it('derivePreset(0) === null (custom)', () => {
    expect(derivePreset(0)).toBeNull();
  });
});

// ── presetToMax ──────────────────────────────────────────────────────────────

describe('presetToMax', () => {
  it('presetToMax(beginner) === 2', () => {
    expect(presetToMax('beginner')).toBe(DEPTH_PRESET_BEGINNER_MAX);
  });

  it('presetToMax(intermediate) === 6', () => {
    expect(presetToMax('intermediate')).toBe(DEPTH_PRESET_INTERMEDIATE_MAX);
  });

  it('presetToMax(advanced) === null', () => {
    expect(presetToMax('advanced')).toBeNull();
  });
});

// ── sliderToMax (full-move slider → half-ply maxMoves) ─────────────────────

describe('sliderToMax', () => {
  it('sliderToMax(1) === 2 (1 full move = 2 half-plies)', () => {
    expect(sliderToMax(1)).toBe(2);
  });

  it('sliderToMax(3) === 6 (3 full moves = 6 half-plies)', () => {
    expect(sliderToMax(3)).toBe(6);
  });

  it('sliderToMax(DEPTH_SLIDER_MAX_MOVES) === null (Advanced / no cap)', () => {
    expect(sliderToMax(DEPTH_SLIDER_MAX_MOVES)).toBeNull();
  });

  it('sliderToMax(2) === 4 (2 full moves = 4 half-plies)', () => {
    expect(sliderToMax(2)).toBe(4);
  });

  it('sliderToMax(4) === 8', () => {
    expect(sliderToMax(4)).toBe(8);
  });
});

// ── maxToSlider (half-ply maxMoves → full-move slider position) ─────────────

describe('maxToSlider', () => {
  it('maxToSlider(2) === 1', () => {
    expect(maxToSlider(2)).toBe(1);
  });

  it('maxToSlider(6) === 3', () => {
    expect(maxToSlider(6)).toBe(3);
  });

  it('maxToSlider(null) === DEPTH_SLIDER_MAX_MOVES', () => {
    expect(maxToSlider(null)).toBe(DEPTH_SLIDER_MAX_MOVES);
  });

  it('maxToSlider(4) === 2', () => {
    expect(maxToSlider(4)).toBe(2);
  });
});

// ── Round-trip: maxToSlider(sliderToMax(n)) for n in 1..5 ───────────────────

describe('round-trip sliderToMax / maxToSlider', () => {
  for (let n = 1; n <= DEPTH_SLIDER_MAX_MOVES; n++) {
    it(`round-trip for slider position ${n}`, () => {
      expect(maxToSlider(sliderToMax(n))).toBe(n);
    });
  }
});

// ── depthToQueryParam ────────────────────────────────────────────────────────

describe('depthToQueryParam', () => {
  it('depthToQueryParam(null) returns empty object (no max_tactic_depth key)', () => {
    const result = depthToQueryParam(null);
    expect(result).toEqual({});
    expect('max_tactic_depth' in result).toBe(false);
  });

  it('depthToQueryParam(6) returns { max_tactic_depth: 6 } (half-ply passthrough)', () => {
    expect(depthToQueryParam(6)).toEqual({ max_tactic_depth: 6 });
  });

  it('depthToQueryParam(2) returns { max_tactic_depth: 2 }', () => {
    expect(depthToQueryParam(2)).toEqual({ max_tactic_depth: 2 });
  });

  it('depthToQueryParam(4) returns { max_tactic_depth: 4 }', () => {
    expect(depthToQueryParam(4)).toEqual({ max_tactic_depth: 4 });
  });
});

// ── formatDepthSummary (reads in full moves) ─────────────────────────────────

describe('formatDepthSummary', () => {
  it('Beginner preset: "Beginner (1 move)"', () => {
    expect(formatDepthSummary({ preset: 'beginner', maxMoves: DEPTH_PRESET_BEGINNER_MAX })).toBe(
      'Beginner (1 move)',
    );
  });

  it('Intermediate preset: "Intermediate (≤ 3 moves deep)"', () => {
    expect(
      formatDepthSummary({ preset: 'intermediate', maxMoves: DEPTH_PRESET_INTERMEDIATE_MAX }),
    ).toBe('Intermediate (≤ 3 moves deep)');
  });

  it('Advanced preset: "Advanced (all)"', () => {
    expect(formatDepthSummary({ preset: 'advanced', maxMoves: null })).toBe('Advanced (all)');
  });

  it('Custom (2 full moves): "Custom (≤ 2 moves)"', () => {
    // maxMoves=4 half-plies = 2 full moves
    expect(formatDepthSummary({ preset: 'intermediate', maxMoves: 4 })).toBe('Custom (≤ 2 moves)');
  });

  it('Custom (1 full move via maxMoves=2): "Beginner (1 move)" because preset matches', () => {
    // when derivePreset(maxMoves) matches a preset, show preset summary
    expect(formatDepthSummary({ preset: 'beginner', maxMoves: 2 })).toBe('Beginner (1 move)');
  });

  it('Custom (4 full moves, maxMoves=8): "Custom (≤ 4 moves)"', () => {
    expect(formatDepthSummary({ preset: 'advanced', maxMoves: 8 })).toBe('Custom (≤ 4 moves)');
  });

  it('Summary uses no em-dashes', () => {
    const s = formatDepthSummary({ preset: 'intermediate', maxMoves: DEPTH_PRESET_INTERMEDIATE_MAX });
    expect(s).not.toContain('—');
  });
});
