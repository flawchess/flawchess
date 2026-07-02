import { describe, expect, it } from 'vitest';
import { tacticOrientationAtPly } from '@/lib/tacticOrientation';
import type { FlawMarker } from '@/types/library';

// Quick 260702-fog: auto-open a tactic line when the board is deep-linked to a tactic ply.
// These cover the pure selection logic (which orientation, if any, to open).

function marker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 10,
    severity: 'blunder',
    tags: [],
    is_user: true,
    move_san: 'Qh5',
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

describe('tacticOrientationAtPly', () => {
  it('opens the missed line when only a missed tactic is present', () => {
    const markers = [marker({ ply: 10, missed_tactic_motif: 'fork' })];
    expect(tacticOrientationAtPly(markers, 10)).toBe('missed');
  });

  it('opens the allowed line when only an allowed tactic is present', () => {
    const markers = [marker({ ply: 10, allowed_tactic_motif: 'pin' })];
    expect(tacticOrientationAtPly(markers, 10)).toBe('allowed');
  });

  it('prefers the missed line when both missed and allowed are present', () => {
    const markers = [
      marker({ ply: 10, missed_tactic_motif: 'fork', allowed_tactic_motif: 'pin' }),
    ];
    expect(tacticOrientationAtPly(markers, 10)).toBe('missed');
  });

  it('returns null when the flaw at the ply has no tactic', () => {
    const markers = [marker({ ply: 10 })];
    expect(tacticOrientationAtPly(markers, 10)).toBeNull();
  });

  it('ignores opponent flaws (is_user=false)', () => {
    const markers = [marker({ ply: 10, is_user: false, missed_tactic_motif: 'fork' })];
    expect(tacticOrientationAtPly(markers, 10)).toBeNull();
  });

  it('returns null when no marker exists at the requested ply', () => {
    const markers = [marker({ ply: 8, missed_tactic_motif: 'fork' })];
    expect(tacticOrientationAtPly(markers, 10)).toBeNull();
  });

  it('returns null for null/undefined markers or null ply', () => {
    expect(tacticOrientationAtPly(null, 10)).toBeNull();
    expect(tacticOrientationAtPly(undefined, 10)).toBeNull();
    expect(tacticOrientationAtPly([marker({ ply: 10, missed_tactic_motif: 'fork' })], null)).toBeNull();
  });
});
