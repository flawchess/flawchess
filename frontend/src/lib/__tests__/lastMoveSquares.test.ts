import { describe, expect, it } from 'vitest';
import { lastMoveSquares } from '@/lib/sanToSquares';

describe('lastMoveSquares', () => {
  it('returns the from/to squares of the last move of a line', () => {
    expect(lastMoveSquares(['e4', 'c6', 'd4', 'd5', 'e5'])).toEqual({ from: 'e4', to: 'e5' });
  });

  it('resolves castling to the king squares', () => {
    expect(lastMoveSquares(['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O'])).toEqual({
      from: 'e1',
      to: 'g1',
    });
  });

  it('returns null for an empty or illegal line', () => {
    expect(lastMoveSquares([])).toBeNull();
    expect(lastMoveSquares(['e4', 'e4'])).toBeNull();
  });
});
