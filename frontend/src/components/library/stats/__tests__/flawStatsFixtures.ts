/**
 * Shared fixtures for the Library Stats tests: per-TC flaw-comparison payload
 * entries modelled on the dev data.
 */

import { TEMPO_PHASE_PHASES, TEMPO_PHASE_TEMPOS } from '@/lib/flawComparisonMeta';
import { TACTIC_COMPARISON_FAMILIES, type TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TimeControlBucket } from '@/types/endgames';
import type {
  FlawBullet,
  FlawComparisonResponse,
  FlawComparisonTc,
  FlawDeltaMetric,
  FlawPhaseMetric,
  FlawTempoMetric,
  FlawTrendPoint,
  TacticBullet,
  TacticComparisonResponse,
  TacticComparisonTc,
  TacticSide,
  TempoPhaseCell,
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
    zone_lo: -0.3,
    zone_hi: 0.3,
    has_zone: true,
    significant: true,
    ...overrides,
  };
}

/** A small, non-significant crossed cell (no zone) unless overridden. */
export function makeTempoPhaseCell(
  tempo: FlawTempoMetric,
  phase: FlawPhaseMetric,
  overrides: Partial<TempoPhaseCell> = {},
): TempoPhaseCell {
  return {
    tempo,
    phase,
    delta: 0.1,
    ci_low: -0.2,
    ci_high: 0.4,
    player_rate: 0.6,
    opp_rate: 0.5,
    p_value: 0.5,
    player_events: 30,
    opp_events: 25,
    zone_lo: 0,
    zone_hi: 0,
    has_zone: false,
    significant: false,
    ...overrides,
  };
}

interface TcEntryOptions {
  analyzedN: number;
  /** Coverage denominator; defaults to analyzedN (fully analyzed). */
  totalN?: number;
  blunder?: Partial<FlawBullet>;
  mistake?: Partial<FlawBullet>;
  /** Per-metric overrides for any of the 12 metrics (applied after blunder / mistake). */
  overrides?: Partial<Record<FlawDeltaMetric, Partial<FlawBullet>>>;
  /** Per-cell overrides of the 9 crossed tempo x phase cells, keyed `tempo:phase`. */
  tempoPhase?: Partial<Record<`${FlawTempoMetric}:${FlawPhaseMetric}`, Partial<TempoPhaseCell>>>;
}

/** One TC entry with all 12 bullets; blunder and mistake can be overridden per test. */
export function makeTcEntry(tc: TimeControlBucket, options: TcEntryOptions): FlawComparisonTc {
  return {
    tc,
    analyzed_n: options.analyzedN,
    total_n: options.totalN ?? options.analyzedN,
    below_gate: options.analyzedN < ANALYZED_GATE,
    bullets: FLAW_DELTA_METRICS.map((tag) => {
      const base = tag === 'blunder' ? options.blunder : tag === 'mistake' ? options.mistake : undefined;
      return makeBullet(tag, { ...base, ...options.overrides?.[tag] });
    }),
    tempo_phase_cells: TEMPO_PHASE_PHASES.flatMap((phase) =>
      TEMPO_PHASE_TEMPOS.map((tempo) =>
        makeTempoPhaseCell(tempo, phase, options.tempoPhase?.[`${tempo}:${phase}`]),
      ),
    ),
  };
}

/** Blitz blunders 5.46 vs 6.12 (gap -0.66), rapid blunders 5.22 vs 5.83 (gap -0.61). */
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

/** One row: gap and a symmetric benchmark band; flaw counts default to a normal sample. */
function sketchRow(delta: number, bandHalfWidth: number): Partial<FlawBullet> {
  return {
    delta,
    zone_lo: -bandHalfWidth,
    zone_hi: bandHalfWidth,
    player_events: 500,
    opp_events: 500,
  };
}

/**
 * Rapid context-tag rows (gap, benchmark band): better hasty, opening,
 * middlegame; worse low_clock, squandered, unrushed, reversed; typical endgame, miss, lucky.
 */
export const SKETCH_RAPID_ENTRY = makeTcEntry('rapid', {
  analyzedN: 1841,
  blunder: { player_rate: 5.22, opp_rate: 5.83, delta: -0.61 },
  mistake: { player_rate: 6.4, opp_rate: 6.9, delta: -0.5 },
  overrides: {
    low_clock: sketchRow(0.4129, 0.05),
    hasty: sketchRow(-2.0752, 0.23),
    unrushed: sketchRow(0.4965, 0.37),
    opening: sketchRow(-0.5894, 0.14),
    middlegame: sketchRow(-0.5552, 0.25),
    endgame_phase: sketchRow(-0.0229, 0.11),
    miss: sketchRow(-0.0454, 0.11),
    lucky: sketchRow(0.0699, 0.09),
    reversed: sketchRow(0.0506, 0.04),
    squandered: sketchRow(0.1522, 0.07),
  },
});

export function makeComparison(tcs: FlawComparisonTc[], totalN?: number): FlawComparisonResponse {
  return {
    tcs,
    analyzed_gate: ANALYZED_GATE,
    total_n: totalN ?? tcs.reduce((sum, t) => sum + t.total_n, 0),
  };
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

// ─── Tactic comparison (per 100 games) ─────────────────────────────────────────

export const TACTIC_SIDES: readonly TacticSide[] = ['missed', 'allowed'];

interface TacticBulletOptions {
  /** Your flaws with this family on this side. */
  you?: number;
  /** Your opponents' flaws with it. */
  opp?: number;
  analyzedN?: number;
  /** Typical-gap band per 100 games; omit for a band-less family-side (has_zone false). */
  zone?: readonly [number, number];
}

/** One tactic bullet built from raw flaw counts: rates per 100 games, zero flaws -> null stats. */
export function makeTacticBullet(
  family: TacticFamily,
  orientation: TacticSide,
  options: TacticBulletOptions = {},
): TacticBullet {
  const { you = 0, opp = 0, analyzedN = 1841, zone } = options;
  const none = you + opp === 0;
  const youRate = none ? null : (you / analyzedN) * 100;
  const oppRate = none ? null : (opp / analyzedN) * 100;
  const delta = youRate === null || oppRate === null ? null : youRate - oppRate;
  return {
    family,
    orientation,
    you_rate: youRate,
    opp_rate: oppRate,
    delta,
    ci_low: delta === null ? null : delta - 1,
    ci_high: delta === null ? null : delta + 1,
    p_value: delta === null ? null : 0.04,
    you_events: you,
    opp_events: opp,
    zone_lo: zone ? zone[0] : 0,
    zone_hi: zone ? zone[1] : 0,
    has_zone: zone !== undefined,
    // Mirrors the backend significance gate on the fixture CI (delta +- 1): it excludes 0.
    significant: delta !== null && Math.abs(delta) > 1,
  };
}

/** `fork:missed` -> options; every other family-side is a zero-flaw, band-less bullet. */
export type TacticOverrides = Partial<Record<`${TacticFamily}:${TacticSide}`, TacticBulletOptions>>;

/**
 * One TC entry with all 38 bullets in the API order (family order, missed before allowed).
 * Pass `reverse` to scramble the payload order: the UI must not depend on it.
 */
export function makeTacticTcEntry(
  tc: TimeControlBucket,
  analyzedN: number,
  overrides: TacticOverrides = {},
  reverse = false,
): TacticComparisonTc {
  const bullets = TACTIC_COMPARISON_FAMILIES.flatMap(({ family }) =>
    TACTIC_SIDES.map((side) =>
      makeTacticBullet(family, side, { analyzedN, ...overrides[`${family}:${side}`] }),
    ),
  );
  return {
    tc,
    analyzed_n: analyzedN,
    below_gate: analyzedN < ANALYZED_GATE,
    bullets: reverse ? bullets.reverse() : bullets,
  };
}

/** Rapid: fork missed 84 vs 44, allowed 134 vs 180 (4.56 vs 2.39 and 7.28 vs 9.78 per 100 games). */
export const SKETCH_RAPID_TACTIC_OVERRIDES: TacticOverrides = {
  'fork:missed': { you: 84, opp: 44, zone: [-0.7, 0.7] },
  'fork:allowed': { you: 134, opp: 180 },
  'pin:missed': { you: 42, opp: 37 },
  'pin:allowed': { you: 72, opp: 70 },
  'hanging:allowed': { you: 190, opp: 254 },
  'mate:missed': { you: 136, opp: 90 },
  'mate:allowed': { you: 193, opp: 267 },
  'discovered_attack:allowed': { you: 50, opp: 50 },
  'sacrifice:missed': { you: 20, opp: 11 },
};

export const RAPID_TACTIC_ENTRY = makeTacticTcEntry('rapid', 1841, SKETCH_RAPID_TACTIC_OVERRIDES);
export const BLITZ_TACTIC_ENTRY = makeTacticTcEntry('blitz', 1000, {
  'fork:missed': { you: 30, opp: 12 },
  'fork:allowed': { you: 45, opp: 50 },
});

export function makeTacticComparison(tcs: TacticComparisonTc[]): TacticComparisonResponse {
  return { tcs, analyzed_gate: ANALYZED_GATE };
}
