/**
 * backup.ts unit tests — pure, deterministic (no engine/worker involved).
 *
 * Encodes the SC2 primary fixture from 153-RESEARCH.md ("Backup Rule: Worked
 * Fixture"): a non-root node with three children mixing one EXPANDED child
 * (its own backed-up expectation) and two UNEXPANDED children (parent-time
 * leaf estimates), proving `backupExpectation` is the Maia-prior-weighted
 * expectation over the FULL truncated set (D-02) and NOT:
 *   - a naive average (would ignore priors entirely), or
 *   - a visit-count-weighted average (the textbook-MCTS degeneration this
 *     phase's interface design (BackupChild) makes structurally impossible —
 *     Pitfall 1).
 *
 * Also covers the renormalization path, the totalPrior===0 degenerate guard,
 * and the root-vs-non-root branch (backupRootMax uses max, never the
 * expectation formula — D-01's "exactly one max node in the tree").
 */

import { describe, it, expect } from 'vitest';
import { backupExpectation, backupRootMax, type BackupChild } from '../backup';

describe('backupExpectation', () => {
  it('computes the Maia-prior-weighted expectation over a mixed expanded/unexpanded set (SC2 fixture)', () => {
    const children: BackupChild[] = [
      { prior: 0.6, value: 0.72 }, // EXPANDED — its own subtree's backed-up value
      { prior: 0.3, value: 0.55 }, // UNEXPANDED — parent-time leaf estimate
      { prior: 0.1, value: 0.4 }, // UNEXPANDED — parent-time leaf estimate
    ];

    const result = backupExpectation(children);

    expect(result).toBeCloseTo(0.637, 6);

    // Negative assertion #1: NOT the naive average (priors are actually used).
    const naiveAverage = (0.72 + 0.55 + 0.4) / 3;
    expect(naiveAverage).toBeCloseTo(0.5567, 4);
    expect(result).not.toBeCloseTo(naiveAverage, 2);

    // Negative assertion #2: NOT the visit-count-weighted collapse to child
    // A's value (the textbook-MCTS degeneration Pitfall 1 warns about — a
    // wide, shallow-visited node where only child A has visits > 0 would
    // wrongly collapse to just child A's value under a visit-weighted rule).
    expect(result).not.toBeCloseTo(0.72, 2);
  });

  it('renormalizes when priors do not sum to 1', () => {
    // Same relative weights as the primary fixture (0.6:0.3:0.1 scaled by
    // 0.5), unnormalized — must renormalize to the identical result.
    const children: BackupChild[] = [
      { prior: 0.3, value: 0.72 },
      { prior: 0.15, value: 0.55 },
      { prior: 0.05, value: 0.4 },
    ];

    const result = backupExpectation(children);

    expect(result).toBeCloseTo(0.637, 6);
  });

  it('returns 0.5 as the degenerate guard when totalPrior is 0', () => {
    const children: BackupChild[] = [
      { prior: 0, value: 0.9 },
      { prior: 0, value: 0.1 },
    ];

    expect(backupExpectation(children)).toBe(0.5);
  });

  it('returns 0.5 for an empty children array', () => {
    expect(backupExpectation([])).toBe(0.5);
  });
});

describe('backupRootMax', () => {
  it('returns the max value over root candidates (root-level companion fixture)', () => {
    const children: BackupChild[] = [
      { prior: 0.55, value: 0.6 }, // its own expanded subtree's backupExpectation
      { prior: 0.45, value: 0.66 }, // a not-yet-expanded root child's leaf estimate
    ];

    expect(backupRootMax(children)).toBeCloseTo(0.66, 6);
  });

  it('differs from backupExpectation over the same children — proving root uses max, not expectation', () => {
    const children: BackupChild[] = [
      { prior: 0.55, value: 0.6 },
      { prior: 0.45, value: 0.66 },
    ];

    const rootValue = backupRootMax(children);
    const expectationValue = backupExpectation(children);

    expect(rootValue).toBeCloseTo(0.66, 6);
    expect(expectationValue).not.toBeCloseTo(rootValue, 6);
  });

  it('returns 0.5 for an empty children array (never -Infinity from Math.max of nothing)', () => {
    expect(backupRootMax([])).toBe(0.5);
  });
});
