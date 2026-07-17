import { describe, expect, it } from 'vitest';
import { isUserPly } from '@/lib/plyOwnership';

describe('isUserPly', () => {
  it('assigns even plies to White and odd plies to Black', () => {
    // White user: only even plies (0, 2, 4…) are the user's moves.
    expect(isUserPly(0, 'white')).toBe(true);
    expect(isUserPly(1, 'white')).toBe(false);
    expect(isUserPly(2, 'white')).toBe(true);
    expect(isUserPly(3, 'white')).toBe(false);
  });

  it('assigns odd plies to a Black user', () => {
    expect(isUserPly(0, 'black')).toBe(false);
    expect(isUserPly(1, 'black')).toBe(true);
    expect(isUserPly(2, 'black')).toBe(false);
    expect(isUserPly(3, 'black')).toBe(true);
  });

  it('returns false for an unknown/invalid user color (ownership undefined without a known color)', () => {
    expect(isUserPly(0, 'free')).toBe(false);
    expect(isUserPly(1, '')).toBe(false);
  });
});
