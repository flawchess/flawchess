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

/** Axis half-width for the Score-Delta bullet: ±20pp covers the expected ±15pp IQR generously.
 *  CIs that overflow this window render with open-ended whiskers.
 */
export const PRESSURE_DELTA_DOMAIN = 0.20;

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
