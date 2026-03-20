// Arrow color utility — maps WDL percentages to one of three discrete oklch colors.
//
// Colors match the WDL chart (WDLBar.tsx):
//   green = oklch(0.45 0.16 145)   — win rate >= 60%
//   grey  = oklch(0.55 0.01 260)   — neither threshold met
//   red   = oklch(0.45 0.17 25)    — loss rate >= 60%
//
// Frequency is encoded as arrow thickness (handled by ChessBoard).

const GREEN = 'oklch(0.45 0.16 145)';
const GREY = 'oklch(0.75 0.01 260)';
const RED = 'oklch(0.45 0.17 25)';

// Hovered arrows use boosted lightness for visibility
const GREEN_HOVER = 'oklch(0.6 0.16 145)';
const GREY_HOVER = 'oklch(0.9 0.01 260)';
const RED_HOVER = 'oklch(0.6 0.17 25)';

const MIN_GAMES_FOR_COLOR = 10;
const GREEN_THRESHOLD = 60;
const RED_THRESHOLD = 60;

/**
 * Returns an oklch CSS color string for a board arrow.
 *
 * @param winPct    Win percentage, 0–100
 * @param lossPct   Loss percentage, 0–100
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, lossPct: number, gameCount: number, isHovered: boolean): string {
  if (gameCount < MIN_GAMES_FOR_COLOR) return isHovered ? GREY_HOVER : GREY;
  if (winPct >= GREEN_THRESHOLD) return isHovered ? GREEN_HOVER : GREEN;
  if (lossPct >= RED_THRESHOLD) return isHovered ? RED_HOVER : RED;
  return isHovered ? GREY_HOVER : GREY;
}
