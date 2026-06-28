/**
 * resolveVisibleTactic unit tests — Quick 260625-qbj.
 *
 * resolveVisibleTactic is the single source of truth deciding whether a tactic slot's
 * chip AND depth badge render. These tests pin it to two contracts:
 *   1. The family guard (family-less motifs → null) shared with tacticDepthBadge.
 *   2. The live-filter predicate, which must mirror the backend tactic_slot_visible
 *      (app/repositories/library_repository.py) axis-for-axis — orientation scope,
 *      family narrowing, and the decision-anchored depth range with the +1 allowed
 *      offset. If the two drift, the FE↔BE parity cases below fail.
 */

import { describe, expect, it } from 'vitest';
import { resolveVisibleTactic, tacticDepthBadge } from '@/lib/tacticComparisonMeta';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// A family-having motif (Advanced family 'sacrifice') and a family-less one
// (self-interference maps to no family — D-09).
const SACRIFICE = 'sacrifice';
const FAMILYLESS = 'self-interference';

function filterWith(overrides: Partial<FlawFilterState>): FlawFilterState {
  return { ...DEFAULT_FLAW_FILTER, ...overrides };
}

describe('resolveVisibleTactic — family guard (no filter)', () => {
  it('returns the bundled chip + depth for a family-having motif', () => {
    // missed display depth = raw + 1.
    expect(resolveVisibleTactic('missed', SACRIFICE, 2)).toEqual({
      motif: SACRIFICE,
      motifLabel: SACRIFICE,
      depthLabel: '3',
    });
  });

  it('returns null for a family-less motif (chip self-nullifies → no bare depth)', () => {
    expect(resolveVisibleTactic('missed', FAMILYLESS, 2)).toBeNull();
  });

  it('returns null when the motif is absent', () => {
    expect(resolveVisibleTactic('missed', null, 2)).toBeNull();
  });

  it('keeps the chip but emits no depth label when depth is null', () => {
    expect(resolveVisibleTactic('missed', SACRIFICE, null)).toEqual({
      motif: SACRIFICE,
      motifLabel: SACRIFICE,
      depthLabel: null,
    });
  });

  it('applies the +1 decision-anchored offset to the allowed orientation', () => {
    // allowed display depth = raw + 1 + 1.
    expect(resolveVisibleTactic('allowed', SACRIFICE, 2)?.depthLabel).toBe('4');
  });

  // anchored=false (Quick 260628-1t5 DECISION 2): navigable surfaces drop the allowed +1
  // offset on the DISPLAY depth only. The filter predicate is untouched (see below).
  it('anchored=false drops the allowed offset on the depth label (display only)', () => {
    // allowed display depth without anchor = raw + 1 (reads like missed).
    expect(resolveVisibleTactic('allowed', SACRIFICE, 2, undefined, false)?.depthLabel).toBe('3');
    // missed is unaffected by the flag.
    expect(resolveVisibleTactic('missed', SACRIFICE, 2, undefined, false)?.depthLabel).toBe('3');
  });
});

describe('tacticDepthBadge — thin delegate over resolveVisibleTactic', () => {
  it('returns the depth string for a family-having motif', () => {
    expect(tacticDepthBadge(SACRIFICE, 2, 'missed')).toBe('3');
  });

  it('returns null for a family-less motif', () => {
    expect(tacticDepthBadge(FAMILYLESS, 2, 'missed')).toBeNull();
  });

  it('returns null when depth is null', () => {
    expect(tacticDepthBadge(SACRIFICE, null, 'missed')).toBeNull();
  });
});

describe('resolveVisibleTactic — live filter mirrors backend tactic_slot_visible', () => {
  it('hides a slot whose orientation is out of scope', () => {
    const filter = filterWith({ tacticOrientation: 'allowed' });
    expect(resolveVisibleTactic('missed', SACRIFICE, 2, filter)).toBeNull();
    expect(resolveVisibleTactic('allowed', SACRIFICE, 2, filter)).not.toBeNull();
  });

  it('narrows by family — non-matching family is hidden', () => {
    const filter = filterWith({ tacticFamilies: ['sacrifice'] });
    expect(resolveVisibleTactic('missed', SACRIFICE, 2, filter)).not.toBeNull();
    expect(resolveVisibleTactic('missed', 'fork', 2, filter)).toBeNull();
  });

  it('skips the depth-range check entirely on the full range', () => {
    // DEFAULT_FLAW_FILTER is the full range 0..11 → a deep tactic still passes.
    expect(resolveVisibleTactic('allowed', SACRIFICE, 9, DEFAULT_FLAW_FILTER)).not.toBeNull();
  });

  it('applies the decision-anchored depth range (allowed gets +1) — FE↔BE parity', () => {
    const filter = filterWith({ tacticDepthMin: 0, tacticDepthMax: 5 });
    // missed: anchored = raw 5 = 5 ≤ 5 → visible.
    expect(resolveVisibleTactic('missed', SACRIFICE, 5, filter)).not.toBeNull();
    // allowed: anchored = 5 + 1 = 6 > 5 → hidden (the offset the backend applies).
    expect(resolveVisibleTactic('allowed', SACRIFICE, 5, filter)).toBeNull();
    // allowed: anchored = 4 + 1 = 5 ≤ 5 → visible.
    expect(resolveVisibleTactic('allowed', SACRIFICE, 4, filter)).not.toBeNull();
  });

  it('hides a slot with no depth once the range is active', () => {
    const filter = filterWith({ tacticDepthMin: 0, tacticDepthMax: 5 });
    expect(resolveVisibleTactic('missed', SACRIFICE, null, filter)).toBeNull();
  });
});
