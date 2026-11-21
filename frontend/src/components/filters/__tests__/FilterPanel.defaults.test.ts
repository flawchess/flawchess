// @vitest-environment jsdom
/**
 * Regression guard for the shared filter defaults (258 D-01, D-08).
 *
 * D-01: the recent-sample snapshots change no filter default. "All time" stays the untouched
 * default (recency and customRange null), and the quiet-time-control message never edits the
 * filter store, so there is nothing to reset.
 * D-08: no default opponent-strength filter (no default +-100 around the player's rating).
 */
import { describe, expect, it } from 'vitest';

import { ANY_RANGE } from '@/lib/opponentStrength';
import { DEFAULT_FILTERS } from '../FilterPanel';

describe('DEFAULT_FILTERS (258 D-01, D-08)', () => {
  it('keeps recency on "All time" (null)', () => {
    expect(DEFAULT_FILTERS.recency).toBeNull();
  });

  it('keeps the custom range empty (null)', () => {
    expect(DEFAULT_FILTERS.customRange).toBeNull();
  });

  it('keeps the opponent strength unrestricted', () => {
    expect(DEFAULT_FILTERS.opponentStrength).toEqual(ANY_RANGE);
  });
});
