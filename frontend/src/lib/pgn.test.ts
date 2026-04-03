import { describe, it, expect } from 'vitest';
import { pgnToSanArray } from './pgn';

describe('pgnToSanArray', () => {
  // ── Standard inputs ───────────────────────────────────────────────────────
  it('parses a standard 3-ply PGN into a SAN array', () => {
    expect(pgnToSanArray('1. e4 e5 2. Nf3')).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('parses a 5-ply PGN into a SAN array', () => {
    expect(pgnToSanArray('1. e4 c6 2. d4 d5 3. Nc3')).toEqual(['e4', 'c6', 'd4', 'd5', 'Nc3']);
  });

  // ── Edge cases ────────────────────────────────────────────────────────────
  it('returns an empty array for an empty string', () => {
    expect(pgnToSanArray('')).toEqual([]);
  });

  it('parses a single white move', () => {
    expect(pgnToSanArray('1. e4')).toEqual(['e4']);
  });

  // ── Multi-digit move numbers ───────────────────────────────────────────────
  it('correctly strips multi-digit move numbers', () => {
    expect(pgnToSanArray('10. Qd2 Bd7 11. O-O-O')).toEqual(['Qd2', 'Bd7', 'O-O-O']);
  });

  // ── Castling notation ─────────────────────────────────────────────────────
  it('preserves kingside castling notation O-O', () => {
    expect(pgnToSanArray('1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O')).toEqual([
      'e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O',
    ]);
  });

  it('preserves queenside castling notation O-O-O', () => {
    expect(pgnToSanArray('1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. O-O-O')).toEqual([
      'd4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'O-O-O',
    ]);
  });

  // ── Whitespace handling ───────────────────────────────────────────────────
  it('handles extra whitespace between tokens', () => {
    expect(pgnToSanArray('1.  e4   e5  2.  Nf3')).toEqual(['e4', 'e5', 'Nf3']);
  });

  it('handles leading and trailing whitespace', () => {
    expect(pgnToSanArray('  1. e4 e5  ')).toEqual(['e4', 'e5']);
  });
});
