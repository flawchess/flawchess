/**
 * Shared gate for the Train drills' side-column layout (blunder check, personalized puzzles).
 *
 * The side layout: the board column on the left (board height-fitted to the viewport, game
 * info under it), the bot bubble / solution / reveal in a right column. Below the gate the
 * drills stack with a sticky pinned board.
 *
 * The gate is "1024px and up, or 768px and up in landscape" (width greater than height). The
 * landscape band covers an unfolded Galaxy Z Fold8 (816x616, 933x704) where the stacked
 * layout used to overflow the viewport. `index.css`'s `trainside` custom variant MUST read
 * this exact query, and `lib/__tests__/trainSideLayout.test.ts` enforces it. The JS twin is
 * `useIsTrainSideLayout` in `hooks/useIsDesktop.ts`.
 *
 * These constants live here, not in `hooks/useIsDesktop.ts`, on purpose: two test files mock
 * that module wholesale with a factory, and a missing export of a factory mock throws.
 */

/** Tailwind's default `lg` breakpoint: the side layout applies at any orientation from here. */
const SIDE_LAYOUT_ANY_ORIENTATION_MIN_PX = 1024;
/** Tailwind's default `md` breakpoint: the side layout applies from here in landscape only. */
const SIDE_LAYOUT_LANDSCAPE_MIN_PX = 768;

/** The one media query behind both the `trainside:` CSS variant and `useIsTrainSideLayout`. */
export const TRAIN_SIDE_LAYOUT_QUERY = `(min-width: ${SIDE_LAYOUT_ANY_ORIENTATION_MIN_PX}px), (min-width: ${SIDE_LAYOUT_LANDSCAPE_MIN_PX}px) and (orientation: landscape)`;

/**
 * Width cap of the side column. Desktop (lg and up) keeps its 384px column; the 768-1023px
 * landscape band caps it at 272px. The band's 4:3-ish screens are width-bound: at 816x616 the
 * page content is 768px wide, so the board gets what the side column and gap leave. With the
 * compact floated-avatar bot bubble (useIsTrainSideBand) a 272px column reads fine, and with
 * TRAIN_SIDE_ROW_GAP_CLASS's 16px gap the board is about 452px there instead of 388px.
 *
 * The two conditions are disjoint on purpose: custom-variant utilities are emitted after the
 * built-in breakpoints, so pairing a plain `trainside:max-w-68` with `lg:max-w-sm` would let
 * the band value override desktop.
 */
export const TRAIN_SIDE_COLUMN_WIDTH_CLASS = 'lg:max-w-sm trainside:max-lg:max-w-68';

/** Gap between the board column and the side column: 32px on desktop, 16px in the landscape
 * band, where every pixel of the short, narrow screen goes to the board. Disjoint conditions,
 * for the same cascade-order reason as TRAIN_SIDE_COLUMN_WIDTH_CLASS. */
export const TRAIN_SIDE_ROW_GAP_CLASS = 'lg:gap-8 trainside:max-lg:gap-4';

/** A short viewport: the same query as `index.css`'s `short` custom variant (below 560px tall,
 * e.g. a phone in landscape at about 393px). The JS twin for the Train drills' height fit. */
export const SHORT_VIEWPORT_QUERY = '(max-height: 559.98px)';

/** Bottom gutter of the Train drills' height fit on a short side-layout screen (a phone in
 * landscape). The default 40px gutter plus the page padding took about a quarter of a 393px
 * screen; this keeps a small gap above the bottom edge and gives the rest to the board. */
export const SHORT_SIDE_BOARD_GUTTER_PX = 12;

/** Short side layout (a phone in landscape): the progress row and the game info move from the
 * board column to the top and foot of the side column, so the board column holds the board
 * alone. The side column's top offset (it top-aligns with the board under the progress row) and
 * the footer's bottom offset (it lines up with the board above the game-info slot) reset. */
export const SHORT_SIDE_TOP_RESET_CLASS = 'trainside:short:mt-0';
export const SHORT_SIDE_FOOTER_RESET_CLASS = 'trainside:short:mb-0';

/**
 * Short side layout: the side column (a reveal's verdict, lines, move list and Analyze / Next)
 * is taller than a phone's landscape height. Bug fix (iPhone 16 landscape, 852x393): the page
 * scrolled about 200px and Next sat below the fold. The column now sits in a frame as tall as
 * the board column and scrolls inside it, with the footer pinned to its bottom edge.
 */
export const SHORT_SIDE_FRAME_CLASS = `relative w-full self-stretch ${TRAIN_SIDE_COLUMN_WIDTH_CLASS}`;
/** The scroller inside SHORT_SIDE_FRAME_CLASS; `short:`-gated so it is inert outside the frame. */
export const SHORT_SIDE_SCROLLER_CLASS =
  'trainside:short:absolute trainside:short:inset-0 trainside:short:overflow-y-auto';
/** The side column's footer (Analyze / Next), pinned to the scroller's bottom edge. */
export const SHORT_SIDE_STICKY_FOOTER_CLASS =
  'trainside:short:sticky trainside:short:bottom-0 trainside:short:z-10 trainside:short:bg-background trainside:short:pt-2';
