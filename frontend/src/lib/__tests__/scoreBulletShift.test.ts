/**
 * Phase 87.4 (Plan 02 Wave 0) — unit test for SCORE_GAP_BUCKET_DISPLAY_SHIFT.
 *
 * The shift is a presentation-layer affine that recenters the Conv/Parity/Recov
 * bullets on a single visual "zero" without mutating the underlying calibrated
 * zone bands. See CONTEXT.md D-03/D-04: shift values come from the midpoint of
 * each metric's calibrated typical band ([-0.11, 0.00] for Conv, [-0.04, +0.04]
 * for Parity, [+0.01, +0.11] for Recov).
 */

import { describe, it, expect } from 'vitest';

import { SCORE_GAP_BUCKET_DISPLAY_SHIFT } from '@/lib/endgameMetrics';
import type { MaterialBucket } from '@/types/endgames';

describe('SCORE_GAP_BUCKET_DISPLAY_SHIFT', () => {
  it('shifts conversion by -0.055 (midpoint of [-0.11, 0.00])', () => {
    expect(SCORE_GAP_BUCKET_DISPLAY_SHIFT.conversion).toBeCloseTo(-0.055, 6);
  });

  it('shifts parity by 0 (band already symmetric around zero)', () => {
    expect(SCORE_GAP_BUCKET_DISPLAY_SHIFT.parity).toBe(0);
  });

  it('shifts recovery by +0.06 (midpoint of [+0.01, +0.11])', () => {
    expect(SCORE_GAP_BUCKET_DISPLAY_SHIFT.recovery).toBeCloseTo(0.06, 6);
  });

  it('covers exactly the three MaterialBucket keys (no extras, no missing)', () => {
    const keys = Object.keys(SCORE_GAP_BUCKET_DISPLAY_SHIFT).sort();
    const expected: MaterialBucket[] = ['conversion', 'parity', 'recovery'];
    expect(keys).toEqual(expected.sort());
  });

  it('all shifts stay within the ScoreGapRow domain (|shift| < 0.1)', () => {
    for (const shift of Object.values(SCORE_GAP_BUCKET_DISPLAY_SHIFT)) {
      expect(Math.abs(shift)).toBeLessThan(0.1);
    }
  });
});
