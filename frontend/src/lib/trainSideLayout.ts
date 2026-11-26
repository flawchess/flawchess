/**
 * Shared gate for the Train drills' side-column layout (blunder check, personalized puzzles).
 *
 * The side layout: the board column on the left (board height-fitted to the viewport, game
 * info under it), the bot bubble / solution / reveal in a right column. Below the gate the
 * drills stack with a sticky pinned board.
 *
 * The gate is "1024px and up, or 640px and up in landscape" (width greater than height). The
 * landscape band covers unfolded foldables (Galaxy Z Fold8 816x616 / 933x704, near-square
 * inner screens around 820x790) and phones held sideways (iPhone 16 852x393, iPhone SE
 * 667x375), where the stacked layout used to overflow the viewport. `index.css`'s `trainside` custom variant MUST read
 * this exact query, and `lib/__tests__/trainSideLayout.test.ts` enforces it. The JS twin is
 * `useIsTrainSideLayout` in `hooks/useIsDesktop.ts`.
 *
 * The Openings page's phone branch reuses the same gate for its landscape side layout (board
 * left, content right; see `lib/openingsBoardLayout.ts`), so board pages switch at one point.
 *
 * These constants live here, not in `hooks/useIsDesktop.ts`, on purpose: two test files mock
 * that module wholesale with a factory, and a missing export of a factory mock throws.
 */

/** Tailwind's default `lg` breakpoint: the side layout applies at any orientation from here. */
const SIDE_LAYOUT_ANY_ORIENTATION_MIN_PX = 1024;
/** Tailwind's default `sm` breakpoint: the side layout applies from here in landscape only.
 * Bug fix: it was `md` (768px), which left small phones in landscape (iPhone SE 667x375,
 * Galaxy S8 740x360) in the stacked layout, with the board running off the screen. */
const SIDE_LAYOUT_LANDSCAPE_MIN_PX = 640;

/** The one media query behind both the `trainside:` CSS variant and `useIsTrainSideLayout`. */
export const TRAIN_SIDE_LAYOUT_QUERY = `(min-width: ${SIDE_LAYOUT_ANY_ORIENTATION_MIN_PX}px), (min-width: ${SIDE_LAYOUT_LANDSCAPE_MIN_PX}px) and (orientation: landscape)`;

/**
 * Width of the side column. Desktop (lg and up) keeps its 384px column. In the 640-1023px
 * landscape band (and on a phone in landscape) the column takes the width the board leaves:
 * `flex-1 basis-0` with a 392px floor and a 448px cap. Its flex base size is 0, so when the
 * row is too narrow only the board column shrinks to make room for the floor, and when the
 * board is height-bound the column grows into the spare width instead of leaving empty
 * margins. Bug fix (Galaxy Z Fold8 landscape, about 941x710): the fixed 272px column left
 * about 75px empty on each side of the row.
 *
 * The 336px floor fits the solution's three line chips (Move, Best, Game) with a 4-character
 * move such as Rac8 on one line (about 105px each at the phone text size, plus two 8px gaps);
 * a longer move wraps under its eval (TrainLineChips). Bug fix (owner, 2026-11-26): the floor
 * was 272px, and at 816x528 (a 288px column) even Rac8 was cut off. A 392px floor (6-character
 * moves on one line) cost the board too much (816x528 436 to 332px), so it is 336px plus the
 * wrap.
 *
 * The two conditions are disjoint on purpose: custom-variant utilities are emitted after the
 * built-in breakpoints, so a plain `trainside:max-w-md` would override desktop's `lg:max-w-sm`.
 */
export const TRAIN_SIDE_COLUMN_WIDTH_CLASS =
  'lg:max-w-sm trainside:max-lg:max-w-md trainside:max-lg:min-w-84 trainside:max-lg:flex-1 trainside:max-lg:basis-0';

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

/** The shortest landscape-band screen whose Train solutions use the app's bottom bar, as on
 * phones in portrait (`useIsTrainBandBar`), and whose drills keep the bottom tab bar (App.tsx).
 * Between phones held sideways (about 440px at most), where the bar would take a fifth of the
 * board's height, and a foldable with a larger display zoom (816x528 inside the OS bars).
 * Bug fix (owner, 2026-11-26): it was 500px, so a 761x472 window dropped the tab bar although
 * its board was width-bound and left the bar's height empty. */
export const TRAIN_BAND_BAR_MIN_HEIGHT_PX = 450;

/** Bottom gutter of the Train drills' height fit where the solutions use the bottom bar: the bar
 * (71px) plus a 9px gap, less the 28px eval-bar slot, which the fit already leaves free (the board
 * is that much lower than the fitted column is wide). It applies before the solution too, so the
 * board keeps its size when the bar appears. */
export const BAND_BAR_BOARD_GUTTER_PX = 52;

/** Short side layout (a phone in landscape): the progress row and the game info move from the
 * board column to the top and foot of the side column, so the board column holds the board
 * alone. The side column's top offset (it top-aligns with the board under the progress row) and
 * the footer's bottom offset (it lines up with the board above the game-info slot) reset. */
export const SHORT_SIDE_TOP_RESET_CLASS = 'trainside:short:mt-0';
export const SHORT_SIDE_FOOTER_RESET_CLASS = 'trainside:short:mb-0';

/** Marker class of SIDE_SCROLL_FRAME_CLASS; SIDE_SCROLLER_CLASS only engages as its direct child.
 * MUST match the literal in SIDE_SCROLLER_CLASS (Tailwind only sees static class strings). */
const SIDE_SCROLL_FRAME_MARKER = 'train-side-frame';

/**
 * Framed side layout: the side column (a reveal's verdict, lines, move list and Analyze / Next)
 * sits in a frame as tall as the board column and scrolls inside it. Used on short screens and in
 * the landscape band where the solution uses the bottom bar (`useIsTrainFramedSide`).
 * Bug fix (iPhone 16 landscape, 852x393): the page scrolled about 200px and Next sat below the
 * fold. Bug fix (Fold8 landscape, 933x617): a puzzle solution with the "Flaw fixed!" banner made
 * the page 71px taller than the screen, so the board scrolled away under the bottom bar.
 */
export const SIDE_SCROLL_FRAME_CLASS = `${SIDE_SCROLL_FRAME_MARKER} relative w-full self-stretch ${TRAIN_SIDE_COLUMN_WIDTH_CLASS}`;
/** The scroller inside SIDE_SCROLL_FRAME_CLASS. Gated on being the frame's direct child, so it is
 * inert wherever the column is not framed (desktop, portrait). */
export const SIDE_SCROLLER_CLASS =
  '[.train-side-frame>&]:absolute [.train-side-frame>&]:inset-0 [.train-side-frame>&]:overflow-y-auto';
/** The side column's footer (Analyze / Next), pinned to the scroller's bottom edge. */
export const SHORT_SIDE_STICKY_FOOTER_CLASS =
  'trainside:short:sticky trainside:short:bottom-0 trainside:short:z-10 trainside:short:bg-background trainside:short:pt-2';

/** A portrait foldable or small tablet: past `sm` but below `md`, in portrait (the unfolded
 * Galaxy Z Fold8 is about 704px wide). It reads like a phone, so the Train bot bubble uses
 * its compact phone layout there (`useIsPortraitSmBand`). */
export const PORTRAIT_SM_BAND_QUERY = '(min-width: 640px) and (max-width: 767.98px) and (orientation: portrait)';

/**
 * Stacked layout: caps the board row (board plus its 28px eval-bar slot) so the pinned board
 * leaves room for the reveal under it. Bug fix (Galaxy Z Fold8 portrait, 616x816): the board was
 * width-bound alone and the pinned block left about 150px, so the move list and the engine lines
 * were always below the fold. The row shrinks with the screen height down to a 428px floor (a
 * 400px board), which is wider than most phones' board row, so phones keep the full width.
 *
 * The 387px reserve is everything on the reveal except the board row's width-derived height:
 * 415px of chrome (progress row, verdict strip, chips, two-row move list, two Stockfish lines,
 * gaps, bottom bar) less the 28px slot. `svh`, not `dvh`: a collapsing browser toolbar must not
 * resize the board. Only the row is capped: the pinned block keeps its full width, because its
 * background hides the content scrolling under it. Literal class: Tailwind scans the source.
 */
export const STACKED_BOARD_ROW_CAP_CLASS =
  'max-w-[max(428px,calc(100svh-387px))] trainside:max-w-none';
