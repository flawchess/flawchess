/**
 * openingBook.ts unit tests (Phase 169.5, PLAY-11 — SC2/SC3/SC4).
 *
 * Pure unit tests — no mocks, no providers, no `chess.js` Worker anything.
 * `legalMoves` fixtures are either plain `{san, lan}` literals or the real
 * `chess.js` `.moves({ verbose: true })` output; `prefixSet` fixtures are
 * small hand-written `Set<string>` literals (the real 3,641-line corpus is
 * covered by plan 01's `openings.test.ts` — not re-read here).
 *
 * Covers:
 * - `getBookCandidates`: prefix-filtered legal moves, start position + a
 *   mid-history case.
 * - `exit`: the ply cap (`>=` boundary), the RAW-policy floor (Pitfall 3
 *   guard — the case a post-renormalization floor check cannot catch), and
 *   empty candidates.
 * - `variety` (SC3, non-inferable #2): 400 seeded `mulberry32` draws whose
 *   empirical frequency TRACKS the stubbed policy weights, not just "≥2
 *   distinct moves" (a uniform-over-candidates bug would also pass that
 *   weaker check).
 * - `weighting seam` (D-06): a custom `BookWeightingFn` is load-bearing on
 *   the SAMPLE, but never bypasses the RAW-policy exit rule.
 */

import { describe, it, expect } from 'vitest';
import { Chess } from 'chess.js';
import {
  BOOK_POLICY_FLOOR,
  BOOK_PLY_CAP,
  getBookCandidates,
  selectBookMove,
  type BookCandidate,
  type BookWeightingFn,
} from '../openingBook';
import { mulberry32 } from '../botSampling';
import { styleBookWeighting } from '../botStyle';

// ─── getBookCandidates ──────────────────────────────────────────────────────

describe('getBookCandidates', () => {
  it('returns exactly the prefix-matching legal moves from the start position', () => {
    const legalMoves = new Chess().moves({ verbose: true });
    expect(legalMoves).toHaveLength(20); // sanity: all 20 start-position legal moves considered

    const prefixSet = new Set(['e4', 'd4']);
    const candidates = getBookCandidates([], legalMoves, prefixSet);

    const byUci = [...candidates].sort((a, b) => (a.uci < b.uci ? -1 : 1));
    expect(byUci).toEqual([
      { uci: 'd2d4', san: 'd4' },
      { uci: 'e2e4', san: 'e4' },
    ]);
  });

  it('filters against the joined move-history-plus-candidate key at mid-history', () => {
    const chess = new Chess();
    chess.move('e4');
    chess.move('c6');
    const legalMoves = chess.moves({ verbose: true });

    const prefixSet = new Set(['e4 c6 d4']);
    const candidates = getBookCandidates(['e4', 'c6'], legalMoves, prefixSet);

    expect(candidates).toEqual<BookCandidate[]>([{ uci: 'd2d4', san: 'd4' }]);
  });
});

// ─── exit rule ───────────────────────────────────────────────────────────

describe('exit', () => {
  it('returns null once moveHistorySan.length reaches BOOK_PLY_CAP, even with a matching prefix', () => {
    const historyAtCap = Array.from({ length: BOOK_PLY_CAP }, () => 'x');
    const legalMoves = [{ san: 'e4', lan: 'e2e4' }];
    // A prefix set that WOULD match if the cap check didn't fire first.
    const prefixSet = new Set([[...historyAtCap, 'e4'].join(' ')]);
    const rawPolicy = { e2e4: 0.5 }; // clears the floor — cap is the only reason for null

    expect(selectBookMove(historyAtCap, legalMoves, prefixSet, rawPolicy, mulberry32(1))).toBeNull();
  });

  it('still returns a move at BOOK_PLY_CAP - 1 plies with the same shape (proves the boundary is >=, not always-null)', () => {
    const historyBelowCap = Array.from({ length: BOOK_PLY_CAP - 1 }, () => 'x');
    const legalMoves = [{ san: 'e4', lan: 'e2e4' }];
    const prefixSet = new Set([[...historyBelowCap, 'e4'].join(' ')]);
    const rawPolicy = { e2e4: 0.5 };

    expect(selectBookMove(historyBelowCap, legalMoves, prefixSet, rawPolicy, mulberry32(1))).toBe(
      'e2e4',
    );
  });

  it('returns null when the single book candidate is below BOOK_POLICY_FLOOR on the RAW policy (Pitfall 3 guard)', () => {
    // Exactly ONE book candidate (e2e4), below the floor. A second, non-book
    // legal move (d2d4) carries the remaining raw-policy mass, so an
    // implementation that mistakenly checks the floor against the
    // *renormalized* subset (where e2e4 would be the sole candidate at a
    // renormalized share of 1.0) would wrongly return e2e4 here. This test
    // is what makes that bug red — it must read `rawPolicy` directly.
    const legalMoves = [
      { san: 'e4', lan: 'e2e4' },
      { san: 'd4', lan: 'd2d4' },
    ];
    const prefixSet = new Set(['e4']); // only e4 is a book move
    const rawPolicy = { e2e4: 0.01, d2d4: 0.99 };

    expect(selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(1))).toBeNull();
  });

  it('returns the candidate when the single book candidate clears the floor', () => {
    const legalMoves = [
      { san: 'e4', lan: 'e2e4' },
      { san: 'd4', lan: 'd2d4' },
    ];
    const prefixSet = new Set(['e4']);
    const rawPolicy = { e2e4: 0.3, d2d4: 0.7 };

    expect(selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(1))).toBe('e2e4');
  });

  it('returns null when no legal move matches any book prefix', () => {
    const legalMoves = [{ san: 'e4', lan: 'e2e4' }];
    const prefixSet = new Set(['d4']); // does not match 'e4'
    const rawPolicy = { e2e4: 1 };

    expect(selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(1))).toBeNull();
  });
});

// ─── variety (SC3) ───────────────────────────────────────────────────────

describe('variety', () => {
  // Deliberately UNEQUAL stubbed weights (mirrors the plan's own example).
  const WEIGHTS: Record<string, number> = { e2e4: 0.5, d2d4: 0.3, c2c4: 0.15, b1a3: 0.05 };
  const SAN_BY_UCI: Record<string, string> = { e2e4: 'e4', d2d4: 'd4', c2c4: 'c4', b1a3: 'Na3' };
  const SAMPLE_DRAWS = 400;
  const FREQUENCY_TOLERANCE = 0.08;
  const MIN_DISTINCT_MOVES = 2;

  it('tracks the stubbed policy weights, not a uniform spray over candidates', () => {
    const legalMoves = new Chess().moves({ verbose: true });
    const prefixSet = new Set(Object.values(SAN_BY_UCI));
    const candidates = getBookCandidates([], legalMoves, prefixSet);
    expect(candidates).toHaveLength(4); // sanity: exactly the 4 stubbed UCIs are in book

    const tally: Record<string, number> = {};
    for (let seed = 0; seed < SAMPLE_DRAWS; seed++) {
      const move = selectBookMove([], legalMoves, prefixSet, WEIGHTS, mulberry32(seed));
      if (move) tally[move] = (tally[move] ?? 0) + 1;
    }

    // (1) rules out an argmax/deterministic regression.
    expect(Object.keys(tally).length).toBeGreaterThanOrEqual(MIN_DISTINCT_MOVES);

    // (2) the modal move is the highest-weight candidate.
    const modalMove = Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0];
    expect(modalMove).toBe('e2e4');

    // (3) THE POINT OF THIS TEST: each candidate's empirical frequency
    // tracks its stubbed weight within a tolerance band. Replacing the
    // `samplePolicy(weighting(...))` call with a uniform pick over
    // `candidates` still passes (1) and possibly (2), but drives every
    // frequency toward 0.25 and makes this assertion RED — do not weaken
    // it to a "≥2 distinct moves" smoke check.
    for (const [uci, weight] of Object.entries(WEIGHTS)) {
      const frequency = (tally[uci] ?? 0) / SAMPLE_DRAWS;
      const lowerBound = Math.max(0, weight - FREQUENCY_TOLERANCE);
      const upperBound = weight + FREQUENCY_TOLERANCE;
      expect(frequency, `${uci} frequency ${frequency} outside [${lowerBound}, ${upperBound}]`).toBeGreaterThanOrEqual(
        lowerBound,
      );
      expect(frequency, `${uci} frequency ${frequency} outside [${lowerBound}, ${upperBound}]`).toBeLessThanOrEqual(
        upperBound,
      );
    }
  });
});

// ─── weighting seam (D-06) ───────────────────────────────────────────────

describe('weighting seam', () => {
  it('a custom BookWeightingFn is load-bearing on the sample', () => {
    const legalMoves = new Chess().moves({ verbose: true });
    const prefixSet = new Set(['e4', 'd4', 'c4', 'Na3']);
    // Deterministically picks d2d4 no matter what the raw policy says.
    const onlyD2d4: BookWeightingFn = (candidates) => {
      const restricted: Record<string, number> = {};
      for (const c of candidates) restricted[c.uci] = c.uci === 'd2d4' ? 1 : 0;
      return restricted;
    };
    // Only e2e4 clears the floor — the exit rule still lets this position
    // through, but the seam decides which candidate is actually sampled.
    const rawPolicy = { e2e4: 0.5, d2d4: 0.01, c2c4: 0.01, b1a3: 0.01 };

    for (const seed of [1, 2, 3, 4, 5]) {
      const move = selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(seed), onlyD2d4);
      expect(move).toBe('d2d4');
    }
  });

  it('does not bypass the RAW-policy exit rule even when the custom weighting would happily pick a candidate', () => {
    const legalMoves = new Chess().moves({ verbose: true });
    const prefixSet = new Set(['e4', 'd4', 'c4', 'Na3']);
    const onlyD2d4: BookWeightingFn = (candidates) => {
      const restricted: Record<string, number> = {};
      for (const c of candidates) restricted[c.uci] = c.uci === 'd2d4' ? 1 : 0;
      return restricted;
    };
    // NO candidate clears BOOK_POLICY_FLOOR on the raw policy.
    const rawPolicy = { e2e4: 0.01, d2d4: 0.01, c2c4: 0.01, b1a3: 0.01 };
    expect(Math.max(...Object.values(rawPolicy))).toBeLessThan(BOOK_POLICY_FLOOR);

    const move = selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(1), onlyD2d4);
    expect(move).toBeNull();
  });
});

// ─── styled weighting: floor-check-before-weighting regression (Phase 182, Pitfall 1) ─

describe('styled weighting (Phase 182, STYLE-01) — floor check still runs before weighting', () => {
  it('a real styleBookWeighting boost does NOT rescue a sole candidate whose RAW policy is below BOOK_POLICY_FLOOR', () => {
    const legalMoves = [
      { san: 'e4', lan: 'e2e4' },
      { san: 'd4', lan: 'd2d4' },
    ];
    const prefixSet = new Set(['e4']); // only e4 is a book move
    const rawPolicy = { e2e4: 0.01, d2d4: 0.99 }; // e2e4's RAW policy is below the floor
    expect(rawPolicy.e2e4).toBeLessThan(BOOK_POLICY_FLOOR);

    // A heavy real boost on the sole candidate's style line — if the floor
    // check ever read weighting()'s output instead of rawPolicy, this boost
    // would make e2e4 look plausible (0.01 * 50 = 0.5) and wrongly survive.
    const styledWeighting = styleBookWeighting(new Set(['e4']), [], 50);

    const move = selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(1), styledWeighting);
    expect(move).toBeNull();
  });

  it('a boosted candidate that clears the RAW floor is still selected via the styled weighting', () => {
    const legalMoves = [
      { san: 'e4', lan: 'e2e4' },
      { san: 'd4', lan: 'd2d4' },
    ];
    const prefixSet = new Set(['e4', 'd4']);
    const rawPolicy = { e2e4: 0.05, d2d4: 0.05 }; // both clear BOOK_POLICY_FLOOR, equal raw share
    const styledWeighting = styleBookWeighting(new Set(['d4']), [], 1000); // only d4 is styled, heavily

    for (const seed of [1, 2, 3, 4, 5]) {
      const move = selectBookMove([], legalMoves, prefixSet, rawPolicy, mulberry32(seed), styledWeighting);
      expect(move).toBe('d2d4'); // heavily boosted candidate dominates the sample
    }
  });
});
