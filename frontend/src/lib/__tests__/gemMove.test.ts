/**
 * gemMove unit tests — pure, deterministic (no engine/worker involved).
 *
 * Covers: a lost-position best-try still qualifies, no opening-ply guard (there
 * is no ply argument to gate on), mover-agnostic classification (no color
 * parameter), the GEM_MAIA_MAX_PROB constant, plus the two free-lunch guards
 * (saturation, forced recapture) and summarizeForGem's argmax/runner-up/empty
 * reduction.
 */

import { describe, it, expect } from 'vitest';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { MISTAKE_DROP, LICHESS_K } from '@/generated/flawThresholds';
import {
  classifyGem,
  classifyGreat,
  summarizeForGem,
  rareTierForProbability,
  onlyGoodMoveSan,
  GEM_MAIA_MAX_PROB,
  GREAT_MAIA_MAX_PROB,
  type GemGrade,
} from '../gemMove';

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
  it('a lost-position best-try still qualifies (no still-losing exclusion)', () => {
    expect(
      classifyGem({
        maiaProbability: 0.02,
        playedIsBest: true,
        bestEs: 0.2,
        secondBestEs: 0.05,
      }),
    ).toBe(true);
  });

  it('qualifying inputs classify true regardless of ply — classifyGem takes no ply argument, so no opening guard can ever gate it', () => {
    // Same qualifying inputs as above, re-asserted to document there is no ply
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

  it('GEM_MAIA_MAX_PROB is exactly 0.3', () => {
    expect(GEM_MAIA_MAX_PROB).toBe(0.3);
  });

  it('a maiaProbability of 0.15 with a passing C2 now classifies as a gem (would have failed C1 at the old 0.1 threshold)', () => {
    expect(
      classifyGem({
        maiaProbability: 0.15,
        playedIsBest: true,
        bestEs: 0.9,
        secondBestEs: 0.5,
      }),
    ).toBe(true);
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

// ─── classifyGreat ──────────────────────────────────────────────────────────

describe('classifyGreat', () => {
  it('qualifying inputs in the (0.30, 0.70] band with a passing C2 margin classify as great', () => {
    expect(
      classifyGreat({
        maiaProbability: 0.6,
        playedIsBest: true,
        bestEs: 0.55,
        secondBestEs: 0.4,
      }),
    ).toBe(true);
  });

  it('GREAT_MAIA_MAX_PROB is exactly 0.7', () => {
    expect(GREAT_MAIA_MAX_PROB).toBe(0.7);
  });

  it('returns false at the GEM ceiling (0.10 <= GEM_MAIA_MAX_PROB) — that is a gem, not a great', () => {
    expect(
      classifyGreat({
        maiaProbability: 0.1,
        playedIsBest: true,
        bestEs: 0.55,
        secondBestEs: 0.4,
      }),
    ).toBe(false);
  });

  it('returns false above the GREAT ceiling (0.80 > GREAT_MAIA_MAX_PROB)', () => {
    expect(
      classifyGreat({
        maiaProbability: 0.8,
        playedIsBest: true,
        bestEs: 0.55,
        secondBestEs: 0.4,
      }),
    ).toBe(false);
  });

  it('returns false when the ES margin is below MISTAKE_DROP (0.07 < 0.10), regardless of maiaProbability (shared C2 gate)', () => {
    expect(
      classifyGreat({
        maiaProbability: 0.35,
        playedIsBest: true,
        bestEs: 0.47,
        secondBestEs: 0.4,
      }),
    ).toBe(false);
  });

  it('returns false when maiaProbability is null', () => {
    expect(
      classifyGreat({ maiaProbability: null, playedIsBest: true, bestEs: 0.55, secondBestEs: 0.4 }),
    ).toBe(false);
  });

  it('returns false when playedIsBest is false', () => {
    expect(
      classifyGreat({ maiaProbability: 0.35, playedIsBest: false, bestEs: 0.55, secondBestEs: 0.4 }),
    ).toBe(false);
  });

  it('boundary: maiaProbability exactly 0.50 (GREAT_MAIA_MAX_PROB) classifies true — inclusive upper bound', () => {
    expect(
      classifyGreat({
        maiaProbability: GREAT_MAIA_MAX_PROB,
        playedIsBest: true,
        bestEs: 0.55,
        secondBestEs: 0.4,
      }),
    ).toBe(true);
  });

  it('boundary: maiaProbability exactly 0.20 (GEM_MAIA_MAX_PROB) classifies false — half-open (GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB] band excludes the lower bound', () => {
    expect(
      classifyGreat({
        maiaProbability: GEM_MAIA_MAX_PROB,
        playedIsBest: true,
        bestEs: 0.55,
        secondBestEs: 0.4,
      }),
    ).toBe(false);
  });

  it('returns false when bestEs is null', () => {
    expect(
      classifyGreat({ maiaProbability: 0.35, playedIsBest: true, bestEs: null, secondBestEs: 0.4 }),
    ).toBe(false);
  });

  it('returns false when secondBestEs is null', () => {
    expect(
      classifyGreat({ maiaProbability: 0.35, playedIsBest: true, bestEs: 0.55, secondBestEs: null }),
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

  it('classifies identically regardless of mover — symmetric best/second-best for white and black', () => {
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

  // ── Ungraded (null/null) entries ──────────────────────

  it('skips ungraded null/null entries — a phantom 0.5 must not displace the real argmax in a lost position', () => {
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

  it('an ungraded entry never becomes secondBestEs in a winning position (no spurious C2 gap)', () => {
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

  it('an all-ungraded map reduces to all-null fields (same as empty)', () => {
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

// ─── rareTierForProbability / onlyGoodMoveSan (quick 261031-g4l) ───────────

describe('rareTierForProbability', () => {
  it('maps the C1 bands with inclusive upper bounds', () => {
    expect(rareTierForProbability(0)).toBe('gem');
    expect(rareTierForProbability(GEM_MAIA_MAX_PROB)).toBe('gem');
    expect(rareTierForProbability(GEM_MAIA_MAX_PROB + 0.01)).toBe('great');
    expect(rareTierForProbability(GREAT_MAIA_MAX_PROB)).toBe('great');
    expect(rareTierForProbability(GREAT_MAIA_MAX_PROB + 0.01)).toBe('best');
    expect(rareTierForProbability(1)).toBe('best');
  });
});

describe('onlyGoodMoveSan', () => {
  // Gap well above MISTAKE_DROP vs well below it.
  const clearGap = new Map<string, GemGrade>([
    ['Qg5+', gradeForEs(0.95)],
    ['Qe4', gradeForEs(0.3)],
  ]);
  const smallGap = new Map<string, GemGrade>([
    ['Qg5+', gradeForEs(0.6)],
    ['Qe4', gradeForEs(0.59)],
  ]);

  it('returns bestSan when it is the graded argmax and beats the runner-up by MISTAKE_DROP', () => {
    expect(onlyGoodMoveSan(clearGap, 'Qg5+', WHITE)).toBe('Qg5+');
  });

  it('returns null when the gap is below MISTAKE_DROP', () => {
    expect(onlyGoodMoveSan(smallGap, 'Qg5+', WHITE)).toBeNull();
  });

  it('returns null when bestSan is not the graded argmax', () => {
    expect(onlyGoodMoveSan(clearGap, 'Qe4', WHITE)).toBeNull();
  });

  it('returns null without a bestSan or a runner-up', () => {
    expect(onlyGoodMoveSan(clearGap, null, WHITE)).toBeNull();
    expect(onlyGoodMoveSan(new Map([['Qg5+', gradeForEs(0.95)]]), 'Qg5+', WHITE)).toBeNull();
  });

  it('trusts a stored gem/great tag even when live grading misses C2', () => {
    const tagged = new Map<string, GemGrade & { quality?: string }>([
      ['Qg5+', { ...gradeForEs(0.6), quality: 'great' }],
      ['Qe4', gradeForEs(0.59)],
    ]);
    expect(onlyGoodMoveSan(tagged, 'Qg5+', WHITE)).toBe('Qg5+');
  });
});
