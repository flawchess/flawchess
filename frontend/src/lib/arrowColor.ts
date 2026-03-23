// Arrow color utility — maps WDL percentages to categorical colors.
//
// Colors are assigned based on clear thresholds:
//   - dark green  (60%+ win rate)
//   - light green (55-60% win rate)
//   - grey        (45-55% — neutral zone)
//   - light red   (loss rate 55-60%, i.e. win rate 40-45%)
//   - dark red    (loss rate 60%+, i.e. win rate below 40%)
//
// Moves with fewer than MIN_GAMES_FOR_COLOR games remain grey regardless of win/loss rate.
// Hover variants are lighter versions of each color.
//
// Frequency is encoded as arrow thickness (handled by ChessBoard).

export const MIN_GAMES_FOR_COLOR = 10;

// Win/loss rate thresholds for categorical color buckets
const LIGHT_COLOR_THRESHOLD = 55; // > 55% triggers light green/red
const DARK_COLOR_THRESHOLD = 60;  // >= 60% triggers dark green/red

// Categorical color constants — hex strings for direct equality checks
export const GREY = '#B0B0B0';
export const GREY_HOVER = '#D8D8D8';

export const LIGHT_GREEN = '#6BBF59';
export const LIGHT_GREEN_HOVER = '#9DD490';

export const DARK_GREEN = '#2E8B2E';
export const DARK_GREEN_HOVER = '#5BBF5B';

export const LIGHT_RED = '#E07070';
export const LIGHT_RED_HOVER = '#F0A0A0';

export const DARK_RED = '#C03030';
export const DARK_RED_HOVER = '#E06060';

/**
 * Returns a categorical hex color string for a board arrow.
 *
 * @param winPct    Win percentage, 0–100
 * @param lossPct   Loss percentage, 0–100
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, lossPct: number, gameCount: number, isHovered: boolean): string {
  // Below minimum game threshold — always grey
  if (gameCount < MIN_GAMES_FOR_COLOR) {
    return isHovered ? GREY_HOVER : GREY;
  }

  // Determine if win or loss rate qualifies for coloring.
  // When both exceed the threshold, the higher rate wins.
  // If equal, green (win) takes precedence (winPct >= lossPct).
  const winColored = winPct > LIGHT_COLOR_THRESHOLD;
  const lossColored = lossPct > LIGHT_COLOR_THRESHOLD;

  if (winColored && (!lossColored || winPct >= lossPct)) {
    // Green territory
    if (winPct >= DARK_COLOR_THRESHOLD) {
      return isHovered ? DARK_GREEN_HOVER : DARK_GREEN;
    }
    return isHovered ? LIGHT_GREEN_HOVER : LIGHT_GREEN;
  }

  if (lossColored) {
    // Red territory
    if (lossPct >= DARK_COLOR_THRESHOLD) {
      return isHovered ? DARK_RED_HOVER : DARK_RED;
    }
    return isHovered ? LIGHT_RED_HOVER : LIGHT_RED;
  }

  // Neutral zone
  return isHovered ? GREY_HOVER : GREY;
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering order.
 * Green variants → 0 (drawn last = on top), red variants → 1, grey variants → 2 (drawn first = bottom).
 *
 * Uses simple string equality against the 10 known color constants.
 *
 * @param color hex CSS color string produced by getArrowColor
 */
export function arrowSortKey(color: string): number {
  switch (color) {
    case DARK_GREEN:
    case DARK_GREEN_HOVER:
    case LIGHT_GREEN:
    case LIGHT_GREEN_HOVER:
      return 0;
    case DARK_RED:
    case DARK_RED_HOVER:
    case LIGHT_RED:
    case LIGHT_RED_HOVER:
      return 1;
    default:
      // Grey variants and any unknown colors go to bottom
      return 2;
  }
}
