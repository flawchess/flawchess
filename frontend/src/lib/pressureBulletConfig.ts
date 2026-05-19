/**
 * Pressure Score-Delta bullet chart configuration. Used by EndgameTimePressureCard
 * to render per-(TC, pressure-quintile) score-delta and clock-gap bullets.
 * Domain constants keep the visual scale comparable across the 4-TC grid;
 * wide CIs render with open-ended whiskers when they overflow the axis.
 *
 * Unlike scoreBulletConfig, the neutral band is NOT module-level because it
 * varies per (TC, quintile) — callers look it up from PRESSURE_BIN_SCORE_NEUTRAL_ZONES
 * and pass it directly to pressureDeltaZoneColor.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

/** Center the pressure Score-Delta bullet on 0 (delta = 0 means matches cohort). */
export const PRESSURE_DELTA_CENTER = 0;

/** Axis half-width for the Score-Delta bullet: ±30pp covers real-world score deltas
 *  exceeding ±20pp (CONTEXT §2 A-5, 2026-05-17). The ±0.06 D-02 editorial neutral
 *  cap stays unchanged; the colored side-zones widen, the neutral strip shrinks
 *  visually inside the wider axis. CIs that overflow this window render with
 *  open-ended whiskers.
 */
export const PRESSURE_DELTA_DOMAIN = 0.30;

/** Axis half-width for the Clock Gap bullet: ±30pp covers the p5/p95 production range.
 *  CIs that overflow this window render with open-ended whiskers.
 */
export const CLOCK_GAP_DOMAIN = 0.30;

/** Clamp a delta-domain value (or CI bound) to the safe display range [-1, 1].
 *  Prevents CI whiskers from rendering far outside any visible axis.
 */
export function clampDeltaCi(value: number): number {
  if (value < -1) return -1;
  if (value > 1) return 1;
  return value;
}

// ── Score-Gap line chart Y-axis (post-UAT 88.4) ──────────────────────────────

const Y_BASE_PCT = Math.round(PRESSURE_DELTA_DOMAIN * 100); // 30
const Y_TICK_STEP_PCT = 10;

/** Minimal point shape computeScoreGapYAxis needs (a subset of the chart's
 *  ChartPoint): the plotted delta plus the drawn CI whisker offsets. */
export interface ScoreGapAxisPoint {
  delta: number;
  /** [downward_offset, upward_offset] — already clamped upstream. */
  ciError?: [number, number];
}

/**
 * Compute the Score-Gap line chart's Y domain + tick array (fraction units).
 * Expands past the ±30% baseline when a datapoint OR its drawn CI whisker
 * would clip, snapping each edge outward to the next 10% step so ticks stay
 * evenly spaced at exactly 10%. 0 is always a tick (the base envelope is
 * symmetric and 10 divides 30). Mirrors EndgameClockDiffOverTimeChart's
 * domain-expansion behavior, extended to also emit the tick array so the
 * added headroom stays labelled.
 */
export function computeScoreGapYAxis(points: ScoreGapAxisPoint[]): {
  domain: [number, number];
  ticks: number[];
} {
  let minPct = -Y_BASE_PCT;
  let maxPct = Y_BASE_PCT;
  for (const p of points) {
    const candidates = [p.delta];
    if (p.ciError) {
      candidates.push(p.delta - p.ciError[0], p.delta + p.ciError[1]);
    }
    for (const v of candidates) {
      // Round to 0.01% to strip float noise before the floor/ceil snap, so a
      // value sitting exactly on ±30% doesn't push the axis to ±40%.
      const pct = Math.round(v * 10000) / 100;
      minPct = Math.min(minPct, pct);
      maxPct = Math.max(maxPct, pct);
    }
  }
  const loPct = Math.floor(minPct / Y_TICK_STEP_PCT) * Y_TICK_STEP_PCT;
  const hiPct = Math.ceil(maxPct / Y_TICK_STEP_PCT) * Y_TICK_STEP_PCT;
  const ticks: number[] = [];
  for (let t = loPct; t <= hiPct; t += Y_TICK_STEP_PCT) {
    ticks.push(t / 100);
  }
  return { domain: [loPct / 100, hiPct / 100], ticks };
}

/** Pick the zone color for a score-delta relative to the per-bin neutral band.
 *  neutralMin and neutralMax come from PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][quintile].
 *  Returns ZONE_SUCCESS when the user outperforms the neutral band,
 *  ZONE_DANGER when the user underperforms, ZONE_NEUTRAL in between.
 */
export function pressureDeltaZoneColor(
  delta: number,
  neutralMin: number,
  neutralMax: number,
): string {
  if (delta >= neutralMax) return ZONE_SUCCESS;
  if (delta <= neutralMin) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
