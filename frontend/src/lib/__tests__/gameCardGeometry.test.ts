import { describe, expect, it } from 'vitest';
import {
  BOARD_SQUARES,
  DESKTOP_BOARD_SIZE,
  DESKTOP_EVAL_CHART_HEIGHT_CLASS,
  DESKTOP_EVAL_CHART_HEIGHT_PX,
  DESKTOP_LANE_GAP_PX,
  DESKTOP_TAGS_CARD_PX,
  EVAL_SLIDER_ROW_PX,
  MOVE_STATS_ACCURACY_STRIP_PX,
  MOVE_STATS_BORDER_PX,
  MOVE_STATS_DESKTOP_HEIGHT_PX,
  MOVE_STATS_ROW_PX,
  MOVE_STATS_TABLE_PADDING_PX,
} from '@/lib/gameCardGeometry';
import { MOVE_STAT_CATEGORY_ORDER } from '@/lib/moveStatsCounts';

describe('gameCardGeometry', () => {
  it('derives the MoveStats height from the chrome plus one row per category', () => {
    const chrome = MOVE_STATS_BORDER_PX + MOVE_STATS_ACCURACY_STRIP_PX + MOVE_STATS_TABLE_PADDING_PX;
    expect(MOVE_STATS_DESKTOP_HEIGHT_PX).toBe(chrome + MOVE_STAT_CATEGORY_ORDER.length * MOVE_STATS_ROW_PX);
    // 8 rows at today's classes.
    expect(MOVE_STATS_DESKTOP_HEIGHT_PX).toBe(247);
  });

  it('sizes the board to whole-pixel squares, at least the table height and less than one square more', () => {
    expect(DESKTOP_BOARD_SIZE % BOARD_SQUARES).toBe(0);
    expect(DESKTOP_BOARD_SIZE).toBeGreaterThanOrEqual(MOVE_STATS_DESKTOP_HEIGHT_PX);
    expect(DESKTOP_BOARD_SIZE).toBeLessThan(MOVE_STATS_DESKTOP_HEIGHT_PX + BOARD_SQUARES);
  });

  it('gives the eval chart the board height left after the slider row, lane gap and tags card', () => {
    expect(DESKTOP_EVAL_CHART_HEIGHT_PX).toBe(
      DESKTOP_BOARD_SIZE - EVAL_SLIDER_ROW_PX - DESKTOP_LANE_GAP_PX - DESKTOP_TAGS_CARD_PX,
    );
  });

  it('pins the literal Tailwind class to the derived chart height', () => {
    expect(DESKTOP_EVAL_CHART_HEIGHT_CLASS).toBe(`h-[${DESKTOP_EVAL_CHART_HEIGHT_PX}px]`);
  });
});
