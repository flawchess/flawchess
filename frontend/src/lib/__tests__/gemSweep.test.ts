/**
 * gemSweep unit tests — pure, deterministic (no engine/worker involved).
 *
 * Wave 0 gap identified in 172-VALIDATION.md. Traces 1:1 to the plan's
 * <behavior> contract for `selectSweepCandidates` (D-04 free prefilter) and
 * `nextSweepDispatch` (D-05 yield-to-cursor scheduler decision).
 *
 * Two cases are load-bearing and are the project's regression guard against
 * the phase's two silent-failure modes (see 172-RESEARCH.md Common Pitfalls
 * 2 and 4, and the project's mutation-test-gap-closure memory: prove a gap
 * fix by REVERTING it and confirming tests fail, not by grep/symbol
 * presence):
 *   1. The SAN-vs-UCI case — a naive string compare would silently drop
 *      every candidate.
 *   2. The `liveBusy` case — the D-05 yield-to-cursor invariant. Deleting
 *      the `liveBusy` guard from `nextSweepDispatch` MUST turn this test
 *      red; see the manually-recorded revert proof in 172-02-SUMMARY.md.
 */

import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import {
  selectSweepCandidates,
  nextSweepDispatch,
  resolveGemVerdict,
  type SweepCandidate,
} from '../gemSweep';
import type { EvalPoint } from '@/types/library';

const START_FEN = new Chess().fen();

function evalPoint(overrides: Partial<EvalPoint>): EvalPoint {
  return {
    ply: 0,
    es: null,
    eval_cp: null,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    ...overrides,
  };
}

function fenAfter(moves: string[]): (i: number) => string | null {
  // Returns the FEN BEFORE moves[i] was played, for a fixed mainline.
  const fens: string[] = [START_FEN];
  const chess = new Chess(START_FEN);
  for (const san of moves) {
    chess.move(san);
    fens.push(chess.fen());
  }
  return (i: number) => fens[i] ?? null;
}

// ─── selectSweepCandidates ──────────────────────────────────────────────────

describe('selectSweepCandidates', () => {
  it('LOAD-BEARING (RESEARCH Pitfall 2): a SAN played move ("Nf3") whose UCI equivalent ("g1f3") matches best_move survives — a naive string compare would drop it', () => {
    const moves = ['Nf3'];
    const evalSeries = [evalPoint({ ply: 0, best_move: 'g1f3' })];
    const result = selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves));
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual<SweepCandidate>({
      plyIndex: 0,
      parentFen: START_FEN,
      playedSan: 'Nf3',
    });

    // Direct proof the naive string-compare trap is real: SAN !== UCI.
    expect('Nf3').not.toBe('g1f3');
  });

  it('a ply whose played SAN differs from best_move is dropped', () => {
    const moves = ['e4'];
    const evalSeries = [evalPoint({ ply: 0, best_move: 'd2d4' })]; // best was d4, not e4
    const result = selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves));
    expect(result).toHaveLength(0);
  });

  it('D-04/D-06/D-08: a ply with index < openingPlyCount is dropped even when the played move IS the best move (book gate)', () => {
    const moves = ['e4'];
    const evalSeries = [evalPoint({ ply: 0, best_move: 'e2e4' })]; // played === best
    const result = selectSweepCandidates(moves, evalSeries, 1, fenAfter(moves)); // openingPlyCount=1 covers ply 0
    expect(result).toHaveLength(0);
  });

  it('a ply with best_move === null is dropped', () => {
    const moves = ['e4'];
    const evalSeries = [evalPoint({ ply: 0, best_move: null })];
    const result = selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves));
    expect(result).toHaveLength(0);
  });

  it('an out-of-range evalSeries[i] is skipped without throwing (noUncheckedIndexedAccess)', () => {
    const moves = ['e4', 'e5'];
    const evalSeries = [evalPoint({ ply: 0, best_move: 'e2e4' })]; // evalSeries[1] is undefined
    expect(() => selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves))).not.toThrow();
    const result = selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves));
    expect(result).toHaveLength(1);
    expect(result[0]?.plyIndex).toBe(0);
  });

  it('an out-of-range moves[i] is skipped without throwing', () => {
    const moves = ['e4'];
    const evalSeries = [
      evalPoint({ ply: 0, best_move: 'e2e4' }),
      evalPoint({ ply: 1, best_move: 'e7e5' }), // moves[1] is undefined
    ];
    expect(() =>
      selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves)),
    ).not.toThrow();
  });

  it('a null fenAtPly result is skipped without throwing', () => {
    const moves = ['e4'];
    const evalSeries = [evalPoint({ ply: 0, best_move: 'e2e4' })];
    const result = selectSweepCandidates(moves, evalSeries, 0, () => null);
    expect(result).toHaveLength(0);
  });

  it('candidates come back in ascending ply order, each carrying plyIndex/parentFen/playedSan', () => {
    // Italian Game opening: 1.e4 e5 2.Nf3 Nc6 3.Bc4 — every move matches "best" for this fixture.
    const moves = ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4'];
    const bestUcis = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4'];
    const evalSeries = moves.map((_san, i) => evalPoint({ ply: i, best_move: bestUcis[i] ?? null }));
    const result = selectSweepCandidates(moves, evalSeries, 0, fenAfter(moves));
    expect(result.map((c) => c.plyIndex)).toEqual([0, 1, 2, 3, 4]);
    expect(result.map((c) => c.playedSan)).toEqual(moves);
  });
});

// ─── nextSweepDispatch ──────────────────────────────────────────────────────

const CANDIDATE_A: SweepCandidate = { plyIndex: 4, parentFen: START_FEN, playedSan: 'Nf3' };
const CANDIDATE_B: SweepCandidate = { plyIndex: 8, parentFen: START_FEN, playedSan: 'e4' };

function baseInput(overrides: Partial<import('../gemSweep').SweepDispatchInput> = {}) {
  return {
    candidates: [CANDIDATE_A, CANDIDATE_B],
    resolvedPlyIndices: new Set<number>(),
    inFlight: null,
    liveBusy: false,
    tabHidden: false,
    enabled: true,
    ...overrides,
  };
}

describe('nextSweepDispatch', () => {
  it('LOAD-BEARING (D-05 yield-to-cursor invariant): returns idle when liveBusy is true, even with unresolved candidates present and nothing in flight — deleting the liveBusy guard MUST turn this test red', () => {
    const result = nextSweepDispatch(baseInput({ liveBusy: true, inFlight: null }));
    expect(result).toEqual({ kind: 'idle' });
  });

  it('returns idle when tabHidden is true', () => {
    expect(nextSweepDispatch(baseInput({ tabHidden: true }))).toEqual({ kind: 'idle' });
  });

  it('returns idle when enabled is false', () => {
    expect(nextSweepDispatch(baseInput({ enabled: false }))).toEqual({ kind: 'idle' });
  });

  it('returns idle when a candidate is already inFlight (one at a time)', () => {
    expect(nextSweepDispatch(baseInput({ inFlight: CANDIDATE_A }))).toEqual({ kind: 'idle' });
  });

  it('dispatches the lowest-plyIndex candidate not present in resolvedPlyIndices', () => {
    const result = nextSweepDispatch(baseInput());
    expect(result).toEqual({ kind: 'dispatch', candidate: CANDIDATE_A });
  });

  it('skips already-resolved candidates and dispatches the next unresolved one', () => {
    const result = nextSweepDispatch(
      baseInput({ resolvedPlyIndices: new Set([CANDIDATE_A.plyIndex]) }),
    );
    expect(result).toEqual({ kind: 'dispatch', candidate: CANDIDATE_B });
  });

  it('returns done when every candidate is resolved and nothing is in flight', () => {
    const result = nextSweepDispatch(
      baseInput({
        resolvedPlyIndices: new Set([CANDIDATE_A.plyIndex, CANDIDATE_B.plyIndex]),
      }),
    );
    expect(result).toEqual({ kind: 'done' });
  });

  it('returns done for an empty candidates array', () => {
    const result = nextSweepDispatch(baseInput({ candidates: [] }));
    expect(result).toEqual({ kind: 'done' });
  });
});

// ─── resolveGemVerdict (CR-01 precedence) ───────────────────────────────────

interface Detail {
  maiaProbability: number;
  elo: number;
  byOpponent: boolean;
}
const GEM: Detail = { maiaProbability: 0.01, elo: 1500, byOpponent: false };

describe('resolveGemVerdict', () => {
  it("LOAD-BEARING (CR-01): a live null rejection wins over the sweep's gem for the SAME node/ply — the sweep is NEVER consulted once gemByNode has an answer; reverting to a `?? ` collapse MUST turn this red", () => {
    // The live path graded this node and REJECTED it (null). The background
    // sweep, grading at a 4x-shorter movetime, disagreed and stamped a gem for
    // the same mainline ply. The deeper live rejection must win.
    const gemByNode = new Map<number, Detail | null>([[2, null]]);
    const gemByPly = new Map<number, Detail | null>([[2, GEM]]);

    // With the buggy `gemByNode.get(2) ?? gemByPly.get(2)` collapse this returns
    // GEM (`null ?? GEM === GEM`) — the exact wrong-badge bug CR-01 fixes.
    expect(resolveGemVerdict(gemByNode, gemByPly, 2, 2)).toBeNull();
  });

  it('falls back to the sweep ONLY when the live path has no entry for the node', () => {
    const gemByNode = new Map<number, Detail | null>();
    const gemByPly = new Map<number, Detail | null>([[2, GEM]]);
    expect(resolveGemVerdict(gemByNode, gemByPly, 2, 2)).toBe(GEM);
  });

  it('the live gem wins and carries its OWN detail (never the sweep copy) when both resolve a gem', () => {
    const liveGem: Detail = { maiaProbability: 0.02, elo: 2000, byOpponent: true };
    const gemByNode = new Map<number, Detail | null>([[2, liveGem]]);
    const gemByPly = new Map<number, Detail | null>([[2, GEM]]);
    expect(resolveGemVerdict(gemByNode, gemByPly, 2, 2)).toBe(liveGem);
  });

  it('returns null for an off-mainline node (ply < 0) with no live entry — the sweep is mainline-keyed only', () => {
    const gemByPly = new Map<number, Detail | null>([[2, GEM]]);
    expect(resolveGemVerdict(new Map<number, Detail | null>(), gemByPly, 99, -1)).toBeNull();
  });

  it('returns null when neither source has an answer', () => {
    expect(
      resolveGemVerdict(new Map<number, Detail | null>(), new Map<number, Detail | null>(), 2, 2),
    ).toBeNull();
  });
});
