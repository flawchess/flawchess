/**
 * Tests for formatFlawEval utility (Phase 112, SC-6).
 *
 * Key invariants:
 * - White-POV → user-POV negation: black's eval is negated (Pitfall 3)
 * - Mate sign: user_color='black' + eval_mate=3 → "#-3" (white mates = bad for black user)
 * - cp formatting: signed 1-decimal pawns via formatSignedEvalPawns
 * - null → em-dash "—"
 * - Swing string joins before/after with " → "
 */

import { describe, expect, it } from 'vitest';
import { formatFlawEval, mateAtPly } from '../formatFlawEval';

describe('formatFlawEval', () => {
  describe('user-POV negation (SC-6)', () => {
    it('for user_color=black, eval_cp_before=-300 renders "+3.0" (negated)', () => {
      const result = formatFlawEval(-300, null, null, null, 'black');
      expect(result).toContain('+3.0');
    });

    it('for user_color=white, eval_cp_before=470 renders "+4.7"', () => {
      const result = formatFlawEval(470, null, null, null, 'white');
      expect(result).toContain('+4.7');
    });

    it('for user_color=white, eval_cp_before=-120 renders "-1.2"', () => {
      const result = formatFlawEval(-120, null, null, null, 'white');
      expect(result).toContain('-1.2');
    });

    it('for user_color=black, eval_cp_before=300 renders "-3.0" (negated positive becomes negative)', () => {
      const result = formatFlawEval(300, null, null, null, 'black');
      expect(result).toContain('-3.0');
    });
  });

  describe('mate sign (SC-6)', () => {
    it('for user_color=black, eval_mate_before=3 (white mates) renders "#-3"', () => {
      const result = formatFlawEval(null, 3, null, null, 'black');
      expect(result).toContain('#-3');
    });

    it('for user_color=white, eval_mate_before=3 renders "#3"', () => {
      const result = formatFlawEval(null, 3, null, null, 'white');
      expect(result).toContain('#3');
    });

    it('for user_color=black, eval_mate_before=-3 (black mates) renders "#3" (negated, good for user)', () => {
      const result = formatFlawEval(null, -3, null, null, 'black');
      expect(result).toContain('#3');
    });
  });

  describe('null eval', () => {
    it('null before renders "—" in the before part', () => {
      const result = formatFlawEval(null, null, 100, null, 'white');
      expect(result).toContain('—');
    });

    it('null after renders "—" in the after part', () => {
      const result = formatFlawEval(100, null, null, null, 'white');
      expect(result).toContain('—');
    });

    it('both null renders "— → —"', () => {
      expect(formatFlawEval(null, null, null, null, 'white')).toBe('— → —');
    });
  });

  describe('swing string format', () => {
    it('joins before and after with " → "', () => {
      const result = formatFlawEval(470, null, -120, null, 'white');
      expect(result).toBe('+4.7 → -1.2');
    });

    it('renders mate then cp: "+4.7 → #-3" (black user, cp before +4.7, white mate after)', () => {
      // For black user: eval_cp_before=-470 (white +4.7 means black -4.7 → after negation +4.7)
      // eval_mate_after=3 (white mates → after negation -3 → "#-3")
      const result = formatFlawEval(-470, null, null, 3, 'black');
      expect(result).toBe('+4.7 → #-3');
    });
  });

  describe('mateAtPly (Phase 135 UAT — mate count tracks the selected ply)', () => {
    // White mates in 3, white to move at the anchor: delivers on ply 2*3-1 = 5.
    // The count drops only when the mating side moves (every 2 plies).
    it('decrements only on the mating side move when mating side is to move at anchor', () => {
      expect(mateAtPly(3, 0, true)).toBe(3); // anchor
      expect(mateAtPly(3, 1, true)).toBe(2); // white moved → mate in 2
      expect(mateAtPly(3, 2, true)).toBe(2); // black moved → still 2
      expect(mateAtPly(3, 3, true)).toBe(1); // white moved → mate in 1
      expect(mateAtPly(3, 4, true)).toBe(1); // black moved → still 1
      expect(mateAtPly(3, 5, true)).toBe(0); // white delivers mate
    });

    // White mates in 3 but the defending side is to move at the anchor: delivers on
    // ply 2*3 = 6, so the first ply (defender) does not change the count.
    it('holds for the first ply when the defending side is to move at anchor', () => {
      expect(mateAtPly(3, 0, false)).toBe(3); // anchor (black to move)
      expect(mateAtPly(3, 1, false)).toBe(3); // black moved → white still mates in 3
      expect(mateAtPly(3, 2, false)).toBe(2); // white moved → mate in 2
      expect(mateAtPly(3, 6, false)).toBe(0); // mate delivered
    });

    it('preserves the sign for the side getting mated (white-POV negative)', () => {
      expect(mateAtPly(-2, 0, true)).toBe(-2);
      expect(mateAtPly(-2, 1, true)).toBe(-1);
      expect(mateAtPly(-2, 3, true)).toBe(0);
    });

    it('never returns a count past mate', () => {
      expect(mateAtPly(1, 5, true)).toBe(0);
    });
  });
});
