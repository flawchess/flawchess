import { describe, it, expect } from 'vitest';
import { sanToSquares } from './sanToSquares';

const STARTING_FEN_WHITE = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// FEN with kingside castling legal for white (king + rook on home squares, no
// pieces between, castling rights present). Same for black on a separate FEN.
const KINGSIDE_CASTLE_WHITE_FEN =
  'rnbqkbnr/pppppppp/8/8/4P3/5N2/PPPPBPPP/RNBQK2R w KQkq - 0 1';
const KINGSIDE_CASTLE_BLACK_FEN =
  'rnbqk2r/ppppbppp/5n2/4p3/4P3/5N2/PPPPBPPP/RNBQK2R b KQkq - 0 1';

describe('sanToSquares', () => {
  it('returns { from: e2, to: e4 } for the e4 opening move', () => {
    const result = sanToSquares(STARTING_FEN_WHITE, 'e4');
    expect(result).toEqual({ from: 'e2', to: 'e4' });
  });

  it('returns { from: b1, to: c3 } for Nc3 from the starting position', () => {
    const result = sanToSquares(STARTING_FEN_WHITE, 'Nc3');
    expect(result).toEqual({ from: 'b1', to: 'c3' });
  });

  it('handles kingside castling for white (O-O → e1/g1)', () => {
    const result = sanToSquares(KINGSIDE_CASTLE_WHITE_FEN, 'O-O');
    expect(result).toEqual({ from: 'e1', to: 'g1' });
  });

  it('handles kingside castling for black (O-O → e8/g8)', () => {
    const result = sanToSquares(KINGSIDE_CASTLE_BLACK_FEN, 'O-O');
    expect(result).toEqual({ from: 'e8', to: 'g8' });
  });

  it('returns null on illegal/unparseable SAN', () => {
    const result = sanToSquares(STARTING_FEN_WHITE, 'xx99');
    expect(result).toBeNull();
  });

  it('returns null on a SAN that is illegal in the given FEN (without throwing)', () => {
    // Nxd4 is illegal from the starting position — no knight can capture on d4.
    expect(() => sanToSquares(STARTING_FEN_WHITE, 'Nxd4')).not.toThrow();
    expect(sanToSquares(STARTING_FEN_WHITE, 'Nxd4')).toBeNull();
  });

  it('returns null on a malformed FEN without throwing', () => {
    expect(() => sanToSquares('this is not a fen', 'e4')).not.toThrow();
    expect(sanToSquares('this is not a fen', 'e4')).toBeNull();
  });
});
