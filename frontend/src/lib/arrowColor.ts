// Arrow color utility — maps win percentage to one of three discrete oklch colors.
//
// Colors match the WDL chart (WDLBar.tsx):
//   green = oklch(0.45 0.16 145)   — win rate >= 60%
//   grey  = oklch(0.65 0.01 260)   — win rate 40–60%
//   red   = oklch(0.45 0.17 25)    — win rate <= 40%
//
// Frequency is encoded as arrow thickness (handled by ChessBoard).

const GREEN = 'oklch(0.45 0.16 145)';
const GREY = 'oklch(0.65 0.01 260)';
const RED = 'oklch(0.45 0.17 25)';

// Hovered arrows use boosted lightness for visibility
const GREEN_HOVER = 'oklch(0.6 0.16 145)';
const GREY_HOVER = 'oklch(0.8 0.01 260)';
const RED_HOVER = 'oklch(0.6 0.17 25)';

const MIN_GAMES_FOR_COLOR = 10;

/**
 * Returns an oklch CSS color string for a board arrow.
 *
 * @param winPct    Win percentage, 0–100
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, gameCount: number, isHovered: boolean): string {
  if (gameCount < MIN_GAMES_FOR_COLOR) return isHovered ? GREY_HOVER : GREY;
  if (winPct >= 60) return isHovered ? GREEN_HOVER : GREEN;
  if (winPct <= 40) return isHovered ? RED_HOVER : RED;
  return isHovered ? GREY_HOVER : GREY;
}
