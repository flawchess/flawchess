/**
 * gemMove unit tests — pure, deterministic (no engine/worker involved).
 *
 * Traces 1:1 to 163-RESEARCH.md's Phase Requirements → Test map: D-01 (lost-
 * position best-try still qualifies), D-02 (no opening-ply guard — there is
 * no ply argument to gate on), D-04 (mover-agnostic — no color parameter),
 * D-07 (GEM_MAIA_MAX_PROB constant), plus the two free-lunch guards
 * (saturation, forced recapture) and summarizeForGem's argmax/runner-up/empty
 * reduction.
 */

import { describe, it, expect } from 'vitest';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP, LICHESS_K } from '@/generated/flawThresholds';
import { classifyGem, summarizeForGem, GEM_MAIA_MAX_PROB, type GemGrade } from '../gemMove';

const WHITE: MoverColor = 'white';
const BLACK: MoverColor = 'black';

/** Analytic inverse of evalToExpectedScore for mover='white' (sign=+1):
 *  es = 1 / (1 + exp(-k*cp))  =>  cp = -ln(1/es - 1) / k. Fixture helper
 *  only — not a reimplementation of the classification logic under test. */
function cpForExpectedScore(es: number): number {
  return -Math.log(1 / es - 1) / LICHESS_K;
}

function gradeForEs(es: number): GemGrade {
  return { evalCp: cpForExpectedScore(es), evalMate: null };
}

// ─── classifyGem ────────────────────────────────────────────────────────────

describe('classifyGem', () => {
  it('D-01: a lost-position best-try still qualifies (no still-losing exclusion)', () => {
    expect(
      classifyGem({
        maiaProbability: 0.02,
        playedIsBest: true,
        bestEs: 0.2,
        secondBestEs: 0.05,
      }),
    ).toBe(true);
  });

  it('D-02: qualifying inputs classify true regardless of ply — classifyGem takes no ply argument, so no opening guard can ever gate it', () => {
    // Same qualifying inputs as D-01, re-asserted to document there is no ply
    // parameter in the classifyGem signature to gate on.
    expect(
      classifyGem({
        maiaProbability: 0.02,
        playedIsBest: true,
        bestEs: 0.2,
        secondBestEs: 0.05,
      }),
    ).toBe(true);
  });

  it('D-07: GEM_MAIA_MAX_PROB is exactly 0.05', () => {
    expect(GEM_MAIA_MAX_PROB).toBe(0.05);
  });

  it('returns false when maiaProbability is null (C1 fail)', () => {
    expect(
      classifyGem({ maiaProbability: null, playedIsBest: true, bestEs: 0.9, secondBestEs: 0.5 }),
    ).toBe(false);
  });

  it('returns false when maiaProbability exceeds GEM_MAIA_MAX_PROB (C1 fail)', () => {
    expect(
      classifyGem({
        maiaProbability: GEM_MAIA_MAX_PROB + 0.001,
        playedIsBest: true,
        bestEs: 0.9,
        secondBestEs: 0.5,
      }),
    ).toBe(false);
  });

  it('returns true at exactly the GEM_MAIA_MAX_PROB boundary (inclusive <=)', () => {
    expect(
      classifyGem({
        maiaProbability: GEM_MAIA_MAX_PROB,
        playedIsBest: true,
        bestEs: 0.9,
        secondBestEs: 0.5,
      }),
    ).toBe(true);
  });

  it('returns false when the played move is not the graded best (C2 fail)', () => {
    expect(
      classifyGem({ maiaProbability: 0.01, playedIsBest: false, bestEs: 0.9, secondBestEs: 0.5 }),
    ).toBe(false);
  });

  it('returns false when bestEs is null', () => {
    expect(
      classifyGem({ maiaProbability: 0.01, playedIsBest: true, bestEs: null, secondBestEs: 0.5 }),
    ).toBe(false);
  });

  it('returns false when secondBestEs is null', () => {
    expect(
      classifyGem({ maiaProbability: 0.01, playedIsBest: true, bestEs: 0.9, secondBestEs: null }),
    ).toBe(false);
  });

  it('returns false when the ES gap is below MISTAKE_DROP (C2 fail)', () => {
    expect(
      classifyGem({
        maiaProbability: 0.01,
        playedIsBest: true,
        bestEs: 0.5,
        secondBestEs: 0.5 - (MISTAKE_DROP - 1e-6),
      }),
    ).toBe(false);
  });

  it('returns true when the ES gap is exactly MISTAKE_DROP (inclusive >=)', () => {
    // Constructed as MISTAKE_DROP - 0 (not 0.5 - MISTAKE_DROP) to avoid a
    // floating-point subtraction that lands a hair below the true boundary.
    expect(
      classifyGem({
        maiaProbability: 0.01,
        playedIsBest: true,
        bestEs: MISTAKE_DROP,
        secondBestEs: 0,
      }),
    ).toBe(true);
  });

  // ── Free-lunch guards ─────────────────────────────────────────────────────

  it('free-lunch guard 1 (saturation): near-1.0 evals with gap < MISTAKE_DROP fail even at low Maia probability', () => {
    const bestEs = evalToExpectedScore(1000, null, WHITE);
    const secondBestEs = evalToExpectedScore(600, null, WHITE);
    expect(bestEs - secondBestEs).toBeLessThan(MISTAKE_DROP);
    expect(
      classifyGem({ maiaProbability: 0.01, playedIsBest: true, bestEs, secondBestEs }),
    ).toBe(false);
  });

  it('free-lunch guard 2 (forced recapture): a large ES gap fails when maiaProbability is well above the ceiling', () => {
    expect(
      classifyGem({
        maiaProbability: 0.85,
        playedIsBest: true,
        bestEs: 0.9,
        secondBestEs: 0.2,
      }),
    ).toBe(false);
  });
});

// ─── summarizeForGem ────────────────────────────────────────────────────────

describe('summarizeForGem', () => {
  it('returns all-null fields for an empty map', () => {
    const result = summarizeForGem(new Map(), WHITE);
    expect(result).toEqual({ bestSan: null, bestEs: null, secondBestEs: null });
  });

  it('returns secondBestEs null for a single-entry map', () => {
    const gradeBySan = new Map<string, GemGrade>([['e4', { evalCp: 0, evalMate: null }]]);
    const result = summarizeForGem(gradeBySan, WHITE);
    expect(result.bestSan).toBe('e4');
    expect(result.bestEs).toBe(evalToExpectedScore(0, null, WHITE));
    expect(result.secondBestEs).toBeNull();
  });

  it('returns the argmax SAN/ES as best and the runner-up ES as secondBestEs', () => {
    const gradeBySan = new Map<string, GemGrade>([
      ['e4', gradeForEs(0.5)],
      ['d4', gradeForEs(0.9)],
      ['c4', gradeForEs(0.3)],
    ]);
    const result = summarizeForGem(gradeBySan, WHITE);
    expect(result.bestSan).toBe('d4');
    expect(result.bestEs).toBeCloseTo(0.9);
    expect(result.secondBestEs).toBeCloseTo(0.5);
  });

  it('D-04: classifies identically regardless of mover — symmetric best/second-best for white and black', () => {
    const gradeBySan = new Map<string, GemGrade>([
      ['e4', { evalCp: 100, evalMate: null }],
      ['d4', { evalCp: 300, evalMate: null }],
      ['c4', { evalCp: -50, evalMate: null }],
    ]);
    const whiteResult = summarizeForGem(gradeBySan, WHITE);
    const blackResult = summarizeForGem(gradeBySan, BLACK);
    // White prefers the highest cp; Black (mirrored sigmoid) prefers the lowest.
    expect(whiteResult.bestSan).toBe('d4');
    expect(blackResult.bestSan).toBe('c4');
    // Both sides' bestEs/secondBestEs are symmetric around 0.5 (same magnitude
    // reasoning, opposite direction) — proving no color-specific branching.
    expect(whiteResult.bestEs).toBeCloseTo(evalToExpectedScore(300, null, WHITE));
    expect(blackResult.bestEs).toBeCloseTo(evalToExpectedScore(-50, null, BLACK));
  });

  // ── Ungraded (null/null) entries — 163-REVIEW WR-02 ──────────────────────

  it('WR-02: skips ungraded null/null entries — a phantom 0.5 must not displace the real argmax in a lost position (D-01)', () => {
    // All REAL evals are losing (es < 0.5); the ungraded entry would otherwise
    // read as a fabricated 0.5 and steal bestSan from the genuine best try.
    const gradeBySan = new Map<string, GemGrade>([
      ['Rh6', gradeForEs(0.2)], // the only defensive resource — real argmax
      ['Kg8', gradeForEs(0.05)],
      ['Qe2', { evalCp: null, evalMate: null }], // ungraded — no evidence
    ]);
    const result = summarizeForGem(gradeBySan, WHITE);
    expect(result.bestSan).toBe('Rh6');
    expect(result.bestEs).toBeCloseTo(0.2);
    expect(result.secondBestEs).toBeCloseTo(0.05);
  });

  it('WR-02: an ungraded entry never becomes secondBestEs in a winning position (no spurious C2 gap)', () => {
    // With one real grade + one ungraded entry, the phantom 0.5 must not serve
    // as the runner-up — secondBestEs stays null, so classifyGem cannot pass C2
    // on fabricated data.
    const gradeBySan = new Map<string, GemGrade>([
      ['Qxh7#', gradeForEs(0.95)],
      ['O-O', { evalCp: null, evalMate: null }], // ungraded — no evidence
    ]);
    const result = summarizeForGem(gradeBySan, WHITE);
    expect(result.bestSan).toBe('Qxh7#');
    expect(result.secondBestEs).toBeNull();
  });

  it('WR-02: an all-ungraded map reduces to all-null fields (same as empty)', () => {
    const gradeBySan = new Map<string, GemGrade>([
      ['e4', { evalCp: null, evalMate: null }],
      ['d4', { evalCp: null, evalMate: null }],
    ]);
    expect(summarizeForGem(gradeBySan, WHITE)).toEqual({
      bestSan: null,
      bestEs: null,
      secondBestEs: null,
    });
  });
});
