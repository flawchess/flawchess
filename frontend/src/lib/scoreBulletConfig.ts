/**
 * Score-vs-50% band configuration: the 50% centre and the +/-5-point typical band shared
 * by the Openings score verdicts (openingVerdict) and the Moves-tab score colour.
 */

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';

// Center the bullet on the 50% score baseline.
export const SCORE_BULLET_CENTER = 0.5;

// Neutral zone: +/-5 score points around 0.5, matching the arrow palette's
// score-zone boundaries (neutral grey band = 0.45..0.55).
export const SCORE_BULLET_NEUTRAL_MIN = -0.05;
export const SCORE_BULLET_NEUTRAL_MAX = 0.05;

// Absolute score thresholds for the zone color (mirrors the bullet's
// neutral band: 0.45..0.55 around the 0.5 center).
export const SCORE_NEUTRAL_LOW = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MIN;
export const SCORE_NEUTRAL_HIGH = SCORE_BULLET_CENTER + SCORE_BULLET_NEUTRAL_MAX;

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
