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
// Hovered arrows turn blue to stand out from the WDL color scheme.
//
// Frequency is encoded as arrow thickness (handled by ChessBoard).

export const MIN_GAMES_FOR_COLOR = 10;

// Score-based thresholds (Phase 75; consumed by Phase 76 once getArrowColor
// body migrates to score-based coloring). MIN_GAMES_FOR_COLOR is already 10
// in this file — leave it as-is; the CI consistency test now asserts it
// matches OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE.
export const SCORE_PIVOT = 0.50;
export const MINOR_EFFECT_SCORE = 0.05;
export const MAJOR_EFFECT_SCORE = 0.10;

// Win/loss rate thresholds for categorical color buckets
const LIGHT_COLOR_THRESHOLD = 55; // > 55% triggers light green/red
const DARK_COLOR_THRESHOLD = 60;  // >= 60% triggers dark green/red

// Categorical color constants — hex strings for direct equality checks
export const GREY = '#B0B0B0';
export const LIGHT_GREEN = '#6BBF59';
export const DARK_GREEN = '#1E6B1E';
export const LIGHT_RED = '#E07070';
export const DARK_RED = '#9B1C1C';

// Hovered arrow color — blue stands out from the green/grey/red WDL palette
export const HOVER_BLUE = '#3B82F6';

/**
 * Returns a categorical hex color string for a board arrow.
 *
 * @param winPct    Win percentage, 0–100
 * @param lossPct   Loss percentage, 0–100
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, lossPct: number, gameCount: number, isHovered: boolean): string {
  // Hovered arrows always turn blue to pop out from the WDL color scheme
  if (isHovered) return HOVER_BLUE;

  // Below minimum game threshold — always grey
  if (gameCount < MIN_GAMES_FOR_COLOR) return GREY;

  // Determine if win or loss rate qualifies for coloring.
  // When both exceed the threshold, the higher rate wins.
  // If equal, green (win) takes precedence (winPct >= lossPct).
  const winColored = winPct > LIGHT_COLOR_THRESHOLD;
  const lossColored = lossPct > LIGHT_COLOR_THRESHOLD;

  if (winColored && (!lossColored || winPct >= lossPct)) {
    return winPct >= DARK_COLOR_THRESHOLD ? DARK_GREEN : LIGHT_GREEN;
  }

  if (lossColored) {
    return lossPct >= DARK_COLOR_THRESHOLD ? DARK_RED : LIGHT_RED;
  }

  return GREY;
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering order.
 * Hovered (blue) → -1 (always on top), green → 0, red → 1, grey → 2 (drawn first = bottom).
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
