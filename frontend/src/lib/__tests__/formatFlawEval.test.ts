import { describe, expect, it } from 'vitest';
import { mateAtPly } from '../formatFlawEval';

describe('mateAtPly (mate count tracks the selected ply)', () => {
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
