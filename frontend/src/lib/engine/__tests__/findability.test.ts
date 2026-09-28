/**
 * findability.ts unit tests (Phase 159 D-01/D-02/D-03; Phase 225
 * D-10a/D-10b/D-10c, SEED-170 item 3).
 *
 * Covers:
 * - pRefForElo: monotonically non-increasing across the 600-2600 domain,
 *   clamps to the first/last anchor outside that range. Unchanged by Phase
 *   225 (D-10e — item 3 never touches the findability curve).
 * - rankScore (4-argument, D-10a): exact saturation at pYou >= pRef (factor
 *   1, strict equality), the pRef<=0 degenerate guard, the fallback-0
 *   reduction to the pre-Phase-225 formula, and the grid bounds invariant
 *   `min(value, fallback) <= rankScore <= value`.
 * - The D-10c clamp: a low-prior move already below V_fallback is never
 *   promoted — it sorts by its own V regardless of `f`.
 * - rankFallbackValue: normalizes by total prior (a weighted MEAN, not the
 *   raw weighted sum), and returns 0 (not backupExpectation's own 0.5
 *   default) for an all-zero-prior or empty input (D-10b amended).
 * - The two D-03 regression cases, restated for D-10a with V_fallback
 *   pinned by a rule stated BEFORE running (Pitfall 5): a 9%-prior mid-V
 *   move (Qxf2 @600) still beats both a 5%-prior high-V move (Nb5) and a
 *   57%-prior low-V Mistake (Rxf2); an in-chart candidate (@1000) still
 *   beats a ~5%-prior tail move at a V gap where findability wins (0.58 vs
 *   0.60 — narrower than Phase 159's original 0.55 vs 0.60 gap, which flips
 *   under D-10a for any V_fallback above ~0.467 and is the accepted Phase
 *   159 showcase reversal, D-10e; covered instead by the rewritten
 *   mctsSearch/fallbackExpectimax "Phase 159 D-01 findability ranking"
 *   describes).
 *
 * Fixture prior/value pairs approximate the real observed relationships from
 * live 600/1000-ELO analyses (159-CONTEXT.md D-03) — the real FENs were not
 * recovered this session (159-RESEARCH.md Open Question 1); an end-to-end
 * live check against the real positions is deferred to the phase-close UAT
 * checkpoint (159-04's verification).
 */

import { describe, it, expect } from 'vitest';
import { P_REF_ANCHORS, pRefForElo, rankFallbackValue, rankScore } from '../findability';
import type { BackupChild } from '../backup';

/**
 * D-10a/Pitfall 5 pinned rule: prior mass NOT attributed to any named
 * candidate in a fixture is valued NEUTRALLY at this constant, stated here
 * BEFORE any test result is computed — so V_fallback in every D-03 fixture
 * below is never chosen after seeing whether a case passes or fails.
 */
const UNLISTED_PRIOR_VALUE = 0.5;

// ─── pRefForElo (Phase 159, unchanged by Phase 225 D-10e) ──────────────────

describe('pRefForElo', () => {
  it('is monotonically non-increasing across the ELO domain', () => {
    expect(pRefForElo(600)).toBeGreaterThan(pRefForElo(1400));
    expect(pRefForElo(1400)).toBeGreaterThan(pRefForElo(2600));
  });

  it('clamps to the first anchor value below the domain', () => {
    expect(pRefForElo(400)).toBe(pRefForElo(600));
  });

  it('clamps to the last anchor value above the domain', () => {
    expect(pRefForElo(3000)).toBe(pRefForElo(2600));
  });

  it('interpolates linearly between adjacent anchors', () => {
    const first = P_REF_ANCHORS[0];
    const second = P_REF_ANCHORS[1];
    expect(first).toBeDefined();
    expect(second).toBeDefined();
    const [eloLo, pRefLo] = first!;
    const [eloHi, pRefHi] = second!;
    const midElo = (eloLo + eloHi) / 2;
    const expectedMid = (pRefLo + pRefHi) / 2;
    expect(pRefForElo(midElo)).toBeCloseTo(expectedMid, 10);
  });
});

// ─── rankScore (Phase 225 D-10a: 4-argument, blends toward fallback) ───────

describe('rankScore', () => {
  const PREF = 0.12;
  const PYOU_GRID = [0, 0.01, 0.06, 0.12, 0.5];
  const VALUE_GRID = [0.1, 0.5, 0.9];
  const FALLBACK_GRID = [0, 0.3, 0.7];

  it('stays within [min(value, fallback), value] for every combination in the grid (D-10a invariant)', () => {
    for (const pYou of PYOU_GRID) {
      for (const value of VALUE_GRID) {
        for (const fallback of FALLBACK_GRID) {
          const score = rankScore(pYou, PREF, value, fallback);
          expect(score).toBeLessThanOrEqual(value);
          expect(score).toBeGreaterThanOrEqual(Math.min(value, fallback));
        }
      }
    }
  });

  it('returns exactly value (strict equality) when pYou >= pRef — saturation at factor 1, for any fallback', () => {
    for (const value of VALUE_GRID) {
      for (const fallback of FALLBACK_GRID) {
        expect(rankScore(PREF, PREF, value, fallback)).toBe(value); // equality boundary also saturates
        expect(rankScore(0.5, PREF, value, fallback)).toBe(value);
      }
    }
  });

  it('returns value unmodified when pRef <= 0, regardless of fallback (degenerate guard)', () => {
    expect(rankScore(0.05, 0, 0.6, 0.9)).toBe(0.6);
    expect(rankScore(0.05, -1, 0.6, 0.9)).toBe(0.6);
  });

  it('reduces to (pYou/pRef) * value when fallback is 0 — the pre-Phase-225 formula (D-10b)', () => {
    expect(rankScore(0.06, 0.12, 0.8, 0)).toBeCloseTo((0.06 / 0.12) * 0.8, 10);
  });

  it('D-10c: clamps a low-prior move already below V_fallback to its own value — never promoted', () => {
    const fallback = 0.6;
    // Below-fallback move: min(0.2, 0.6) = 0.2, so rankScore = f*0.2 +
    // (1-f)*0.2 = 0.2 regardless of f — sorted by its own (low) V.
    const lowPriorBelowFallback = rankScore(0.01, 0.12, 0.2, fallback);
    // Findable move whose V exceeds the fallback: saturates to its own V.
    const findableAboveFallback = rankScore(0.5, 0.12, 0.4, fallback);
    expect(lowPriorBelowFallback).toBe(0.2);
    expect(findableAboveFallback).toBe(0.4);
    // Removing the min() clamp would pull lowPriorBelowFallback UP toward
    // fallback (f=0.01/0.12≈0.083 => 0.083*0.2 + 0.917*0.6 ≈ 0.567, ABOVE
    // 0.2), breaking this exact-equality assertion — the mutation check
    // this test's SUMMARY records.
    expect(lowPriorBelowFallback).toBeLessThan(findableAboveFallback);
  });
});

// ─── rankFallbackValue (Phase 225 D-10b amended) ───────────────────────────

describe('rankFallbackValue', () => {
  it('normalizes by total prior — a weighted MEAN, not the raw weighted sum', () => {
    const children: readonly BackupChild[] = [
      { prior: 0.5, value: 0.8 },
      { prior: 0.3, value: 0.2 },
    ]; // priors sum to 0.8, not 1
    const rawSum = 0.5 * 0.8 + 0.3 * 0.2; // 0.46 — what an UNnormalized sum would give
    const expectedMean = rawSum / 0.8; // 0.575 — the correct normalized mean
    const result = rankFallbackValue(children);
    expect(result).toBeCloseTo(expectedMean, 10);
    expect(result).not.toBeCloseTo(rawSum, 5);
  });

  it('returns 0 (not backupExpectation\'s own 0.5 default) when every prior is 0 — D-10b amended', () => {
    const children: readonly BackupChild[] = [
      { prior: 0, value: 0.9 },
      { prior: 0, value: 0.1 },
    ];
    expect(rankFallbackValue(children)).toBe(0);
  });

  it('returns 0 for an empty list', () => {
    expect(rankFallbackValue([])).toBe(0);
  });
});

// ─── D-03 regression cases (restated for D-10a/D-10e, Pitfall 5) ───────────

describe('D-03 regression cases (restated for D-10a — V_fallback pinned by the stated rule BEFORE running)', () => {
  it('@600: Qxf2 (9% prior, Good) beats both Nb5 (5% prior, Best/high-V) and Rxf2 (57% prior, Mistake/low-V)', () => {
    const pRef600 = pRefForElo(600);

    // V approximations implied by the observed grades (Best > Good > Mistake).
    const V_NB5 = 0.6; // Best, high V
    const V_QXF2 = 0.57; // Good, slightly below Best
    const V_RXF2 = 0.35; // Mistake, well below Best
    const P_NB5 = 0.05;
    const P_QXF2 = 0.09;
    const P_RXF2 = 0.57;
    const unlistedPrior = 1 - P_NB5 - P_QXF2 - P_RXF2; // 0.29

    // V_fallback = 0.05*0.6 + 0.09*0.57 + 0.57*0.35 + 0.29*0.5 ≈ 0.4258
    // (total prior sums to exactly 1 here, so the mean equals the raw sum).
    const vFallback = rankFallbackValue([
      { prior: P_NB5, value: V_NB5 },
      { prior: P_QXF2, value: V_QXF2 },
      { prior: P_RXF2, value: V_RXF2 },
      { prior: unlistedPrior, value: UNLISTED_PRIOR_VALUE },
    ]);

    const scoreNb5 = rankScore(P_NB5, pRef600, V_NB5, vFallback);
    const scoreQxf2 = rankScore(P_QXF2, pRef600, V_QXF2, vFallback);
    const scoreRxf2 = rankScore(P_RXF2, pRef600, V_RXF2, vFallback);

    // Rxf2's prior (0.57) exceeds pRef600, so it saturates to its own V.
    expect(scoreRxf2).toBe(V_RXF2);

    expect(scoreQxf2).toBeGreaterThan(scoreNb5);
    expect(scoreQxf2).toBeGreaterThan(scoreRxf2);
  });

  it('@1000 restated (D-10e): the in-chart candidate (30% prior, V 0.58, saturated) still beats Qb8 (5% prior, V 0.60)', () => {
    // The original Phase 159 gap (Qb8 V 0.60 vs an in-chart V 0.55) FLIPS
    // under D-10a for any V_fallback above ~0.467 (225-RESEARCH.md C-3) —
    // which the pinned unlisted-mass-at-0.5 rule produces here (V_fallback
    // ≈ 0.529) — so that reversal IS the accepted Phase 159 showcase
    // reversal (D-10e), asserted instead by the rewritten
    // mctsSearch/fallbackExpectimax "Phase 159 D-01 findability ranking"
    // describes. This case is restated at a narrower V gap (0.60 vs 0.58)
    // where findability still wins.
    const pRef1000 = pRefForElo(1000);

    const V_QB8 = 0.6; // higher V than the chart candidate, but far below pRef
    const V_CHART_CANDIDATE = 0.58; // in-chart, prior well above pRef -> saturates
    const P_QB8 = 0.05;
    const P_CHART_CANDIDATE = 0.3;
    const unlistedPrior = 1 - P_QB8 - P_CHART_CANDIDATE; // 0.65

    // V_fallback = 0.05*0.6 + 0.3*0.58 + 0.65*0.5 ≈ 0.529.
    const vFallback = rankFallbackValue([
      { prior: P_QB8, value: V_QB8 },
      { prior: P_CHART_CANDIDATE, value: V_CHART_CANDIDATE },
      { prior: unlistedPrior, value: UNLISTED_PRIOR_VALUE },
    ]);

    const scoreQb8 = rankScore(P_QB8, pRef1000, V_QB8, vFallback);
    const scoreChartCandidate = rankScore(P_CHART_CANDIDATE, pRef1000, V_CHART_CANDIDATE, vFallback);

    expect(scoreChartCandidate).toBe(V_CHART_CANDIDATE); // saturated
    expect(scoreQb8).toBeLessThan(scoreChartCandidate);
  });
});
