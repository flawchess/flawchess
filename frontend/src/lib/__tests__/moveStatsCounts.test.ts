import { describe, expect, it } from 'vitest';
import { severityCountsBySide, tierCountsBySide } from '@/lib/moveStatsCounts';
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

describe('severityCountsBySide', () => {
  it('returns both sides all-zero for an empty marker list', () => {
    const result = severityCountsBySide([]);
    expect(result.white).toEqual({ inaccuracy: 0, mistake: 0, blunder: 0 });
    expect(result.black).toEqual({ inaccuracy: 0, mistake: 0, blunder: 0 });
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

  it('derives side from ply parity, not is_user (D-08)', () => {
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

  it('counts gem/great/best/good by moverColorAtPly for BOTH sides (D-08)', () => {
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
