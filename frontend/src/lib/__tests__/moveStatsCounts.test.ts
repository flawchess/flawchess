import { describe, expect, it } from 'vitest';
import { FACEPALM_HIGH_CUTOFF } from '@/lib/facepalm';
import { flawMoveCategory, MOVE_STAT_CATEGORY_ORDER, severityCountsBySide, tierCountsBySide } from '@/lib/moveStatsCounts';
import type { EvalPoint, FlawMarker } from '@/types/library';

function marker(overrides: Partial<FlawMarker> & Pick<FlawMarker, 'ply' | 'severity'>): FlawMarker {
  return {
    tags: [],
    is_user: false,
    move_san: null,
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function point(overrides: Partial<EvalPoint> & Pick<EvalPoint, 'ply'>): EvalPoint {
  return {
    es: null,
    eval_cp: null,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    best_move_tier: null,
    maia_prob: null,
    ...overrides,
  };
}

// Local test scale (percent to 0..1 score); the cut itself is read from FACEPALM_HIGH_CUTOFF.
const PCT_SCALE = 100;
const ABOVE_CUT = (FACEPALM_HIGH_CUTOFF + 1) / PCT_SCALE;
const BELOW_CUT = (FACEPALM_HIGH_CUTOFF - 1) / PCT_SCALE;

describe('flawMoveCategory', () => {
  it('splits a blunder at or above the facepalm cut into facepalm', () => {
    expect(flawMoveCategory({ severity: 'blunder', facepalm_score: ABOVE_CUT })).toBe('facepalm');
  });

  it('keeps a blunder below the cut as blunder', () => {
    expect(flawMoveCategory({ severity: 'blunder', facepalm_score: BELOW_CUT })).toBe('blunder');
  });

  it('keeps an unscored blunder as blunder (null and absent score)', () => {
    expect(flawMoveCategory({ severity: 'blunder', facepalm_score: null })).toBe('blunder');
    expect(flawMoveCategory({ severity: 'blunder' })).toBe('blunder');
  });

  it('never splits a mistake or inaccuracy, even with an above-cut score', () => {
    expect(flawMoveCategory({ severity: 'mistake', facepalm_score: ABOVE_CUT })).toBe('mistake');
    expect(flawMoveCategory({ severity: 'inaccuracy', facepalm_score: ABOVE_CUT })).toBe('inaccuracy');
  });
});

describe('MOVE_STAT_CATEGORY_ORDER', () => {
  it('lists 8 categories with Facepalm last after Blunder', () => {
    expect(MOVE_STAT_CATEGORY_ORDER).toHaveLength(8);
    expect(MOVE_STAT_CATEGORY_ORDER.slice(-2)).toEqual(['blunder', 'facepalm']);
  });
});

describe('severityCountsBySide facepalm split', () => {
  it('counts Blunder and Facepalm disjointly; together they equal the blunder markers of the side', () => {
    const markers = [
      marker({ ply: 0, severity: 'blunder', facepalm_score: ABOVE_CUT }),
      marker({ ply: 2, severity: 'blunder', facepalm_score: BELOW_CUT }),
      marker({ ply: 4, severity: 'blunder', facepalm_score: null }),
      marker({ ply: 1, severity: 'blunder', facepalm_score: ABOVE_CUT }),
    ];
    const result = severityCountsBySide(markers);
    expect(result.white.facepalm).toBe(1);
    expect(result.white.blunder).toBe(2);
    expect(result.white.facepalm + result.white.blunder).toBe(3);
    expect(result.black.facepalm).toBe(1);
    expect(result.black.blunder).toBe(0);
  });
});

describe('severityCountsBySide', () => {
  it('returns both sides all-zero for an empty marker list', () => {
    const result = severityCountsBySide([]);
    expect(result.white).toEqual({ inaccuracy: 0, mistake: 0, blunder: 0, facepalm: 0 });
    expect(result.black).toEqual({ inaccuracy: 0, mistake: 0, blunder: 0, facepalm: 0 });
  });

  it('counts a blunder at ply 0 (white) and a mistake at ply 1 (black), regardless of is_user', () => {
    const markers = [
      marker({ ply: 0, severity: 'blunder', is_user: false }),
      marker({ ply: 1, severity: 'mistake', is_user: true }),
    ];
    const result = severityCountsBySide(markers);
    expect(result.white.blunder).toBe(1);
    expect(result.black.mistake).toBe(1);
    expect(result.white.mistake).toBe(0);
    expect(result.black.blunder).toBe(0);
  });

  it('derives side from ply parity, not is_user', () => {
    // Opponent's (is_user=false) inaccuracy at an even ply still lands in white.
    const markers = [marker({ ply: 2, severity: 'inaccuracy', is_user: false })];
    const result = severityCountsBySide(markers);
    expect(result.white.inaccuracy).toBe(1);
    expect(result.black.inaccuracy).toBe(0);
  });
});

describe('tierCountsBySide', () => {
  it('skips points with a null best_move_tier', () => {
    const points = [point({ ply: 0, best_move_tier: null }), point({ ply: 1, best_move_tier: null })];
    const result = tierCountsBySide(points);
    expect(result.white).toEqual({ gem: 0, great: 0, best: 0, good: 0 });
    expect(result.black).toEqual({ gem: 0, great: 0, best: 0, good: 0 });
  });

  it('counts gem/great/best/good by moverColorAtPly for BOTH sides', () => {
    const points = [
      point({ ply: 0, best_move_tier: 'gem' }), // white
      point({ ply: 1, best_move_tier: 'great' }), // black
      point({ ply: 2, best_move_tier: 'best' }), // white
      point({ ply: 3, best_move_tier: 'good' }), // black
    ];
    const result = tierCountsBySide(points);
    expect(result.white.gem).toBe(1);
    expect(result.white.best).toBe(1);
    expect(result.black.great).toBe(1);
    expect(result.black.good).toBe(1);
    expect(result.white.great).toBe(0);
    expect(result.black.gem).toBe(0);
  });
});
