/**
 * terminalPositionEval test (Quick 260709-j3k).
 *
 * A checkmated position reports an ambiguous `mate 0` from the live engine, which
 * upstream read as the 0.5 midpoint — snapping the eval bar to equal and grading the
 * mating move as a blunder. terminalPositionEval derives the eval from the rules
 * instead: white-POV decisive on a checkmate, dead-equal on a draw, null mid-game.
 */

import { describe, it, expect } from 'vitest';
import { terminalPositionEval } from '../liveFlaw';

describe('terminalPositionEval', () => {
  it('returns a positive white-POV mate when White delivers checkmate', () => {
    // Fool's mate: 1. f3 e5 2. g4 Qh4#. Black just moved; White (to move) is mated,
    // so the mate is Black's — white-POV negative.
    const blackMated = 'rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3';
    expect(terminalPositionEval(blackMated)).toEqual({ cp: null, mate: -1 });
  });

  it('returns a negative-signed mate keyed to the mated side to move', () => {
    // Scholar's mate: White delivers Qxf7#. Black (to move) is mated → white-POV positive.
    const whiteWins = 'r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4';
    expect(terminalPositionEval(whiteWins)).toEqual({ cp: null, mate: 1 });
  });

  it('returns dead-equal (cp 0) for a stalemate', () => {
    // Classic king+pawn stalemate, Black to move with no legal move.
    const stalemate = 'k7/P7/1K6/8/8/8/8/8 b - - 0 1';
    expect(terminalPositionEval(stalemate)).toEqual({ cp: 0, mate: null });
  });

  it('returns null for a position that is still in progress', () => {
    const startpos = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    expect(terminalPositionEval(startpos)).toBeNull();
  });

  it('returns null for a malformed FEN instead of throwing', () => {
    expect(terminalPositionEval('not a fen')).toBeNull();
  });
});
