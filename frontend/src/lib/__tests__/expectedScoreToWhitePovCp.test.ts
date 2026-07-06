/**
 * expectedScoreToWhitePovCp table test (Phase 155 Plan 01, D-06 / DISPLAY-03).
 *
 * Verifies the inverse-sigmoid conversion from a 0-1 root-STM expected score
 * (RankedLine.practicalScore) to a white-POV centipawn value, including the
 * mate-boundary guards (Pitfall 2 regression guard — a naive log-odds inversion
 * produces ±Infinity/NaN at es<=0 / es>=1).
 */

import { describe, it, expect } from 'vitest';
import { expectedScoreToWhitePovCp, evalToExpectedScore } from '../liveFlaw';
import { MATE_CP_EQUIVALENT } from '@/generated/flawThresholds';

describe('expectedScoreToWhitePovCp', () => {
  it('converts a mid-range white-STM expected score to a positive white-POV cp', () => {
    expect(expectedScoreToWhitePovCp(0.9, 'white')).toBeCloseTo(596.6, 0);
  });

  it('converts a mid-range black-STM expected score to a negative white-POV cp', () => {
    expect(expectedScoreToWhitePovCp(0.9, 'black')).toBeCloseTo(-596.6, 0);
  });

  it('maps es=0 (white STM, forced loss) to -MATE_CP_EQUIVALENT', () => {
    expect(expectedScoreToWhitePovCp(0, 'white')).toBe(-MATE_CP_EQUIVALENT);
  });

  it('maps es=0 (black STM, forced loss for black = white winning) to +MATE_CP_EQUIVALENT', () => {
    expect(expectedScoreToWhitePovCp(0, 'black')).toBe(MATE_CP_EQUIVALENT);
  });

  it('maps es=1 (white STM, forced win) to +MATE_CP_EQUIVALENT', () => {
    expect(expectedScoreToWhitePovCp(1, 'white')).toBe(MATE_CP_EQUIVALENT);
  });

  it('maps es=1 (black STM, forced win for black) to -MATE_CP_EQUIVALENT', () => {
    expect(expectedScoreToWhitePovCp(1, 'black')).toBe(-MATE_CP_EQUIVALENT);
  });

  it('never returns NaN or Infinity for any es in [0, 1]', () => {
    for (const es of [0, 0.001, 0.25, 0.5, 0.75, 0.999, 1]) {
      for (const rootMover of ['white', 'black'] as const) {
        const cp = expectedScoreToWhitePovCp(es, rootMover);
        expect(Number.isFinite(cp)).toBe(true);
      }
    }
  });

  it('round-trips through evalToExpectedScore for a mid-range cp (white)', () => {
    const originalCp = 250;
    const es = evalToExpectedScore(originalCp, null, 'white');
    const roundTripCp = expectedScoreToWhitePovCp(es, 'white');
    expect(roundTripCp).toBeCloseTo(originalCp, 0);
  });

  it('round-trips through evalToExpectedScore for a mid-range cp (black)', () => {
    const originalCp = -150;
    const es = evalToExpectedScore(originalCp, null, 'black');
    const roundTripCp = expectedScoreToWhitePovCp(es, 'black');
    expect(roundTripCp).toBeCloseTo(originalCp, 0);
  });
});
