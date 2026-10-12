/**
 * Shared fixtures for the Library Stats tests (Phase 239): per-TC flaw-comparison payload
 * entries modelled on the sketch 010 dev data.
 */

import type { TimeControlBucket } from '@/types/endgames';
import type {
  FlawBullet,
  FlawComparisonResponse,
  FlawComparisonTc,
  FlawDeltaMetric,
  FlawTrendPoint,
} from '@/types/library';

export const ANALYZED_GATE = 20;

export const FLAW_DELTA_METRICS: readonly FlawDeltaMetric[] = [
  'blunder',
  'mistake',
  'low_clock',
  'hasty',
  'unrushed',
  'opening',
  'middlegame',
  'endgame_phase',
  'miss',
  'lucky',
  'reversed',
  'squandered',
];

export function makeBullet(tag: FlawDeltaMetric, overrides: Partial<FlawBullet> = {}): FlawBullet {
  return {
    tag,
    delta: -0.2,
    ci_low: -0.4,
    ci_high: 0,
    player_rate: 1.2,
    opp_rate: 1.4,
    p_value: 0.05,
    player_events: 120,
    opp_events: 140,
    zone_lo: -0.31,
    zone_hi: 0.25,
    has_zone: true,
    low_sample: false,
    ...overrides,
  };
}

interface TcEntryOptions {
  analyzedN: number;
  blunder?: Partial<FlawBullet>;
  mistake?: Partial<FlawBullet>;
}

/** One TC entry with all 12 bullets; blunder and mistake can be overridden per test. */
export function makeTcEntry(tc: TimeControlBucket, options: TcEntryOptions): FlawComparisonTc {
  return {
    tc,
    analyzed_n: options.analyzedN,
    below_gate: options.analyzedN < ANALYZED_GATE,
    bullets: FLAW_DELTA_METRICS.map((tag) => {
      if (tag === 'blunder') return makeBullet(tag, options.blunder);
      if (tag === 'mistake') return makeBullet(tag, options.mistake);
      return makeBullet(tag);
    }),
  };
}

/** Sketch 010: blitz blunders 5.46 vs 6.12 (gap -0.66), rapid blunders 5.22 vs 5.83 (gap -0.61). */
export const BLITZ_ENTRY = makeTcEntry('blitz', {
  analyzedN: 1000,
  blunder: { player_rate: 5.4569, opp_rate: 6.1176, delta: -0.6607, player_events: 1916, opp_events: 1982 },
  mistake: { player_rate: 7.1, opp_rate: 7.34, delta: -0.24 },
});

export const RAPID_ENTRY = makeTcEntry('rapid', {
  analyzedN: 1841,
  blunder: { player_rate: 5.22, opp_rate: 5.83, delta: -0.61 },
  mistake: { player_rate: 6.4, opp_rate: 6.9, delta: -0.5 },
});

export function makeComparison(tcs: FlawComparisonTc[]): FlawComparisonResponse {
  return { tcs, analyzed_gate: ANALYZED_GATE };
}

export function makeTrendPoint(date: string): FlawTrendPoint {
  return {
    date,
    blunder_rate: 5,
    mistake_rate: 7,
    inaccuracy_rate: 9,
    games_in_window: 20,
    per_week_games: 4,
  };
}
