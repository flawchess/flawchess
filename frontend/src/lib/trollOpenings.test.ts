import { describe, it, expect, vi } from 'vitest';

// Mock the data module so this test is independent of Plan 02's curated set.
vi.mock('@/data/trollOpenings', () => ({
  WHITE_TROLL_KEYS: new Set([
    // Bongcloud-style fixture: position after 1.e4 e5 2.Ke2 (white-side-only key)
    '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR',
  ]),
  BLACK_TROLL_KEYS: new Set<string>(),
}));

import { deriveUserSideKey, isTrollPosition } from './trollOpenings';

describe('deriveUserSideKey', () => {
  it('returns the white-only key for the starting position (board-only FEN)', () => {
    expect(
      deriveUserSideKey('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 'white'),
    ).toBe('8/8/8/8/8/8/PPPPPPPP/RNBQKBNR');
  });

  it('returns the black-only key for the starting position', () => {
    expect(
      deriveUserSideKey('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 'black'),
    ).toBe('rnbqkbnr/pppppppp/8/8/8/8/8/8');
  });

  it('strips a single opponent pawn after 1.e4 e5 (full FEN with side-to-move token)', () => {
    expect(
      deriveUserSideKey(
        'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
        'white',
      ),
    ).toBe('8/8/8/8/4P3/8/PPPP1PPP/RNBQKBNR');
  });

  it('handles kings-only endgame (4 empties + K + 3 empties = 4K3)', () => {
    expect(deriveUserSideKey('8/8/8/8/8/8/8/4K2k', 'white')).toBe(
      '8/8/8/8/8/8/8/4K3',
    );
  });

  it('passes through the all-empty board unchanged', () => {
    expect(deriveUserSideKey('8/8/8/8/8/8/8/8', 'white')).toBe('8/8/8/8/8/8/8/8');
  });

  it('accepts board-only FEN (no side-to-move token) — same input shape from result_fen', () => {
    // result_fen is board.board_fen() per app/services/openings_service.py:350
    expect(
      deriveUserSideKey('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 'white'),
    ).toBe('8/8/8/8/8/8/PPPPPPPP/RNBQKBNR');
  });

  it('throws on invalid FEN with wrong rank count', () => {
    expect(() => deriveUserSideKey('8/8/8/8/8/8/8', 'white')).toThrow(/expected 8 ranks/);
  });
});

describe('isTrollPosition', () => {
  it('returns true when the derived white key is in WHITE_TROLL_KEYS', () => {
    // Bongcloud after 1.e4 e5 2.Ke2 — board FEN.
    // [Rule 1] Plan's original FEN was missing the white e4 pawn on rank 4
    // (rank 4 was '8' instead of '4P3'). After 1.e4 the white pawn lives on
    // e4; the corrected FEN has '4P3' on rank 4 so deriveUserSideKey strips
    // black pieces and yields '8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR' — which is
    // exactly the key the mock places in WHITE_TROLL_KEYS.
    const bongcloud = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR';
    expect(isTrollPosition(bongcloud, 'white')).toBe(true);
  });

  it('returns false for a position not in the curated set', () => {
    expect(
      isTrollPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 'white'),
    ).toBe(false);
  });

  it('routes to the correct side-set (Bongcloud key is white-only; black returns false)', () => {
    const bongcloud = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR';
    expect(isTrollPosition(bongcloud, 'black')).toBe(false);
  });

  it('returns false on malformed FEN instead of throwing — render-time safety', () => {
    // isTrollPosition is called unconditionally during render of every insights
    // card and move-explorer row. A bad FEN from the API must NOT crash the
    // surface — caller-side try/catch in every consumer would be fragile.
    expect(isTrollPosition('', 'white')).toBe(false);
    expect(isTrollPosition('not-a-fen', 'white')).toBe(false);
    expect(isTrollPosition('8/8/8/8/8/8/8', 'black')).toBe(false);
  });
});
