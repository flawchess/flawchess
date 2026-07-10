/**
 * moveQuality unit tests — pure, deterministic (no engine/worker involved).
 *
 * Covers every <behavior> bullet from 151.1-02-PLAN.md Task 1:
 * - classifyMoveQuality: empty map, single entry, and the 5-bucket boundary
 *   behavior (best / good / inaccuracy / mistake / blunder), straddling each
 *   flawThresholds boundary (INACCURACY_DROP/MISTAKE_DROP/BLUNDER_DROP) so
 *   classifyLiveSeverity's inclusive `>=` semantics are exercised precisely.
 * - selectCandidatesByMass: mass-threshold accumulation, top-5 hard cap, and
 *   forced inclusion of bestSan/playedSan even when they fall outside the
 *   0.95-mass/top-5 cut (D-02/D-06/D-07), plus the empty-perElo edge case.
 * - Constant assertions (CUMULATIVE_MASS_THRESHOLD, CANDIDATE_HARD_CAP).
 */

import { describe, it, expect } from 'vitest';
import { evalToExpectedScore, type MoverColor } from '@/lib/liveFlaw';
import { LICHESS_K } from '@/generated/flawThresholds';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import {
  classifyMoveQuality,
  selectCandidatesByMass,
  bucketMovesByQuality,
  QUALITY_BUCKET_ORDER,
  CUMULATIVE_MASS_THRESHOLD,
  CANDIDATE_HARD_CAP,
  type MoveGrade,
  type MoveQuality,
  type QualityBucketKey,
} from '../moveQuality';

const WHITE: MoverColor = 'white';

/** A tiny straddle offset used to test threshold-boundary semantics without
 *  relying on bit-exact floating-point equality (the sigmoid round-trip has
 *  double-precision noise at the ~1e-13 level, far below this). */
const STRADDLE = 1e-6;

/**
 * Analytic inverse of evalToExpectedScore for mover='white' (sign=+1):
 * es = 1 / (1 + exp(-k*cp))  =>  cp = -ln(1/es - 1) / k.
 * Used only to construct fixture cp values that produce a known expected
 * score / drop — not a reimplementation of the classification logic under
 * test (classifyMoveQuality / classifyLiveSeverity's bucket boundaries).
 */
function cpForExpectedScore(es: number): number {
  return -Math.log(1 / es - 1) / LICHESS_K;
}

function gradeForEs(es: number): MoveGrade {
  return { evalCp: cpForExpectedScore(es), evalMate: null, depth: 12 };
}

// ─── classifyMoveQuality ────────────────────────────────────────────────────

describe('classifyMoveQuality', () => {
  it('returns an empty map for an empty gradeMap', () => {
    const result = classifyMoveQuality(new Map(), WHITE);
    expect(result.size).toBe(0);
  });

  it('classifies a single entry as best', () => {
    const gradeMap = new Map<string, MoveGrade>([['e4', { evalCp: 0, evalMate: null, depth: 10 }]]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('e4')).toEqual({ quality: 'best', expectedScore: 0.5 });
  });

  it('assigns the max-expected-score candidate as best, verified via evalToExpectedScore', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - 0.03)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('e4')?.quality).toBe('best');
    expect(result.get('e4')?.expectedScore).toBe(evalToExpectedScore(0, null, WHITE));
  });

  it('classifies a clean non-best move (drop < INACCURACY_DROP) as good', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - 0.03)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('d4')?.quality).toBe('good');
  });

  it('classifies a mid-band drop (0.05 <= drop < 0.10) as inaccuracy', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['Nf3', gradeForEs(0.5 - 0.07)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('Nf3')?.quality).toBe('inaccuracy');
  });

  it('classifies a mid-band drop (0.10 <= drop < 0.15) as mistake', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['c4', gradeForEs(0.5 - 0.12)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('c4')?.quality).toBe('mistake');
  });

  it('classifies a large drop (drop >= 0.15) as blunder', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['a3', gradeForEs(0.5 - 0.2)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE);
    expect(result.get('a3')?.quality).toBe('blunder');
  });

  // ── Boundary straddle tests (>= semantics: at-or-above the threshold lands
  // in the higher band; just below stays in the lower band) ────────────────

  it('drop just below INACCURACY_DROP (0.05) stays good; just above becomes inaccuracy', () => {
    const below = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.05 - STRADDLE))],
    ]);
    const above = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.05 + STRADDLE))],
    ]);
    expect(classifyMoveQuality(below, WHITE).get('d4')?.quality).toBe('good');
    expect(classifyMoveQuality(above, WHITE).get('d4')?.quality).toBe('inaccuracy');
  });

  it('drop just below MISTAKE_DROP (0.10) stays inaccuracy; just above becomes mistake', () => {
    const below = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.1 - STRADDLE))],
    ]);
    const above = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.1 + STRADDLE))],
    ]);
    expect(classifyMoveQuality(below, WHITE).get('d4')?.quality).toBe('inaccuracy');
    expect(classifyMoveQuality(above, WHITE).get('d4')?.quality).toBe('mistake');
  });

  it('drop just below BLUNDER_DROP (0.15) stays mistake; just above becomes blunder', () => {
    const below = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.15 - STRADDLE))],
    ]);
    const above = new Map<string, MoveGrade>([
      ['e4', { evalCp: 0, evalMate: null, depth: 12 }],
      ['d4', gradeForEs(0.5 - (0.15 + STRADDLE))],
    ]);
    expect(classifyMoveQuality(below, WHITE).get('d4')?.quality).toBe('mistake');
    expect(classifyMoveQuality(above, WHITE).get('d4')?.quality).toBe('blunder');
  });

  // ── designatedBestSan: the primary engine's best move is the reference, so
  // the chart's "best" agrees with the eval bar + engine card (151.1 UAT). ──

  it('honors designatedBestSan as "best" even when another candidate scores higher', () => {
    // Nf6 (the primary engine's best) scores marginally BELOW d5 in this grading
    // pass — the exact near-tie that produced the self-contradictory tooltip.
    const gradeMap = new Map<string, MoveGrade>([
      ['Nf6', gradeForEs(0.5)],
      ['d5', gradeForEs(0.5 + 0.01)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE, 'Nf6');
    expect(result.get('Nf6')?.quality).toBe('best');
    // A candidate above the designated best (negative drop) is clean → "good".
    expect(result.get('d5')?.quality).toBe('good');
  });

  it('grades other candidates against the designatedBestSan, not the top scorer', () => {
    // Reference is Nf6 (es 0.5); e6 drops 0.07 below it → inaccuracy, regardless
    // of d5 being the numerically top move.
    const gradeMap = new Map<string, MoveGrade>([
      ['Nf6', gradeForEs(0.5)],
      ['d5', gradeForEs(0.5 + 0.01)],
      ['e6', gradeForEs(0.5 - 0.07)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE, 'Nf6');
    expect(result.get('e6')?.quality).toBe('inaccuracy');
  });

  it('falls back to the top scorer when designatedBestSan is null', () => {
    const gradeMap = new Map<string, MoveGrade>([
      ['Nf6', gradeForEs(0.5)],
      ['d5', gradeForEs(0.5 + 0.01)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE, null);
    expect(result.get('d5')?.quality).toBe('best');
  });

  it('falls back to the top scorer when designatedBestSan is not yet graded (streaming)', () => {
    // bestSan is set but its grade hasn't streamed into gradeMap yet (D-05).
    const gradeMap = new Map<string, MoveGrade>([
      ['d5', gradeForEs(0.5 + 0.01)],
      ['e6', gradeForEs(0.5)],
    ]);
    const result = classifyMoveQuality(gradeMap, WHITE, 'Nf6');
    expect(result.get('d5')?.quality).toBe('best');
  });
});

// ─── selectCandidatesByMass ─────────────────────────────────────────────────

describe('selectCandidatesByMass', () => {
  it('returns [] for an empty perElo', () => {
    expect(selectCandidatesByMass([], 1500, null, null)).toEqual([]);
  });

  it('stops mass accumulation once cumulative probability reaches the threshold', () => {
    const perElo: MoveCurvePoint[] = [
      {
        elo: 1500,
        moveProbabilities: { a: 0.5, b: 0.3, c: 0.15, d: 0.05 },
      },
    ];
    // cumulative before each: 0(<.95)->push a(.5); .5(<.95)->push b(.8);
    // .8(<.95)->push c(.95); .95>=.95 -> stop (d excluded).
    const result = selectCandidatesByMass(perElo, 1500, null, null);
    expect(result).toEqual(['a', 'b', 'c']);
  });

  it('selects the perElo rung nearest to selectedElo', () => {
    const perElo: MoveCurvePoint[] = [
      { elo: 1000, moveProbabilities: { far: 1.0 } },
      { elo: 1500, moveProbabilities: { near: 1.0 } },
    ];
    const result = selectCandidatesByMass(perElo, 1400, null, null);
    expect(result).toEqual(['near']);
  });

  it('caps the mass set to the top-5 by probability and force-includes bestSan/playedSan outside the cut', () => {
    const perElo: MoveCurvePoint[] = [
      {
        elo: 1500,
        moveProbabilities: {
          m1: 0.3,
          m2: 0.2,
          m3: 0.15,
          m4: 0.1,
          m5: 0.08,
          m6: 0.07,
          m7: 0.06,
          m8: 0.04,
        },
      },
    ];
    // Mass set (0.95 cut): m1..m7 (cumulative crosses 0.95 at m7 -> 0.96).
    // Top-5 cap of the mass set: m1..m5. m6 falls outside the cap and is NOT
    // force-included by anything, so it must be excluded from the result.
    // bestSan = m7 (in the mass set but outside the top-5 cap) -> force-included.
    // playedSan = m8 (outside the mass set entirely) -> force-included (D-07).
    const result = selectCandidatesByMass(perElo, 1500, 'm8', 'm7');
    expect(result).toEqual(['m1', 'm2', 'm3', 'm4', 'm5', 'm7', 'm8']);
    expect(result).not.toContain('m6');
  });

  it('skips force-inclusion when bestSan/playedSan are null', () => {
    const perElo: MoveCurvePoint[] = [
      {
        elo: 1500,
        moveProbabilities: { a: 0.5, b: 0.3, c: 0.15, d: 0.05 },
      },
    ];
    const result = selectCandidatesByMass(perElo, 1500, null, null);
    expect(result).toEqual(['a', 'b', 'c']);
  });

  it('returns candidates in probability-descending order', () => {
    const perElo: MoveCurvePoint[] = [
      {
        elo: 1500,
        moveProbabilities: { low: 0.1, high: 0.6, mid: 0.29, tiny: 0.01 },
      },
    ];
    const result = selectCandidatesByMass(perElo, 1500, null, null);
    expect(result).toEqual(['high', 'mid', 'low']);
  });
});

// ─── bucketMovesByQuality (move-quality bar, quick 260705-kfg) ───────────────

describe('bucketMovesByQuality', () => {
  const perElo: MoveCurvePoint[] = [
    { elo: 1000, moveProbabilities: { ignored: 1.0 } },
    {
      elo: 1500,
      moveProbabilities: { Ra8: 0.52, g4: 0.11, Rb1: 0.1, Ra5: 0.09, Nf3: 0.06 },
    },
  ];

  function quality(map: Record<string, MoveQuality>): Map<string, { quality: MoveQuality }> {
    return new Map(Object.entries(map).map(([san, q]) => [san, { quality: q }]));
  }

  function byKey(buckets: ReturnType<typeof bucketMovesByQuality>) {
    return new Map<QualityBucketKey, (typeof buckets)[number]>(buckets.map((b) => [b.key, b]));
  }

  it('always returns all buckets in the fixed worst→best→pending order', () => {
    const buckets = bucketMovesByQuality(perElo, 1500, [], new Map());
    expect(buckets.map((b) => b.key)).toEqual([...QUALITY_BUCKET_ORDER]);
    expect(buckets.every((b) => b.moves.length === 0 && b.probabilityMass === 0)).toBe(true);
  });

  it('folds best ∪ good into the single green "good" bucket', () => {
    const buckets = byKey(
      bucketMovesByQuality(perElo, 1500, ['Ra8', 'Nf3'], quality({ Ra8: 'best', Nf3: 'good' })),
    );
    expect(buckets.get('good')!.moves.map((m) => m.san)).toEqual(['Ra8', 'Nf3']);
    expect(buckets.get('good')!.probabilityMass).toBeCloseTo(0.58);
  });

  it('folds a "gem"-quality move into the "good" bucket (Phase 163) — never the "pending" default', () => {
    const buckets = byKey(
      bucketMovesByQuality(perElo, 1500, ['Ra8'], quality({ Ra8: 'gem' })),
    );
    expect(buckets.get('good')!.moves.map((m) => m.san)).toEqual(['Ra8']);
    expect(buckets.get('pending')!.moves).toEqual([]);
  });

  it('routes each severity to its own bucket and weights by Maia probability at the nearest rung', () => {
    const buckets = byKey(
      bucketMovesByQuality(
        perElo,
        1450, // nearest rung is 1500
        ['Ra8', 'g4', 'Rb1', 'Ra5'],
        quality({ Ra8: 'best', g4: 'blunder', Rb1: 'blunder', Ra5: 'mistake' }),
      ),
    );
    expect(buckets.get('blunder')!.probabilityMass).toBeCloseTo(0.21);
    expect(buckets.get('mistake')!.probabilityMass).toBeCloseTo(0.09);
    expect(buckets.get('good')!.probabilityMass).toBeCloseTo(0.52);
    expect(buckets.get('inaccuracy')!.probabilityMass).toBe(0);
  });

  it('sorts moves within a bucket by probability descending', () => {
    const buckets = byKey(
      bucketMovesByQuality(
        perElo,
        1500,
        ['Rb1', 'g4'], // 0.10, 0.11 — inserted low-first
        quality({ Rb1: 'blunder', g4: 'blunder' }),
      ),
    );
    expect(buckets.get('blunder')!.moves.map((m) => m.san)).toEqual(['g4', 'Rb1']);
  });

  it('puts ungraded (streaming) candidates in the pending bucket', () => {
    const buckets = byKey(
      bucketMovesByQuality(perElo, 1500, ['Ra8', 'g4'], quality({ Ra8: 'best' })),
    );
    expect(buckets.get('pending')!.moves.map((m) => m.san)).toEqual(['g4']);
    expect(buckets.get('good')!.moves.map((m) => m.san)).toEqual(['Ra8']);
  });

  it('assigns probability 0 to a shown move absent from the nearest rung', () => {
    const buckets = byKey(
      bucketMovesByQuality(perElo, 1500, ['missing'], quality({ missing: 'good' })),
    );
    expect(buckets.get('good')!.moves).toEqual([{ san: 'missing', probability: 0 }]);
  });
});

// ─── Constant assertions ────────────────────────────────────────────────────

describe('constants', () => {
  it('CUMULATIVE_MASS_THRESHOLD is 0.95 (D-02)', () => {
    expect(CUMULATIVE_MASS_THRESHOLD).toBe(0.95);
  });

  it('CANDIDATE_HARD_CAP is 5 (D-06)', () => {
    expect(CANDIDATE_HARD_CAP).toBe(5);
  });
});
