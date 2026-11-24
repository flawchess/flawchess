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
