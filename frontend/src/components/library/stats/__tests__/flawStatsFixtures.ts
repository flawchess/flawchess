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
  /** Per-metric overrides for any of the 12 metrics (applied after blunder / mistake). */
  overrides?: Partial<Record<FlawDeltaMetric, Partial<FlawBullet>>>;
}

/** One TC entry with all 12 bullets; blunder and mistake can be overridden per test. */
export function makeTcEntry(tc: TimeControlBucket, options: TcEntryOptions): FlawComparisonTc {
  return {
    tc,
    analyzed_n: options.analyzedN,
    below_gate: options.analyzedN < ANALYZED_GATE,
    bullets: FLAW_DELTA_METRICS.map((tag) => {
      const base = tag === 'blunder' ? options.blunder : tag === 'mistake' ? options.mistake : undefined;
      return makeBullet(tag, { ...base, ...options.overrides?.[tag] });
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

/** One sketch row: gap and the real benchmark band; flaw counts default to a normal sample. */
function sketchRow(delta: number, zoneLo: number, zoneHi: number): Partial<FlawBullet> {
  return { delta, zone_lo: zoneLo, zone_hi: zoneHi, player_events: 500, opp_events: 500 };
}

/**
 * Sketch 010 rapid context-tag rows (gap, benchmark band). Ranked by band-width distance:
 * strengths hasty 3.9, opening 1.6, middlegame 0.6; weaknesses low_clock 3.5, squandered 0.5,
 * unrushed 0.2, reversed 0.1 (cut by the top 3); typical: endgame, miss, lucky.
 */
export const SKETCH_RAPID_ENTRY = makeTcEntry('rapid', {
  analyzedN: 1841,
  blunder: { player_rate: 5.22, opp_rate: 5.83, delta: -0.61 },
  mistake: { player_rate: 6.4, opp_rate: 6.9, delta: -0.5 },
  overrides: {
    low_clock: sketchRow(0.4129, -0.08, 0.03),
    hasty: sketchRow(-2.0752, -0.28, 0.18),
    unrushed: sketchRow(0.4965, -0.38, 0.36),
    opening: sketchRow(-0.5894, -0.15, 0.13),
    middlegame: sketchRow(-0.5552, -0.27, 0.23),
    endgame_phase: sketchRow(-0.0229, -0.12, 0.1),
    miss: sketchRow(-0.0454, -0.11, 0.11),
    lucky: sketchRow(0.0699, -0.09, 0.09),
    reversed: sketchRow(0.0506, -0.04, 0.04),
    squandered: sketchRow(0.1522, -0.07, 0.08),
  },
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
