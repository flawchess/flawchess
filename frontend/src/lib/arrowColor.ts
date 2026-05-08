// Arrow color utility — maps chess score to a 3-category palette for board
// arrows on the Openings → Moves tab.
//
// Categories:
//   reliable + score >= 0.55           → DARK_GREEN (advantage)
//   reliable + score <= 0.45           → DARK_RED   (disadvantage)
//   everything else                    → DARK_BLUE
//     ↳ "everything else" includes the in-between band (0.45..0.55) AND
//       low-data rows (gameCount < MIN_GAMES_FOR_COLOR) AND low-confidence
//       rows. The board renders these grey arrows at a much lower opacity
//       (see ARROW_LOW_EMPHASIS_OPACITY in ChessBoard.tsx) so reliable
//       red/green moves dominate visually.
//
// Hover does NOT change arrow color — the board increases size + opacity
// instead. Sorting hovered arrows on top happens in ChessBoard.tsx via a
// separate isHovered-first comparator, not via this color value.
//
import { ARROW_NEUTRAL } from '@/lib/theme';

export const MIN_GAMES_FOR_COLOR = 10;

// Score-based thresholds. MIN_GAMES_FOR_COLOR is 10 — intentionally lower
// than the Insights tab's OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE (20). The
// explorer arrow palette can tolerate weaker evidence; a surfaced "weakness"
// card on the Insights tab cannot.
export const SCORE_PIVOT = 0.50;
export const SCORE_BOUNDARY = 0.05;  // boundaries: >=0.55 / <=0.45

// Categorical color constants — hex strings for direct equality checks.
export const DARK_GREEN = '#1E6B1E';
export const DARK_RED = '#9B1C1C';
// Historically blue; now grey via ARROW_NEUTRAL — categorical equality preserved.
// (Renaming would touch every `=== DARK_BLUE` call site; out of scope for now.)
export const DARK_BLUE = ARROW_NEUTRAL;

/**
 * Returns a categorical hex color string for a board arrow / row tint based on
 * chess score (W + 0.5*D)/N.
 *
 * @param score      Score in [0, 1]. The pivot is 0.50 (break-even).
 * @param gameCount  Absolute game count for this move. Below MIN_GAMES_FOR_COLOR
 *                   (10) the function returns DARK_BLUE — the board renders
 *                   blue arrows at low opacity to fade them into the background.
 * @param confidence Statistical confidence ('low' | 'medium' | 'high'). 'low'
 *                   collapses to DARK_BLUE — the effect could plausibly be
 *                   chance, so we don't encode it as a strength/weakness.
 */
export function getArrowColor(
  score: number,
  gameCount: number,
  confidence: 'low' | 'medium' | 'high',
): string {
  if (gameCount < MIN_GAMES_FOR_COLOR || confidence === 'low') return DARK_BLUE;
  if (score >= SCORE_PIVOT + SCORE_BOUNDARY) return DARK_GREEN;  // >= 0.55
  if (score <= SCORE_PIVOT - SCORE_BOUNDARY) return DARK_RED;    // <= 0.45
  return DARK_BLUE;                                              // 0.45..0.55
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering
 * order. Within the score-coded set: green > red > blue. Hovered arrows are
 * sorted on top by a separate isHovered-first comparator in ChessBoard.tsx.
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
