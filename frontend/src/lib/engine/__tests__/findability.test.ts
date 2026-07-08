/**
 * findability.ts unit tests (Phase 159 D-01/D-02/D-03).
 *
 * Covers:
 * - pRefForElo: monotonically non-increasing across the 600-2600 domain,
 *   clamps to the first/last anchor outside that range.
 * - rankScore: exact saturation at pYou >= pRef (factor 1, strict equality),
 *   sub-saturation scaling below pRef, the pRef<=0 degenerate guard, and the
 *   upper-bound invariant (rankScore never exceeds value).
 * - The three D-03 regression cases: a 5%-prior high-V move (Nb5 @600) does
 *   NOT top the ranking; a 9%-prior mid-V move (Qxf2 @600) DOES beat both the
 *   5%-prior high-V move and a 57%-prior low-V Mistake (Rxf2); a ~5%-prior
 *   tail move (Qb8 @1000) does NOT beat an in-chart candidate of
 *   comparable-or-higher V.
 *
 * Fixture prior/value pairs approximate the real observed relationships from
 * live 600/1000-ELO analyses (159-CONTEXT.md D-03) — the real FENs were not
 * recovered this session (159-RESEARCH.md Open Question 1); an end-to-end
 * live check against the real positions is deferred to the phase-close UAT
 * checkpoint (159-04's verification).
 */

import { describe, it, expect } from 'vitest';
import { P_REF_ANCHORS, pRefForElo, rankScore } from '../findability';

// ─── pRefForElo ──────────────────────────────────────────────────────────────

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

// ─── rankScore ───────────────────────────────────────────────────────────────

describe('rankScore', () => {
  it('returns exactly value (strict equality) when pYou >= pRef — saturation at factor 1', () => {
    expect(rankScore(0.5, 0.12, 0.73)).toBe(0.73);
    expect(rankScore(0.12, 0.12, 0.73)).toBe(0.73); // equality boundary also saturates
  });

  it('scales by pYou/pRef when pYou < pRef', () => {
    expect(rankScore(0.06, 0.12, 0.8)).toBeCloseTo(0.4, 10);
  });

  it('returns value unmodified when pRef <= 0 (degenerate guard)', () => {
    expect(rankScore(0.05, 0, 0.6)).toBe(0.6);
    expect(rankScore(0.05, -1, 0.6)).toBe(0.6);
  });

  it('never exceeds value for any pYou (upper bound invariant)', () => {
    const value = 0.65;
    const pRef = 0.08;
    for (const pYou of [0, 0.01, 0.08, 0.5, 1, 5]) {
      expect(rankScore(pYou, pRef, value)).toBeLessThanOrEqual(value);
    }
  });
});

// ─── D-03 regression cases ───────────────────────────────────────────────────

describe('D-03 regression cases', () => {
  it('@600: Qxf2 (9% prior, Good) beats both Nb5 (5% prior, Best/high-V) and Rxf2 (57% prior, Mistake/low-V)', () => {
    const pRef600 = pRefForElo(600);

    // V approximations implied by the observed grades (Best > Good > Mistake).
    const V_NB5 = 0.6; // Best, high V
    const V_QXF2 = 0.57; // Good, slightly below Best
    const V_RXF2 = 0.35; // Mistake, well below Best

    const scoreNb5 = rankScore(0.05, pRef600, V_NB5);
    const scoreQxf2 = rankScore(0.09, pRef600, V_QXF2);
    const scoreRxf2 = rankScore(0.57, pRef600, V_RXF2);

    // Rxf2's prior (0.57) exceeds pRef600, so it saturates to its own V.
    expect(scoreRxf2).toBe(V_RXF2);

    expect(scoreQxf2).toBeGreaterThan(scoreNb5);
    expect(scoreQxf2).toBeGreaterThan(scoreRxf2);
  });

  it('@1000: Qb8 (~5% prior, tail move) does NOT beat an in-chart candidate of comparable-or-higher V', () => {
    const pRef1000 = pRefForElo(1000);

    const V_QB8 = 0.6; // higher V than the chart candidate, but far below pRef
    const V_CHART_CANDIDATE = 0.55; // in-chart, prior well above pRef -> saturates

    const scoreQb8 = rankScore(0.05, pRef1000, V_QB8);
    const scoreChartCandidate = rankScore(0.3, pRef1000, V_CHART_CANDIDATE);

    expect(scoreChartCandidate).toBe(V_CHART_CANDIDATE); // saturated
    expect(scoreQb8).toBeLessThan(scoreChartCandidate);
  });
});
