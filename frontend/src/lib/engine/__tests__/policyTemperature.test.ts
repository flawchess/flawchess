/**
 * policyTemperature.ts unit tests (Phase 159 D-06/D-07).
 *
 * Covers:
 * - Direction: T>1 flattens (reduces the top move's share, raises the tail's
 *   share); T<1 sharpens (raises the top move's share).
 * - T=1 identity: applying the transform at the default temperature leaves
 *   the RAW probability values unchanged (the runtime no-op is a caller-side
 *   short-circuit, per Pitfall 1 — this test proves the underlying math is
 *   ALSO a true identity at T=1, independent of that short-circuit).
 * - Renormalization: output always sums to 1 (within floating-point
 *   tolerance) for any positive-mass input, at any temperature.
 * - Empty-input guard: an empty policy returns an empty result; a
 *   zero-mass-only input (impossible via real Maia output, but a defensive
 *   guard per the module's degenerate-input convention) returns all zeros.
 */

import { describe, it, expect } from 'vitest';
import {
  DEFAULT_POLICY_TEMPERATURE,
  ROOT_CANDIDATE_HARD_CAP,
  applyPolicyTemperature,
} from '../policyTemperature';

const PEAKED_POLICY: Record<string, number> = {
  e2e4: 0.7,
  e2e3: 0.2,
  d2d4: 0.1,
};

function sum(policy: Record<string, number>): number {
  return Object.values(policy).reduce((a, b) => a + b, 0);
}

describe('DEFAULT_POLICY_TEMPERATURE', () => {
  it('is exactly 1 (strict equality — Pitfall 7)', () => {
    expect(DEFAULT_POLICY_TEMPERATURE).toBe(1);
  });
});

describe('applyPolicyTemperature — direction', () => {
  it('T>1 flattens: reduces the top move share and raises a tail move share', () => {
    const flattened = applyPolicyTemperature(PEAKED_POLICY, 2);
    expect(flattened.e2e4).toBeDefined();
    expect(flattened.d2d4).toBeDefined();
    expect(flattened.e2e4!).toBeLessThan(PEAKED_POLICY.e2e4!);
    expect(flattened.d2d4!).toBeGreaterThan(PEAKED_POLICY.d2d4!);
  });

  it('T<1 sharpens: raises the top move share and reduces a tail move share', () => {
    const sharpened = applyPolicyTemperature(PEAKED_POLICY, 0.5);
    expect(sharpened.e2e4).toBeDefined();
    expect(sharpened.d2d4).toBeDefined();
    expect(sharpened.e2e4!).toBeGreaterThan(PEAKED_POLICY.e2e4!);
    expect(sharpened.d2d4!).toBeLessThan(PEAKED_POLICY.d2d4!);
  });

  it('T=1 is a true identity on the raw probability values', () => {
    const identity = applyPolicyTemperature(PEAKED_POLICY, DEFAULT_POLICY_TEMPERATURE);
    for (const [uci, p] of Object.entries(PEAKED_POLICY)) {
      expect(identity[uci]).toBeCloseTo(p, 10);
    }
  });
});

describe('applyPolicyTemperature — renormalization', () => {
  it('sums to 1 (within fp tolerance) at T>1, T=1, and T<1', () => {
    for (const t of [0.5, 1, 1.5, 2]) {
      expect(sum(applyPolicyTemperature(PEAKED_POLICY, t))).toBeCloseTo(1, 10);
    }
  });
});

describe('applyPolicyTemperature — empty-input guard', () => {
  it('returns an empty result for an empty policy', () => {
    expect(applyPolicyTemperature({}, 2)).toEqual({});
  });

  it('returns all-zeros for a zero-mass-only input (degenerate guard)', () => {
    const zeroMass = { a: 0, b: 0 };
    const result = applyPolicyTemperature(zeroMass, 2);
    expect(result.a).toBe(0);
    expect(result.b).toBe(0);
  });
});

describe('ROOT_CANDIDATE_HARD_CAP', () => {
  it('is a positive integer', () => {
    expect(Number.isInteger(ROOT_CANDIDATE_HARD_CAP)).toBe(true);
    expect(ROOT_CANDIDATE_HARD_CAP).toBeGreaterThan(0);
  });
});
