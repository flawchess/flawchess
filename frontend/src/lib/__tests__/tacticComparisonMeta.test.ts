import { describe, it, expect } from 'vitest';

import { tacticMotifLabel, tacticMotifDefinition } from '@/lib/tacticComparisonMeta';
import { TACTIC_MOTIF_DEFINITIONS } from '@/lib/tacticMotifDefinitions';

// The nine mate-family motif strings stored on flaws (app/services/tactic_detector.py).
const MATE_MOTIFS = [
  'back-rank-mate',
  'smothered-mate',
  'anastasia-mate',
  'hook-mate',
  'arabian-mate',
  'boden-mate',
  'double-bishop-mate',
  'dovetail-mate',
  'mate',
];

describe('tacticMotifLabel', () => {
  it('collapses every mate-family motif to "checkmate" (Quick 260620-onv)', () => {
    for (const motif of MATE_MOTIFS) {
      expect(tacticMotifLabel(motif)).toBe('checkmate');
    }
  });

  it('leaves non-mate motifs unchanged', () => {
    expect(tacticMotifLabel('fork')).toBe('fork');
    expect(tacticMotifLabel('discovered-check')).toBe('discovered-check');
    expect(tacticMotifLabel('x-ray')).toBe('x-ray');
  });

  it('returns the raw string for an unknown motif', () => {
    expect(tacticMotifLabel('not-a-motif')).toBe('not-a-motif');
  });

  it('deduping marker motifs by label yields a single checkmate entry', () => {
    // Reproduces the game-card chip aggregation: two different mate subtypes in one
    // game must collapse to ONE "checkmate" chip, not two.
    const markerMotifs = ['back-rank-mate', 'mate', 'fork'];
    const labels = Array.from(new Set(markerMotifs.map(tacticMotifLabel)));
    expect(labels).toEqual(['checkmate', 'fork']);
  });
});

describe('tacticMotifDefinition', () => {
  it('gives every mate-family motif the same generic checkmate definition', () => {
    const generic = TACTIC_MOTIF_DEFINITIONS.checkmate;
    expect(generic).toBeTruthy();
    for (const motif of MATE_MOTIFS) {
      expect(tacticMotifDefinition(motif)).toBe(generic);
    }
  });

  it('returns the motif-specific definition for non-mate motifs', () => {
    expect(tacticMotifDefinition('fork')).toBe(TACTIC_MOTIF_DEFINITIONS.fork);
  });
});
