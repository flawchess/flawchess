/**
 * engineEvalLookup unit tests — pure, deterministic (no jsdom/worker involved).
 *
 * Covers every <behavior> bullet from 162-01-PLAN.md Task 1 (grading-first
 * precedence, SEED-090):
 * - both-sources: a UCI present in both pvLines and gradeMapBySan resolves to
 *   the grading value, not the free-run value.
 * - not-yet-graded: a UCI present ONLY in pvLines still resolves to the
 *   free-run value (placeholder role preserved).
 * - gradeMap-only: a SAN-only move resolves via sanToUci to its UCI key.
 * - unresolvable SAN: skipped silently, no throw.
 * - neither source: getByUci returns null (no pool-grade fallback exists).
 * - getBySan/getByUci accessor round-trips.
 */

import { describe, it, expect } from 'vitest';
import {
  buildEvalLookup,
  getByUci,
  getBySan,
  resolveReconciledBest,
  rankReconciledCandidates,
} from './engineEvalLookup';
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

describe('buildEvalLookup — grading-first precedence (SEED-090, Phase 162 D-01)', () => {
  it('a move present in BOTH pvLines and gradeMap resolves to the grading value', () => {
    const pvLines = [pvLine('e2e4', 30, null, 20)];
    const gradeMapBySan = new Map<string, MoveGrade>([['e4', grade(999, null, 5)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    expect(getByUci(lookup, 'e2e4')).toEqual({ evalCp: 999, evalMate: null, depth: 5 });
  });

  it('a not-yet-graded move present ONLY in pvLines still resolves to the free-run value (placeholder role preserved)', () => {
    const pvLines = [pvLine('g1f3', 15, null, 18)];
    const gradeMapBySan = new Map<string, MoveGrade>([['Nf3', grade(-500, null, 6)]]);

    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    // 'Nf3' and 'g1f3' are the same move — grading wins on overlap, so this
    // asserts the OTHER direction: a move with no grading entry keeps its
    // free-run value.
    const pvLinesNoOverlap = [pvLine('g1f3', 15, null, 18)];
    const noOverlapLookup = buildEvalLookup(pvLinesNoOverlap, new Map<string, MoveGrade>(), START_FEN);
    expect(getByUci(noOverlapLookup, 'g1f3')?.evalCp).toBe(15);

    // And confirm the overlap direction resolves to the grading value.
    expect(getByUci(lookup, 'g1f3')?.evalCp).toBe(-500);
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
    // Free-run entries retain their PV (162 UAT card re-source).
    expect(getBySan(lookup, START_FEN, 'e4')).toEqual({ evalCp: 30, evalMate: null, depth: 20, pv: ['e2e4'] });
  });

  it('an unresolvable SAN returns null, not a throw', () => {
    const lookup = buildEvalLookup([], new Map(), START_FEN);
    expect(getBySan(lookup, START_FEN, 'Qxz9')).toBeNull();
  });
});

describe('resolveReconciledBest (Phase 162 D-03)', () => {
  it('argmax picks the highest-expected-score UCI', () => {
    // White-POV cp values, mover white: higher cp -> higher expected score.
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', grade(50)],
      ['d4', grade(200)],
      ['Nf3', grade(-100)],
    ]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);

    const best = resolveReconciledBest(lookup, ['e2e4', 'd2d4', 'g1f3'], 'white', null);

    expect(best).toBe('d2d4');
  });

  it('mirror-image best case: a candidate that is NOT tieBreakUci but has the top reconciled eval is returned', () => {
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', grade(30)],
      ['d4', grade(400)],
    ]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);

    // tieBreakUci pins e2e4 (the free-run pin), but d2d4 has the strictly
    // higher expected score and must win regardless.
    const best = resolveReconciledBest(lookup, ['e2e4', 'd2d4'], 'white', 'e2e4');

    expect(best).toBe('d2d4');
  });

  it('exact expected-score tie resolves toward tieBreakUci', () => {
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', grade(120)],
      ['d4', grade(120)],
    ]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);

    const best = resolveReconciledBest(lookup, ['e2e4', 'd2d4'], 'white', 'd2d4');

    expect(best).toBe('d2d4');
  });

  it('returns null when no candidate resolves to a grade', () => {
    const lookup = buildEvalLookup([], new Map<string, MoveGrade>(), START_FEN);

    const best = resolveReconciledBest(lookup, ['e2e4', 'd2d4'], 'white', null);

    expect(best).toBeNull();
  });

  it('a candidate absent from the lookup is skipped', () => {
    const gradeMapBySan = new Map<string, MoveGrade>([['e4', grade(80)]]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);

    // g1f3 has no entry in the lookup and must be skipped, leaving e2e4 as
    // the only resolvable candidate.
    const best = resolveReconciledBest(lookup, ['g1f3', 'e2e4'], 'white', null);

    expect(best).toBe('e2e4');
  });
});

describe('rankReconciledCandidates (162 UAT card re-source)', () => {
  it('returns every resolvable candidate sorted by descending expected score, skipping unresolved UCIs', () => {
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', grade(50)],
      ['d4', grade(200)],
      ['Nf3', grade(-100)],
    ]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);

    // a2a3 has no lookup entry — skipped, not a hole in the ranking.
    const ranked = rankReconciledCandidates(lookup, ['e2e4', 'a2a3', 'd2d4', 'g1f3'], 'white', null);

    expect(ranked.map((r) => r.uci)).toEqual(['d2d4', 'e2e4', 'g1f3']);
    expect(ranked[0]?.grade.evalCp).toBe(200);
  });

  it('its head IS resolveReconciledBest (one ranking, argmax = first element)', () => {
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', grade(120)],
      ['d4', grade(120)],
      ['Nf3', grade(90)],
    ]);
    const lookup = buildEvalLookup([], gradeMapBySan, START_FEN);
    const candidates = ['e2e4', 'd2d4', 'g1f3'];

    // Exact tie + tieBreakUci — the exact semantics the argmax documents.
    const ranked = rankReconciledCandidates(lookup, candidates, 'white', 'd2d4');
    const best = resolveReconciledBest(lookup, candidates, 'white', 'd2d4');

    expect(ranked[0]?.uci).toBe('d2d4');
    expect(best).toBe(ranked[0]?.uci);
  });

  it('mixed sources rank together: a grading candidate outranks a free-run-only line, and each entry carries its own pv', () => {
    // The UAT screenshot shape: the free run's top line (Rad1-analog e2e4,
    // +4.2) is outranked by a grading-union candidate (Bc1-analog d2d4, +4.3)
    // that the free run never searched.
    const pvLines = [pvLine('e2e4', 420, null, 19)];
    const gradeMapBySan = new Map<string, MoveGrade>([
      ['e4', { evalCp: 420, evalMate: null, depth: 22, pv: ['e2e4', 'e7e5'] }],
      ['d4', { evalCp: 430, evalMate: null, depth: 22, pv: ['d2d4', 'd7d5'] }],
    ]);
    const lookup = buildEvalLookup(pvLines, gradeMapBySan, START_FEN);

    const ranked = rankReconciledCandidates(lookup, ['e2e4', 'd2d4'], 'white', 'e2e4');

    expect(ranked.map((r) => r.uci)).toEqual(['d2d4', 'e2e4']);
    expect(ranked[0]?.grade.pv).toEqual(['d2d4', 'd7d5']);
    expect(ranked[1]?.grade.pv).toEqual(['e2e4', 'e7e5']);
  });

  it('returns [] when no candidate resolves', () => {
    const lookup = buildEvalLookup([], new Map<string, MoveGrade>(), START_FEN);
    expect(rankReconciledCandidates(lookup, ['e2e4'], 'white', null)).toEqual([]);
  });
});
