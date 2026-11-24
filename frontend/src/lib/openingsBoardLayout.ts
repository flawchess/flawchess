import type { OpeningsTab } from '@/types/openingsTab';

/**
 * Board container layout helpers for the Openings page.
 *
 * Extracted to a standalone module so the react-refresh ESLint rule is
 * satisfied (component files may only export components) and so the logic
 * is directly unit-testable without rendering the full Openings page.
 */

/**
 * Returns the className for the desktop board container.
 * On the Stats subtab, lg:hidden hides the board to free horizontal space
 * (Stats uses the full content width for the findings and opening cards).
 * The ChessBoard JSX element is NOT removed so chess.js state is preserved
 * across tab switches.
 */
export function getBoardContainerClassName(activeTab: OpeningsTab): string {
  const hideOnLg = activeTab === 'stats';
  return `flex flex-col gap-2 w-[400px] shrink-0${hideOnLg ? ' lg:hidden' : ''}`;
}

/*
 * Landscape side layout of the phone branch (`lg:hidden`).
 *
 * Below lg the Openings page renders its phone branch at any orientation. In portrait it is
 * one column (subnav, board, opening name, move list, tab content). In landscape (640-1023px
 * wide, width greater than height: unfolded foldables such as the Galaxy Z Fold8 at 941x710
 * or 816x616, phones held sideways at 852x393 or 667x375) that column left the right half of
 * the screen empty and pushed the move list, games and stats below the fold. There the board
 * now sits in a height-fitted column on the left and everything else in a column on the right.
 *
 * The gate is the `trainside:` variant (TRAIN_SIDE_LAYOUT_QUERY in lib/trainSideLayout.ts), so
 * Openings switches at the same point as the Train drills. Inside the `lg:hidden` branch it
 * only ever matches that landscape band, so the classes below need no `max-lg:` guard.
 */

/** The board column's height fit never grows the board past this (unreachable below lg). */
export const OPENINGS_SIDE_BOARD_MAX_PX = 720;
/** Nor shrinks it below this; under it the page scrolls instead. */
export const OPENINGS_SIDE_BOARD_MIN_PX = 200;
/** Portrait keeps the board's own cap (the ChessBoard default and the desktop board width). */
export const OPENINGS_STACKED_BOARD_MAX_PX = 400;
/** Height of the phone frame's fixed bottom tab bar (App.tsx MobileBottomBar, `main` pb-16). */
const PHONE_BOTTOM_BAR_PX = 64;
/** Space between the board controls and the top of the bottom tab bar. */
const SIDE_BOARD_BOTTOM_GAP_PX = 8;
/** The height fit's bottom gutter: the board controls end just above the bottom tab bar. */
export const OPENINGS_SIDE_BOARD_GUTTER_PX = PHONE_BOTTOM_BAR_PX + SIDE_BOARD_BOTTOM_GAP_PX;
/** Width the board row adds beside the board: the 44px settings column (w-11), the 4px gap
 * (gap-1) and the row's 4px padding on each side (px-1). The board column's width is the fitted board
 * plus this. */
export const OPENINGS_BOARD_ROW_CHROME_PX = 56;

/** The row holding the board column and the content column: stacked in portrait, side by side
 * in landscape. Its portrait gap matches the Tabs column it replaced, so portrait is unchanged. */
export const OPENINGS_MOBILE_ROW_CLASS =
  'flex min-w-0 flex-col gap-2 trainside:flex-row trainside:items-start trainside:gap-4';

/** The board column: the board and its controls, with the settings column beside them. In
 * landscape it pins to the top while the content column scrolls, and `min-w-0` lets it shrink
 * below its fitted width, so the content column keeps its floor on near-square screens
 * (820x791) instead of overflowing the row. */
export const OPENINGS_MOBILE_BOARD_COLUMN_CLASS =
  'flex min-w-0 items-stretch gap-1 px-1 trainside:sticky trainside:top-2';

/** The content column (subnav, Stats row, opening name, move list, tab content). In portrait it
 * is `contents`, so its children stay in the stacked flow. In landscape it takes the width the
 * board leaves (`flex-1 basis-0`), with a 40% floor of the row so the move table and game cards
 * stay readable when the board is height-bound on a near-square or narrow screen. */
export const OPENINGS_MOBILE_CONTENT_COLUMN_CLASS =
  'contents trainside:flex trainside:min-w-[40%] trainside:flex-1 trainside:basis-0 trainside:flex-col trainside:gap-2';

/** The subnav and the Stats sticky row sit in the content column after the board column in the
 * DOM. In portrait (content column `contents`) they move back above the board with `order`. */
export const OPENINGS_MOBILE_TOP_ROW_ORDER_CLASS = 'order-first trainside:order-none';
