// Arrow color utility — maps chess score to a 3-category palette for board
// arrows on the Openings → Moves tab. Boundaries match the bullet-chart
// neutral band (0.45 / 0.55) and the backend opening-insights classifier.
//
// Categories:
//   score >= 0.55           → DARK_GREEN (advantage)
//   score <= 0.45           → DARK_RED   (disadvantage)
//   in between (0.45..0.55) → DARK_BLUE  (neutral, but reliable signal)
//   below MIN_GAMES_FOR_COLOR / low confidence / hovered → GREY
//
// LIGHT_GREEN / LIGHT_RED are kept exported because the OpeningFindingCard
// border (Insights tab) still uses them for minor-severity findings — that
// 4-shade severity palette is independent of the board-arrow scheme.

export const MIN_GAMES_FOR_COLOR = 10;

// Score-based threshold. MIN_GAMES_FOR_COLOR is 10 — matching
// OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE on the backend.
export const SCORE_PIVOT = 0.50;
export const SCORE_BOUNDARY = 0.05;  // boundaries: >=0.55 / <=0.45

// Categorical color constants — hex strings for direct equality checks.
export const GREY = '#B0B0B0';
export const DARK_GREEN = '#1E6B1E';
export const DARK_RED = '#9B1C1C';
export const DARK_BLUE = '#1E40AF';

// Insights severity-border palette (OpeningFindingCard). Not used by
// getArrowColor — kept here so the insights card and the score-aware UI
// share one place to look up palette hex.
export const LIGHT_GREEN = '#6BBF59';
export const LIGHT_RED = '#E07070';

/**
 * Returns a categorical hex color string for a board arrow / row tint based on
 * chess score (W + 0.5*D)/N.
 *
 * @param score      Score in [0, 1]. The pivot is 0.50 (break-even).
 * @param gameCount  Absolute game count for this move. Below MIN_GAMES_FOR_COLOR
 *                   (10), the function falls back to GREY.
 * @param confidence Statistical confidence ('low' | 'medium' | 'high'). 'low'
 *                   collapses to GREY — the effect could plausibly be chance.
 * @param isHovered  Whether this arrow is currently hovered by the user.
 *                   Hovered arrows render in GREY (highlight color), drawn on
 *                   top via arrowSortKey.
 */
export function getArrowColor(
  score: number,
  gameCount: number,
  confidence: 'low' | 'medium' | 'high',
  isHovered: boolean,
): string {
  if (isHovered) return GREY;
  if (gameCount < MIN_GAMES_FOR_COLOR) return GREY;
  if (confidence === 'low') return GREY;

  if (score >= SCORE_PIVOT + SCORE_BOUNDARY) return DARK_GREEN;  // >= 0.55
  if (score <= SCORE_PIVOT - SCORE_BOUNDARY) return DARK_RED;    // <= 0.45
  return DARK_BLUE;                                              // 0.45..0.55
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering order.
 * Hovered (grey) is drawn last — keep it on top via a separate isHovered flag in
 * the caller. Within the score-coded set: green > red > blue > grey-by-default.
 *
 * Note: GREY is now ambiguous (low-data OR hovered). Callers that need the
 * hovered arrow on top should sort by isHovered separately rather than relying
 * on color alone.
 *
 * @param color hex CSS color string produced by getArrowColor
 */
export function arrowSortKey(color: string): number {
  switch (color) {
    case DARK_GREEN:
      return 0;
    case DARK_RED:
      return 1;
    case DARK_BLUE:
      return 2;
    default:
      return 3;
  }
}
