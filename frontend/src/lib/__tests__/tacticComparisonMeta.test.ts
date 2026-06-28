import { describe, it, expect } from 'vitest';

import {
  tacticMotifLabel,
  tacticMotifDefinition,
  tacticDepthBadge,
  TACTIC_FAMILY_FOR_MOTIF,
} from '@/lib/tacticComparisonMeta';
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

describe('family mapping coverage', () => {
  it('maps promotion (28) to a family now that D-09 is reversed', () => {
    expect(TACTIC_FAMILY_FOR_MOTIF.promotion).toBe('promotion');
    // It must also carry a chip definition so the popover body is not the raw string.
    expect(TACTIC_MOTIF_DEFINITIONS.promotion).toBeTruthy();
  });

  it('keeps self-interference (14) family-less', () => {
    expect(TACTIC_FAMILY_FOR_MOTIF['self-interference']).toBeUndefined();
  });
});

describe('tacticDepthBadge', () => {
  // Regression for the leak where a family-less motif's depth still rendered on the
  // miniboard as a bare number with no chip. The badge shows only when the motif
  // resolves to a visible family ("show the depth iff there is a chip").
  it('returns the orientation-aware display depth for a mapped motif', () => {
    // missed = raw + 1; allowed = raw + 1 + 1 (decision-anchored offset).
    expect(tacticDepthBadge('fork', 0, 'missed')).toBe('1');
    expect(tacticDepthBadge('fork', 0, 'allowed')).toBe('2');
    expect(tacticDepthBadge('promotion', 5, 'allowed')).toBe('7');
  });

  it('returns null for a family-less motif even when depth is present', () => {
    expect(tacticDepthBadge('self-interference', 8, 'allowed')).toBeNull();
    expect(tacticDepthBadge('not-a-motif', 3, 'missed')).toBeNull();
  });

  it('returns null when the motif or depth is null', () => {
    expect(tacticDepthBadge(null, 5, 'allowed')).toBeNull();
    expect(tacticDepthBadge('fork', null, 'missed')).toBeNull();
  });

  // anchored=false (Quick 260628-1t5 DECISION 2): navigable surfaces drop the allowed +1
  // offset, so an allowed badge reads on the same plain scale as missed.
  it('anchored=false drops the allowed offset (allowed reads like missed)', () => {
    expect(tacticDepthBadge('fork', 0, 'allowed', false)).toBe('1');
    expect(tacticDepthBadge('promotion', 5, 'allowed', false)).toBe('6');
    // missed is unaffected by the flag.
    expect(tacticDepthBadge('fork', 0, 'missed', false)).toBe('1');
  });
});
