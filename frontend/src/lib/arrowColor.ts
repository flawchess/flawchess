// Arrow color utility — maps chess score to a 3-category palette for board
// arrows and row tints on the Openings → Moves tab.
//
// Categories (Phase 242 D-35: the same rule as the "Results played as" panel and the
// Stats cards, via openingVerdict: 95% confidence, 20+ games, outside the +/-5-point band):
//   verdict 'better'  → DARK_GREEN (advantage)
//   verdict 'worse'   → DARK_RED   (disadvantage)
//   everything else   → NEUTRAL_ARROW_COLOR
//     ↳ "everything else" includes the typical band (45..55%), rows under 20 games and
//       low-confidence rows. The board renders these grey arrows at a much lower opacity
//       (see ARROW_LOW_EMPHASIS_OPACITY in ChessBoard.tsx) so reliable
//       red/green moves dominate visually.
//
// Hover does NOT change arrow color — the board increases size + opacity
// instead. Sorting hovered arrows on top happens in ChessBoard.tsx via a
// separate isHovered-first comparator, not via this color value.
//
import { openingVerdict, SCORE_VERDICT_BAND, scoreDelta } from '@/lib/openingVerdict';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import { ARROW_NEUTRAL } from '@/lib/theme';

// Categorical color constants — hex strings for direct equality checks.
export const DARK_GREEN = '#1E6B1E';
export const DARK_RED = '#9B1C1C';
export const NEUTRAL_ARROW_COLOR = ARROW_NEUTRAL;

/**
 * Returns a categorical hex color string for a board arrow / row tint based on
 * chess score (W + 0.5*D)/N.
 *
 * @param score      Score in [0, 1]. The pivot is 0.50 (break-even).
 * @param gameCount  Absolute game count for this move. Under REPERTOIRE_MIN_GAMES_FOR_VERDICT
 *                   (20) the function returns NEUTRAL_ARROW_COLOR.
 * @param confidence Statistical confidence of the score against 50%. 'low' collapses to
 *                   NEUTRAL_ARROW_COLOR: the effect could plausibly be chance.
 */
export function getArrowColor(score: number, gameCount: number, confidence: ConfidenceLevel): string {
  const verdict = openingVerdict({
    delta: scoreDelta(score),
    band: SCORE_VERDICT_BAND,
    confidence,
    games: gameCount,
  });
  if (verdict === 'better') return DARK_GREEN;
  if (verdict === 'worse') return DARK_RED;
  return NEUTRAL_ARROW_COLOR;
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering
 * order. Within the score-coded set: green > red > grey. Hovered arrows are
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
    case NEUTRAL_ARROW_COLOR:
      return 2;
    default:
      return 3;
  }
}
