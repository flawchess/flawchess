import { describe, expect, it } from 'vitest';
import { lineHasVisibleMotif } from '@/lib/tacticOrientation';
import type { FlawMarker } from '@/types/library';

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

describe('lineHasVisibleMotif', () => {
  it('is true for a user missed motif on a missed line', () => {
    const markers = [marker({ ply: 10, missed_tactic_motif: 'fork' })];
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'missed' })).toBe(true);
  });

  it('is false for the allowed orientation when only a missed motif exists', () => {
    const markers = [marker({ ply: 10, missed_tactic_motif: 'fork', allowed_tactic_motif: null })];
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'allowed' })).toBe(false);
  });

  it('is true for a user allowed motif on an allowed line', () => {
    const markers = [marker({ ply: 10, allowed_tactic_motif: 'pin' })];
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'allowed' })).toBe(true);
  });

  it('is true for an opponent marker with motifs (opponent chips are shown too)', () => {
    const markers = [
      marker({ ply: 10, is_user: false, missed_tactic_motif: 'fork', allowed_tactic_motif: 'pin' }),
    ];
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'missed' })).toBe(true);
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'allowed' })).toBe(true);
  });

  it('is false when no marker sits at the line ply', () => {
    const markers = [marker({ ply: 8, missed_tactic_motif: 'fork' })];
    expect(lineHasVisibleMotif(markers, { ply: 10, orientation: 'missed' })).toBe(false);
  });

  it('is false for null markers or a null line', () => {
    const markers = [marker({ ply: 10, missed_tactic_motif: 'fork' })];
    expect(lineHasVisibleMotif(null, { ply: 10, orientation: 'missed' })).toBe(false);
    expect(lineHasVisibleMotif(undefined, { ply: 10, orientation: 'missed' })).toBe(false);
    expect(lineHasVisibleMotif(markers, null)).toBe(false);
  });
});
