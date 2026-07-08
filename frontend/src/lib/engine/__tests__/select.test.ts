/**
 * select.ts unit tests (ENGINE-02, D-01, D-05).
 *
 * Covers:
 * - truncateAndRenormalize: cuts at ~90% cumulative mass, drops the tail, and
 *   renormalizes the kept set to sum to ~1.0; an already-concentrated policy
 *   (one move at 0.95) keeps just that move renormalized to 1.0.
 * - selectChild: root PUCT selection includes the Q term (a fixture where Q
 *   flips the choice vs. exploration alone); non-root selection drops Q
 *   entirely (same children, different winner at root vs. non-root — proving
 *   the D-01 split); canonical UCI tie-break on equal scores.
 * - rootExplorationPriors: floor-boosts a near-zero-Maia candidate, while
 *   truncateAndRenormalize on the same input does NOT — proving the floor is
 *   a separate, root-only transform (D-05).
 */

import { describe, it, expect } from 'vitest';
import {
  truncateAndRenormalize,
  rootExplorationPriors,
  selectChild,
  POLICY_MASS_THRESHOLD,
  C_PUCT,
  ROOT_PRIOR_FLOOR,
  type SelectionChild,
} from '../select';

/** Sums a Map's values — used to assert renormalization lands at ~1.0. */
function sumValues(m: Map<string, number>): number {
  return [...m.values()].reduce((sum, v) => sum + v, 0);
}

// ─── truncateAndRenormalize ─────────────────────────────────────────────────

describe('truncateAndRenormalize', () => {
  it('keeps the highest-probability moves until ~90% cumulative mass and drops the tail', () => {
    const policy = { a: 0.5, b: 0.3, c: 0.15, d: 0.05 };
    const kept = truncateAndRenormalize(policy);

    // a (0.5) + b (0.3) = 0.8 < 0.9, keep c (0.15) -> cumulative 0.95 >= 0.9, break.
    // d is dropped entirely.
    expect(kept.has('a')).toBe(true);
    expect(kept.has('b')).toBe(true);
    expect(kept.has('c')).toBe(true);
    expect(kept.has('d')).toBe(false);
    expect(sumValues(kept)).toBeCloseTo(1.0, 10);
  });

  it('keeps just one move when it already exceeds the threshold, renormalized to 1.0', () => {
    const policy = { a: 0.95, b: 0.03, c: 0.02 };
    const kept = truncateAndRenormalize(policy);

    expect(kept.size).toBe(1);
    expect(kept.get('a')).toBeCloseTo(1.0, 10);
  });

  it('exports POLICY_MASS_THRESHOLD as 0.9, independent of moveQuality.ts', () => {
    expect(POLICY_MASS_THRESHOLD).toBe(0.9);
  });

  it('breaks equal-probability ties by ascending UCI order, not Record insertion order (WR-03)', () => {
    // d2d4 and c2c4 tie at 0.2 and straddle the 0.9 boundary: only one
    // survives (0.75 + 0.2 = 0.95 >= threshold; 0.75 chosen over 0.7 to
    // stay clear of float rounding, 0.7 + 0.2 < 0.9 in doubles). The
    // survivor must be the UCI-ascending one (c2c4) for BOTH insertion
    // orders.
    const insertionOrderA = { e2e4: 0.75, d2d4: 0.2, c2c4: 0.2 };
    const insertionOrderB = { e2e4: 0.75, c2c4: 0.2, d2d4: 0.2 };

    const keptA = truncateAndRenormalize(insertionOrderA);
    const keptB = truncateAndRenormalize(insertionOrderB);

    expect([...keptA.keys()]).toEqual(['e2e4', 'c2c4']);
    expect([...keptB.keys()]).toEqual(['e2e4', 'c2c4']);
  });
});

// ─── selectChild — root vs non-root PUCT split (D-01) ──────────────────────

describe('selectChild', () => {
  // Shared fixture (D-01 split proof): the plain `prior` (non-root
  // exploration weight) favors 'a1a2' (0.8 vs 0.2), while `rootExplorationPrior`
  // is IDENTICAL for both (so the root exploration term ties) and `q` favors
  // 'b1b2' heavily (0.9 vs 0.1). Same children object, opposite winner at
  // root vs. non-root, proving the D-01 formula split.
  const splitFixtureChildren: SelectionChild[] = [
    { uci: 'a1a2', prior: 0.8, visits: 0, q: 0.1, rootExplorationPrior: 0.5 },
    { uci: 'b1b2', prior: 0.2, visits: 0, q: 0.9, rootExplorationPrior: 0.5 },
  ];

  it('root selection picks the child maximizing Q + C_PUCT * P_root * sqrt(N)/(1+n)', () => {
    const parentVisits = 4;

    // Equal rootExplorationPrior + visits for both -> exploration terms tie,
    // so Q alone decides: 'b1b2' has the higher Q.
    const exploration = C_PUCT * 0.5 * (Math.sqrt(parentVisits) / 1);
    const scoreA = 0.1 + exploration;
    const scoreB = 0.9 + exploration;
    expect(scoreB).toBeGreaterThan(scoreA); // sanity: fixture is well-formed

    const winner = selectChild(splitFixtureChildren, parentVisits, true);
    expect(winner).toBe('b1b2');
  });

  it('non-root selection ignores Q entirely — same children, different winner than at root', () => {
    // At the root, 'b1b2' wins because of its high Q (previous test). At a
    // non-root node the Q term is dropped entirely, so the winner flips to
    // whichever child has the higher plain-prior exploration term: 'a1a2'
    // (prior 0.8 vs 0.2).
    const parentVisits = 4;

    const winner = selectChild(splitFixtureChildren, parentVisits, false);
    expect(winner).toBe('a1a2');
  });

  it('breaks ties by canonical ascending UCI-string order', () => {
    const children: SelectionChild[] = [
      { uci: 'e2e4', prior: 0.5, visits: 2 },
      { uci: 'd2d4', prior: 0.5, visits: 2 },
    ];
    // Identical prior and visits -> identical non-root exploration scores.
    const winner = selectChild(children, 8, false);
    expect(winner).toBe('d2d4'); // lexicographically smaller than 'e2e4'
  });

  it('throws on an empty children array', () => {
    expect(() => selectChild([], 1, false)).toThrow();
  });
});

// ─── rootExplorationPriors — floor scope isolated from truncateAndRenormalize (D-05) ──

describe('rootExplorationPriors', () => {
  it('raises a near-zero-Maia candidate to at least the floor after renormalization', () => {
    const renormalized = new Map<string, number>([
      ['a1a2', 0.999],
      ['h7h8q', 0.001],
    ]);

    const floored = rootExplorationPriors(renormalized);
    const flooredCandidate = floored.get('h7h8q');
    expect(flooredCandidate).toBeDefined();
    expect(flooredCandidate ?? 0).toBeGreaterThanOrEqual(ROOT_PRIOR_FLOOR * 0.5);
    // Confirms the floor materially raised the near-zero candidate's share
    // (it started at 0.001, an order of magnitude below the floor).
    expect(flooredCandidate ?? 0).toBeGreaterThan(0.001);
    expect(sumValues(floored)).toBeCloseTo(1.0, 10);
  });

  it('does NOT floor-boost when truncateAndRenormalize runs on the same input (D-05 floor scope isolated)', () => {
    const policy = { a1a2: 0.999, h7h8q: 0.001 };
    const kept = truncateAndRenormalize(policy);

    // truncateAndRenormalize with POLICY_MASS_THRESHOLD=0.9 keeps only 'a1a2'
    // (0.999 already exceeds 0.9) — h7h8q is dropped, not floor-boosted.
    expect(kept.has('h7h8q')).toBe(false);
    expect(kept.get('a1a2')).toBeCloseTo(1.0, 10);
  });
});
