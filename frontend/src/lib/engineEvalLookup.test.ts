/**
 * engineEvalLookup unit tests — pure, deterministic (no jsdom/worker involved).
 *
 * Covers every <behavior> bullet from 158-02-PLAN.md Task 1:
 * - both-sources: a UCI present in both pvLines and gradeMapBySan resolves to
 *   the free-run value, never the grading value (precedence never regresses).
 * - gradeMap-only: a SAN-only move resolves via sanToUci to its UCI key.
 * - unresolvable SAN: skipped silently, no throw.
 * - neither source: getByUci returns null (no pool-grade fallback exists).
 * - getBySan/getByUci accessor round-trips.
 */

import { describe, it, expect } from 'vitest';
import { buildEvalLookup, getByUci, getBySan } from './engineEvalLookup';
import type { PvLine } from '@/hooks/uciParser';
import type { MoveGrade } from '@/lib/moveQuality';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Minimal PvLine fixture — evalCp/evalMate/depth + moves[0] are the only fields this module reads. */
function pvLine(uci: string, evalCp: number | null, evalMate: number | null = null, depth = 12): PvLine {
  return { multipv: 1, depth, moves: [uci], evalCp, evalMate };
}

function grade(evalCp: number | null, evalMate: number | null = null, depth = 8): MoveGrade {
  return { evalCp, evalMate, depth };
}

describe('buildEvalLookup — free-run-first precedence (SEED-087 SC1)', () => {
  it('a move present in BOTH pvLines and gradeMap resolves to the free-run value', () => {
    const pvLines = [pvLine('e2e4', 30, null, 20)];
    const gradeMapBySan = new Map<string, MoveGrade>([['e4', grade(999, null, 5)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getByUci(lookup, 'e2e4')).toEqual({ evalCp: 30, evalMate: null, depth: 20 });
  });

  it('precedence never regresses: free-run entry inserted first is not overwritten by a later-processed gradeMap entry for the same move', () => {
    const pvLines = [pvLine('g1f3', 15, null, 18)];
    const gradeMapBySan = new Map<string, MoveGrade>([['Nf3', grade(-500, null, 6)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getByUci(lookup, 'g1f3')?.evalCp).toBe(15);
  });
});

describe('buildEvalLookup — gradeMap-only moves resolved via sanToUci', () => {
  it('a move present ONLY in gradeMapBySan converts via sanToUci and is inserted under its UCI key', () => {
    const pvLines = [pvLine('e2e4', 30)];
    const gradeMapBySan = new Map<string, MoveGrade>([['d4', grade(45, null, 7)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getByUci(lookup, 'd2d4')).toEqual({ evalCp: 45, evalMate: null, depth: 7 });
  });

  it('a SAN in gradeMapBySan that sanToUci cannot resolve is skipped, no throw', () => {
    const pvLines = [pvLine('e2e4', 30)];
    const gradeMapBySan = new Map<string, MoveGrade>([['Qxz9', grade(45, null, 7)]]);

    expect(() => buildEvalLookup(pvLines, gradeMapBySan, START_FEN)).not.toThrow();
    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);
    expect(lookup.size).toBe(1); // only e2e4 from pvLines; the unresolvable SAN never lands
  });
});

describe('buildEvalLookup — no pool-grade fallback', () => {
  it('a UCI in neither source resolves to null (there is no third parameter to fall back to)', () => {
    const pvLines = [pvLine('e2e4', 30)];
    const gradeMapBySan = new Map<string, MoveGrade>([['d4', grade(45)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getByUci(lookup, 'a2a3')).toBeNull();
  });
});

describe('getBySan', () => {
  it('resolves a SAN via sanToUci then getByUci, returning the same MoveGrade as getByUci', () => {
    const pvLines = [pvLine('e2e4', 30, null, 20)];
    const gradeMapBySan = new Map<string, MoveGrade>();

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getBySan(lookup, START_FEN, 'e4')).toEqual(getByUci(lookup, 'e2e4'));
    expect(getBySan(lookup, START_FEN, 'e4')).toEqual({ evalCp: 30, evalMate: null, depth: 20 });
  });

  it('an unresolvable SAN returns null, not a throw', () => {
    const lookup = buildEvalLookup([], new Map(), START_FEN);
    expect(getBySan(lookup, START_FEN, 'Qxz9')).toBeNull();
  });
});
