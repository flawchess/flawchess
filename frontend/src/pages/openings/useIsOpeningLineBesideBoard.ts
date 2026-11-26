import { useIsTrainSideLayout, useMinWidth } from '@/hooks/useIsDesktop';

/** Narrowest portrait screen with the opening line beside the board: the Fold8 inner screen
 * with a larger display zoom (616px) still leaves a 344px board next to the 180px column; the
 * cover screen (475px) would not. */
const OPENING_LINE_BESIDE_BOARD_MIN_PX = 600;

/**
 * True on portrait screens from 600px below the side layout: an unfolded foldable (704x845,
 * 616x728 zoomed) or a portrait tablet (820x1180). The board keeps its 400px cap there, which
 * left a third of the row empty and pushed the move table below the fold; the opening line now
 * fills that space beside the board, so the table starts about 100px higher. Landscape and `lg`
 * use the side layout (`trainside`), phones keep the stacked line.
 */
export function useIsOpeningLineBesideBoard(): boolean {
  const isWideEnough = useMinWidth(OPENING_LINE_BESIDE_BOARD_MIN_PX);
  const isSideLayout = useIsTrainSideLayout();
  return isWideEnough && !isSideLayout;
}
