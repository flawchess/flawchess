/**
 * Size of the /analysis board in the phone takeover (below 768px wide, board on top, tabs
 * below). The board is square and width-driven, so capping the block's width caps its height.
 *
 * Bug fix (Galaxy Z Fold8 portrait, inside the OS bars): width alone sized the board, so the
 * tab panel got only what was left: 50px on the 475x663 cover screen and 10 to 24px with a
 * larger display zoom, while the Explain bar showed. DevTools presets hid this, because they
 * give the page the OS bars' 88px too.
 */
import { BOARD_EVAL_BARS_ALLOWANCE_PX, BOARD_MAX_WIDTH } from '@/components/board/boardSize';

/** Board ceiling, 80px below the shared BOARD_MAX_WIDTH: a full-size board crowds the tabs. */
const TAKEOVER_BOARD_MAX_PX = BOARD_MAX_WIDTH - 80;
/** Board floor under height pressure (32px squares, still easy to tap). Below it the tab panel
 *  gives way. */
const TAKEOVER_BOARD_MIN_PX = 256;
/** The board block is wider than the board by the two eval bars with their gaps and the
 *  wrapper's `px-2`. Capping the block, not the board, keeps the eval bars and the clocks on
 *  the board's edges. */
const BOARD_BLOCK_EXTRA_PX = BOARD_EVAL_BARS_ALLOWANCE_PX + 16;

/** Height of everything but the board and the tab panel (measured): padding, the source caps
 *  row, the tab strip and its gaps, and the board-controls footer. */
const BASE_CHROME_PX = 151;
/** Added by the two player rows. */
const PLAYER_ROWS_PX = 40;
/** The Explain bar. Reserved even while it is hidden, so the board keeps its size from move to
 *  move. */
const EXPLAIN_BAR_PX = 57;
/** What the tab panel keeps: its 8px padding and a bit over three 28px move rows. */
const TAB_PANEL_MIN_PX = 100;

/** The block's share of the width, which leaves a margin beside the board on phones. */
const BLOCK_WIDTH_SHARE = '92vw';
const SAFE_AREAS = 'env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px)';

export interface TakeoverBoardRows {
  /** Player rows above and below the board (a game or a pasted PGN). */
  hasPlayerRows: boolean;
  /** The Explain bar can show (game mode). */
  hasExplainBar: boolean;
}

/**
 * CSS max-width of the board block. `svh`, not `dvh`: a collapsing browser toolbar must not
 * resize the board.
 */
export function takeoverBoardBlockMaxWidth({ hasPlayerRows, hasExplainBar }: TakeoverBoardRows): string {
  const reserve =
    BASE_CHROME_PX + TAB_PANEL_MIN_PX + (hasPlayerRows ? PLAYER_ROWS_PX : 0) + (hasExplainBar ? EXPLAIN_BAR_PX : 0);
  const ceiling = TAKEOVER_BOARD_MAX_PX + BOARD_BLOCK_EXTRA_PX;
  const floor = TAKEOVER_BOARD_MIN_PX + BOARD_BLOCK_EXTRA_PX;
  const byHeight = `100svh - ${reserve - BOARD_BLOCK_EXTRA_PX}px - ${SAFE_AREAS}`;
  return `min(${BLOCK_WIDTH_SHARE}, ${ceiling}px, max(${floor}px, ${byHeight}))`;
}
