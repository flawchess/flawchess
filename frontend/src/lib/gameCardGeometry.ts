/**
 * Desktop Library game card geometry. The MoveStats table's natural height at lg
 * sets the miniboard size, so board and table end level; the eval chart takes the
 * rest of the left lane above a fixed-height tags card.
 *
 * The part constants mirror the MoveStats classes at lg (Tailwind text-sm is a 14px
 * font on a 20px line; the 16px/24px mobile bump applies below 640px only). Change a
 * part constant only when the matching class changes or a browser measurement
 * disagrees by a pixel (inline baseline slack is the known risk).
 */

import { MOVE_STAT_CATEGORY_ORDER } from '@/lib/moveStatsCounts';

/** `.charcoal-texture` card border, 1px top and bottom. */
export const MOVE_STATS_BORDER_PX = 2;
/** Accuracy strip: py-0.5 (4) + 32px content (py-1.5 + 20px line) + 1px border-b. */
export const MOVE_STATS_ACCURACY_STRIP_PX = 37;
/** Table container padding: p-2, 8px top and bottom. */
export const MOVE_STATS_TABLE_PADDING_PX = 16;
/** One category row: py-0.5 (4) + the 20px text-sm line / h-5 icon. */
export const MOVE_STATS_ROW_PX = 24;
/** A chessboard is 8 squares wide; a board size divisible by it has whole-pixel squares. */
export const BOARD_SQUARES = 8;

/** MoveStats natural height on desktop: card chrome plus one row per category. */
export const MOVE_STATS_DESKTOP_HEIGHT_PX =
  MOVE_STATS_BORDER_PX +
  MOVE_STATS_ACCURACY_STRIP_PX +
  MOVE_STATS_TABLE_PADDING_PX +
  MOVE_STAT_CATEGORY_ORDER.length * MOVE_STATS_ROW_PX;

/** Desktop miniboard size: the table height rounded up to whole-pixel squares. */
export const DESKTOP_BOARD_SIZE =
  Math.ceil(MOVE_STATS_DESKTOP_HEIGHT_PX / BOARD_SQUARES) * BOARD_SQUARES;

/** Eval chart slider row under the chart (h-4). */
export const EVAL_SLIDER_ROW_PX = 16;
/** Gap between the eval chart block and the tags card in the left lane (gap-2). */
export const DESKTOP_LANE_GAP_PX = 8;
/**
 * Tags card height, kept as it was when the board was 225px: 225 minus the 104px chart,
 * the slider row and the lane gap. The taller board gives its extra height to the chart.
 */
export const DESKTOP_TAGS_CARD_PX = 97;

/** Desktop eval chart height (chart area only, the slider row is separate). */
export const DESKTOP_EVAL_CHART_HEIGHT_PX =
  DESKTOP_BOARD_SIZE - EVAL_SLIDER_ROW_PX - DESKTOP_LANE_GAP_PX - DESKTOP_TAGS_CARD_PX;

/**
 * The same height as a literal Tailwind class: the scanner needs the full class text,
 * so it cannot be built from the number. gameCardGeometry.test.ts pins the two together.
 */
export const DESKTOP_EVAL_CHART_HEIGHT_CLASS = 'h-[127px]';
