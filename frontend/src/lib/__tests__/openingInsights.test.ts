/**
 * Tests for openingInsights.ts utilities.
 *
 * Phase 112 (D-04): formatMoveNotation extracted as a shared primitive;
 * formatCandidateMove now delegates to it. Both are tested here.
 */

import { describe, expect, it } from 'vitest';
import { formatCandidateMove, formatMoveNotation } from '../openingInsights';

describe('formatMoveNotation', () => {
  it('returns "N. san" for white (even ply index)', () => {
    expect(formatMoveNotation(0, 'e4')).toBe('1. e4');
    expect(formatMoveNotation(2, 'Nxd4')).toBe('2. Nxd4');
    expect(formatMoveNotation(4, 'Nc3')).toBe('3. Nc3');
  });

  it('returns "N... san" for black (odd ply index)', () => {
    expect(formatMoveNotation(1, 'e5')).toBe('1... e5');
    expect(formatMoveNotation(3, 'c5')).toBe('2... c5');
    expect(formatMoveNotation(5, 'Nf6')).toBe('3... Nf6');
  });
});

describe('formatCandidateMove', () => {
  it('matches formatMoveNotation(seq.length, san) for white ply', () => {
    const seq = ['e4', 'e5'];
    const san = 'Nf3';
    expect(formatCandidateMove(seq, san)).toBe(formatMoveNotation(seq.length, san));
  });

  it('matches formatMoveNotation(seq.length, san) for black ply', () => {
    const seq = ['e4'];
    const san = 'e5';
    expect(formatCandidateMove(seq, san)).toBe(formatMoveNotation(seq.length, san));
  });

  it('works for empty sequence (first move)', () => {
    expect(formatCandidateMove([], 'e4')).toBe('1. e4');
    expect(formatCandidateMove([], 'e4')).toBe(formatMoveNotation(0, 'e4'));
  });

  it('returns "4. Nxd4" for entrySanSequence of length 6 (white ply)', () => {
    const seq = ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'];
    expect(formatCandidateMove(seq, 'Nxd4')).toBe('4. Nxd4');
  });

  it('returns "3... c5" for entrySanSequence of length 5 (black ply)', () => {
    const seq = ['e4', 'e5', 'Nf3', 'Nc6', 'd4'];
    expect(formatCandidateMove(seq, 'c5')).toBe('3... c5');
  });
});
