/**
 * Score-domain bullet chart configuration. Used by the current-position
 * score-vs-50% bullet on the Openings Moves tab. Domain matches the
 * MoveExplorer Conf-column visual scale.
 */

// Center the bullet on the 50% score baseline.
export const SCORE_BULLET_CENTER = 0.5;

// Neutral zone: +/-5 score points around 0.5, matching MoveExplorer's
// MINOR_EFFECT_SCORE threshold for "no meaningful edge".
export const SCORE_BULLET_NEUTRAL_MIN = -0.05;
export const SCORE_BULLET_NEUTRAL_MAX = 0.05;

// Axis half-width: spans 0.30-0.70 around center, matching the visual
// range used elsewhere in the move explorer.
export const SCORE_BULLET_DOMAIN = 0.2;

/** Clamp a score-domain value (or CI bound) to the valid [0, 1] range. */
export function clampScoreCi(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}
