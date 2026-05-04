// Arrow color utility — maps chess score to categorical hex colors for board
// arrows. Color encodes effect size only (Phase 76 design lock). Confidence
// is surfaced via the Score column tooltip in the Move Explorer, not via
// arrow opacity or dashing.

export const MIN_GAMES_FOR_COLOR = 10;

// Score-based thresholds. MIN_GAMES_FOR_COLOR is 10 — matching
// OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE on the backend.
export const SCORE_PIVOT = 0.50;
export const MINOR_EFFECT_SCORE = 0.05;  // boundaries: >=0.55 / <=0.45
export const MAJOR_EFFECT_SCORE = 0.10;  // boundaries: >=0.60 / <=0.40

// Categorical color constants — hex strings for direct equality checks
export const GREY = '#B0B0B0';
export const LIGHT_GREEN = '#6BBF59';
export const DARK_GREEN = '#1E6B1E';
export const LIGHT_RED = '#E07070';
export const DARK_RED = '#9B1C1C';

// Hovered arrow color — blue stands out from the green/grey/red score palette
export const HOVER_BLUE = '#3B82F6';

/**
 * Returns a categorical hex color string for a board arrow / row tint based on
 * chess score (W + 0.5*D)/N.
 *
 * Strict >= / <= boundaries match the backend classification in
 * app/services/opening_insights_service.py.
 *
 * @param score      Score in [0, 1]. The pivot is 0.50 (break-even).
 * @param gameCount  Absolute game count for this move. Below MIN_GAMES_FOR_COLOR
 *                   (10), the function falls back to GREY (or HOVER_BLUE if
 *                   hovered) — small samples never carry color.
 * @param confidence Statistical confidence ('low' | 'medium' | 'high'). 'low'
 *                   collapses to GREY (or HOVER_BLUE if hovered) — the effect
 *                   could plausibly be chance, so we don't encode it as a
 *                   strength/weakness.
 * @param isHovered  Whether this arrow is currently hovered by the user.
 */
export function getArrowColor(
  score: number,
  gameCount: number,
  confidence: 'low' | 'medium' | 'high',
  isHovered: boolean,
): string {
  if (isHovered) return HOVER_BLUE;
  if (gameCount < MIN_GAMES_FOR_COLOR) return GREY;
  if (confidence === 'low') return GREY;

  // Order matters: dark before light on each side. Strict >= / <= boundaries.
  if (score >= SCORE_PIVOT + MAJOR_EFFECT_SCORE) return DARK_GREEN;   // >= 0.60
  if (score >= SCORE_PIVOT + MINOR_EFFECT_SCORE) return LIGHT_GREEN;  // >= 0.55
  if (score <= SCORE_PIVOT - MAJOR_EFFECT_SCORE) return DARK_RED;     // <= 0.40
  if (score <= SCORE_PIVOT - MINOR_EFFECT_SCORE) return LIGHT_RED;    // <= 0.45
  return GREY;
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering order.
 * Hovered (blue) -> -1 (always on top), green -> 0, red -> 1, grey -> 2 (drawn first = bottom).
 *
 * @param color hex CSS color string produced by getArrowColor
 */
export function arrowSortKey(color: string): number {
  switch (color) {
    case HOVER_BLUE:
      return -1; // Hovered arrow always drawn last = on top
    case DARK_GREEN:
    case LIGHT_GREEN:
      return 0;
    case DARK_RED:
    case LIGHT_RED:
      return 1;
    default:
      return 2;
  }
}
