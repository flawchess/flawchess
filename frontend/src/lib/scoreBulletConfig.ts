/**
 * Score-domain bullet chart configuration. Used by the current-position
 * score-vs-50% bullet on the Openings Moves tab. Domain matches the
 * MoveExplorer Conf-column visual scale.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

// Center the bullet on the 50% score baseline.
export const SCORE_BULLET_CENTER = 0.5;

// Neutral zone: +/-5 score points around 0.5, matching the arrow palette's
// score-zone boundaries (DARK_BLUE band = 0.45..0.55).
export const SCORE_BULLET_NEUTRAL_MIN = -0.05;
export const SCORE_BULLET_NEUTRAL_MAX = 0.05;

// Absolute score thresholds for the zone color (mirrors the bullet's
// neutral band: 0.45..0.55 around the 0.5 center).
export const SCORE_NEUTRAL_LOW = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MIN;
export const SCORE_NEUTRAL_HIGH = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MAX;

// Default axis half-width: spans the 30-70% score range around the 0.5 center.
// Tighter than the full 0-100% range so typical CIs read clearly; falls back
// to the wide domain when a CI extends past the [0.3, 0.7] window.
export const SCORE_BULLET_DOMAIN = 0.2;

// Wide axis half-width: spans the full 0-100% range. Used when the CI
// overlaps the default 30-70% boundaries so the whisker stays in view.
export const SCORE_BULLET_DOMAIN_WIDE = 0.5;

/** Pick the bullet chart axis half-width based on whether the 95% CI fits
 * within the default 30-70% window. Returns the wide domain (full 0-100%)
 * if either bound is outside, otherwise the tighter default. */
export function scoreBulletDomain(ciLow: number, ciHigh: number): number {
  const min = SCORE_BULLET_CENTER - SCORE_BULLET_DOMAIN;
  const max = SCORE_BULLET_CENTER + SCORE_BULLET_DOMAIN;
  if (ciLow < min || ciHigh > max) return SCORE_BULLET_DOMAIN_WIDE;
  return SCORE_BULLET_DOMAIN;
}

/** Clamp a score-domain value (or CI bound) to the valid [0, 1] range. */
export function clampScoreCi(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/** Pick the zone color for a score in [0, 1] relative to the 50% baseline.
 * Mirrors evalZoneColor: SUCCESS above the neutral band, DANGER below,
 * NEUTRAL in between. Used for the score-percent text in the Moves tab and
 * the per-row Score column in MoveExplorer.
 */
export function scoreZoneColor(score: number): string {
  if (score >= SCORE_NEUTRAL_HIGH) return ZONE_SUCCESS;
  if (score <= SCORE_NEUTRAL_LOW) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}
