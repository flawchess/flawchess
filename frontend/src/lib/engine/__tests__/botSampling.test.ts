/**
 * botSampling.ts unit tests (Phase 166 D-04/D-06/D-11/D-12/D-13/D-14).
 *
 * Covers:
 * - mulberry32: same seed -> same [0,1) stream on repeated construction;
 *   10000-draw distribution sanity check against a two-move 50/50 policy
 *   lands within a few percent of 50/50 (RESEARCH A1).
 * - samplePolicy: UCI-ascending cumulative-distribution walk, deterministic
 *   under a fixed seed; degenerate `{}`/all-zero policies return `null`,
 *   never throw.
 * - sampleRankedLines: softmax over `practicalScore` (NOT array order),
 *   max-subtraction stability at a tiny tau, empty lines -> null; a fixture
 *   whose array order disagrees with practicalScore order still converges
 *   to the highest-practicalScore move at a very small tau.
 * - argmaxLine: scans practicalScore explicitly (array-order-disagrees
 *   fixture), UCI-ascending tie-break, empty lines -> null.
 * - fallbackMove: deterministic legal `.lan` move under a fixed seed on a
 *   normal FEN; throws a clear error naming the FEN on a terminal position.
 * - weightedPick (via samplePolicy): clamps against rng() returning exactly
 *   1, never yielding `undefined`.
 */

import { describe, it, expect } from 'vitest';
import type { RankedLine } from '../types';
import { mulberry32, samplePolicy, sampleRankedLines, argmaxLine, fallbackMove } from '../botSampling';

/** Builds a minimal RankedLine fixture — only rootMove/practicalScore vary per test. */
function makeLine(rootMove: string, practicalScore: number): RankedLine {
  return {
    rootMove,
    practicalScore,
    objectiveEvalCp: null,
    objectiveEvalMate: null,
    modalPath: [],
    modalStats: [],
    visits: 0,
  };
}

const CHECKMATE_FEN = 'rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3'; // fool's mate

// ─── mulberry32 ─────────────────────────────────────────────────────────────

describe('mulberry32', () => {
  it('produces the same stream on repeated construction from the same seed', () => {
    const rngA = mulberry32(42);
    const rngB = mulberry32(42);
    const streamA = Array.from({ length: 10 }, () => rngA());
    const streamB = Array.from({ length: 10 }, () => rngB());
    expect(streamA).toEqual(streamB);
  });

  it('yields values in [0,1)', () => {
    const rng = mulberry32(1);
    for (let i = 0; i < 1000; i++) {
      const v = rng();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });

  it('samples ~50/50 over 10000 draws from a two-move 50/50 policy (RESEARCH A1)', () => {
    const rng = mulberry32(7);
    const policy = { a1a2: 0.5, b1b2: 0.5 };
    let countA = 0;
    const draws = 10000;
    for (let i = 0; i < draws; i++) {
      const picked = samplePolicy(policy, rng);
      if (picked === 'a1a2') countA++;
    }
    const fractionA = countA / draws;
    expect(fractionA).toBeGreaterThan(0.47);
    expect(fractionA).toBeLessThan(0.53);
  });
});

// ─── samplePolicy ───────────────────────────────────────────────────────────

describe('samplePolicy', () => {
  it('returns a deterministic move under a fixed seed', () => {
    const policy = { e2e4: 0.7, d2d4: 0.3 };
    const pickedA = samplePolicy(policy, mulberry32(123));
    const pickedB = samplePolicy(policy, mulberry32(123));
    expect(pickedA).toBe(pickedB);
    expect(['e2e4', 'd2d4']).toContain(pickedA);
  });

  it('returns null for an empty policy (degenerate, D-13) — never throws', () => {
    expect(samplePolicy({}, mulberry32(1))).toBeNull();
  });

  it('returns null for an all-zero-weight policy (degenerate, D-13) — never throws', () => {
    expect(samplePolicy({ a1a2: 0, b1b2: 0 }, mulberry32(1))).toBeNull();
  });

  it('returns null for an all-NaN policy (degenerate, D-13) — never silently picks a move', () => {
    // Regression (WR-01): `total <= 0` is false for NaN, so an all-NaN policy
    // used to fall through to the exhausted-loop clamp and return 'b1b2'.
    expect(samplePolicy({ a1a2: NaN, b1b2: NaN }, mulberry32(1))).toBeNull();
  });

  it('returns null when a single NaN weight poisons an otherwise-valid policy', () => {
    // One NaN entry makes the whole cumulative walk unreliable — must signal
    // fallback rather than deterministically returning the last sorted UCI.
    expect(samplePolicy({ a1a2: 0.5, b1b2: NaN }, () => 0.01)).toBeNull();
  });

  it('returns null for an Infinity-total policy (degenerate, D-13)', () => {
    expect(samplePolicy({ a1a2: Infinity, b1b2: Infinity }, mulberry32(1))).toBeNull();
  });

  it('clamps against rng() returning exactly 1, never yielding undefined', () => {
    const alwaysOne = () => 1;
    const picked = samplePolicy({ a1a2: 0.5, b1b2: 0.5 }, alwaysOne);
    expect(picked).toBe('b1b2'); // last in UCI-ascending order
  });

  it('picks via a UCI-ascending cumulative walk regardless of Record key order', () => {
    // draw = 0.9 * total; with UCI-ascending order [b1b2(0.2), e2e4(0.7),
    // z9z9-nonsense... ] -- keep it simple with two entries summing to 1.
    const policy = { e2e4: 0.7, b1b2: 0.3 };
    const rng = () => 0.75; // draw = 0.75 * 1.0 = 0.75; cumulative: b1b2=0.3, e2e4=1.0 -> picks e2e4
    expect(samplePolicy(policy, rng)).toBe('e2e4');
  });
});

// ─── sampleRankedLines ──────────────────────────────────────────────────────

describe('sampleRankedLines', () => {
  it('returns null for an empty lines array', () => {
    expect(sampleRankedLines([], 0.1, mulberry32(1))).toBeNull();
  });

  it('softmax-samples over practicalScore, not array order, and is deterministic under a fixed seed', () => {
    const lines = [makeLine('a1a2', 0.9), makeLine('b1b2', 0.1)];
    const pickedA = sampleRankedLines(lines, 0.1, mulberry32(5));
    const pickedB = sampleRankedLines(lines, 0.1, mulberry32(5));
    expect(pickedA).toBe(pickedB);
  });

  it('converges to the highest-practicalScore move at very small tau even when array order disagrees (Pitfall 1)', () => {
    // Deliberately NOT sorted by practicalScore: index 0 has the LOWEST
    // score, index 2 (last) has the HIGHEST. If this helper trusted array
    // order or rankScore-style ordering it would favor 'a1a2' or 'b1b2'.
    const lines = [makeLine('a1a2', 0.1), makeLine('b1b2', 0.4), makeLine('c1c2', 0.99)];
    // At a tiny tau the softmax collapses almost all mass onto the true max.
    const picked = sampleRankedLines(lines, 0.001, mulberry32(9));
    expect(picked).toBe('c1c2');
  });

  it('never produces NaN/overflow at a very small tau (max-subtraction stability)', () => {
    const lines = [makeLine('a1a2', 0.99), makeLine('b1b2', 1.0)];
    const picked = sampleRankedLines(lines, 1e-6, mulberry32(3));
    expect(picked).not.toBeNull();
    expect(['a1a2', 'b1b2']).toContain(picked);
  });

  it('returns the argmax at tau = 0 (the softmax limit), never the worst move (WR-03)', () => {
    // Regression: tau = 0 used to yield exp(NaN) on the max line and ride
    // the NaN hole to the alphabetically-last (here worst) move 'z1z2'.
    const lines = [makeLine('a1a2', 0.99), makeLine('z1z2', 0.01)];
    expect(sampleRankedLines(lines, 0, mulberry32(1))).toBe('a1a2');
  });

  it('returns the argmax at negative tau instead of inverting the softmax (WR-03)', () => {
    // A negative tau flips the exponent sign, concentrating mass on the
    // LOWEST practicalScore — clamp to the argmax limit instead.
    const lines = [makeLine('a1a2', 0.99), makeLine('b1b2', 0.01)];
    expect(sampleRankedLines(lines, -0.05, mulberry32(1))).toBe('a1a2');
  });
});

// ─── argmaxLine ─────────────────────────────────────────────────────────────

describe('argmaxLine', () => {
  it('returns null for an empty lines array', () => {
    expect(argmaxLine([])).toBeNull();
  });

  it('scans for the true max practicalScore, ignoring array order (Pitfall 1/D-06)', () => {
    // Index 0 is NOT the highest-practicalScore line (array is "rankScore"-
    // ordered in spirit, e.g. by findability) — argmaxLine must not trust it.
    const lines = [makeLine('a1a2', 0.3), makeLine('c1c2', 0.95), makeLine('b1b2', 0.6)];
    expect(argmaxLine(lines)).toBe('c1c2');
  });

  it('breaks ties by ascending UCI string', () => {
    const lines = [makeLine('e2e4', 0.5), makeLine('d2d4', 0.5)];
    expect(argmaxLine(lines)).toBe('d2d4');
  });

  it('never latches a NaN practicalScore as best (WR-02)', () => {
    // Regression: a first-scanned NaN line used to become `best` via the
    // `best === null` arm and was then unbeatable (all NaN comparisons are
    // false) — the true max must win instead.
    const lines = [makeLine('a1a2', NaN), makeLine('b1b2', 0.9)];
    expect(argmaxLine(lines)).toBe('b1b2');
  });

  it('returns null when every practicalScore is non-finite (degenerate, D-13)', () => {
    const lines = [makeLine('a1a2', NaN), makeLine('b1b2', Infinity)];
    expect(argmaxLine(lines)).toBeNull();
  });
});

// ─── fallbackMove ───────────────────────────────────────────────────────────

describe('fallbackMove', () => {
  it('returns a legal .lan move, deterministic under a fixed seed, on a normal FEN', () => {
    const fen = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'; // 6 legal moves
    const movedA = fallbackMove(fen, mulberry32(2));
    const movedB = fallbackMove(fen, mulberry32(2));
    expect(movedA).toBe(movedB);
    expect(movedA).toMatch(/^[a-h][1-8][a-h][1-8][qrbn]?$/);
  });

  it('throws a clear error naming the FEN on a terminal (checkmate) position', () => {
    expect(() => fallbackMove(CHECKMATE_FEN, mulberry32(1))).toThrow(/no legal moves/);
    expect(() => fallbackMove(CHECKMATE_FEN, mulberry32(1))).toThrow(CHECKMATE_FEN);
  });
});
