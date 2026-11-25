/**
 * useIsDesktop: shared `matchMedia`-based gates. `useIsDesktop` sits at Tailwind's own
 * default `lg` breakpoint (1024px) instead of a page-specific value, so this JS gate always
 * agrees with a caller's `lg:` CSS split. Its remaining Train user is
 * `TrainFlawFixedBanner.tsx` (thumb size only).
 *
 * `useIsTrainSideLayout` is the gate of the Train drills' side-column layout (see
 * `lib/trainSideLayout.ts`); `TrainSolveScreen`, `TrainReveal`, `TrainMoveTreeList` and the
 * blunder-check stage use it to decide whether the legend spotlight is driven by whole-card
 * hover (side layout) or glyph tap (stacked layout), and which layout-dependent branches mount.
 */
import { useEffect, useState } from 'react';
import {
  BAND_BAR_BOARD_GUTTER_PX,
  PORTRAIT_FOLDABLE_QUERY,
  SHORT_SIDE_BOARD_GUTTER_PX,
  SHORT_VIEWPORT_QUERY,
  TRAIN_BAND_BAR_MIN_HEIGHT_PX,
  TRAIN_SIDE_LAYOUT_QUERY,
} from '@/lib/trainSideLayout';

/** Tailwind's default `lg` breakpoint — kept module-private (not exported;
 * knip flags unused exports) since nothing outside this hook needs the raw
 * number. */
const DESKTOP_BREAKPOINT_PX = 1024;

/** Tailwind's default `sm` breakpoint: where the Train reveal's in-flow action
 * bar takes over from the fixed phone bottom bar. */
const SM_BREAKPOINT_PX = 640;

/** Keeps a `max-height` query exclusive at fractional viewport heights (as in `559.98px`). */
const SUBPIXEL_PX = 0.02;

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia(query);
    const update = () => setMatches(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, [query]);

  return matches;
}

/** True from `minWidthPx` up, for a JS gate that mirrors a `min-[...px]:` CSS split. */
export function useMinWidth(minWidthPx: number): boolean {
  return useMediaQuery(`(min-width: ${minWidthPx}px)`);
}

export function useIsDesktop(): boolean {
  return useMinWidth(DESKTOP_BREAKPOINT_PX);
}

/** True from Tailwind's `sm` (640px) up, so a JS gate always agrees with a
 * caller's `sm:` CSS split (e.g. mounting exactly one of the in-flow vs fixed
 * phone Train reveal action bar instead of CSS-hiding the other copy). */
export function useIsSmUp(): boolean {
  return useMinWidth(SM_BREAKPOINT_PX);
}

/** True when the viewport is shorter than `heightPx`. Asked as "too short", not "tall enough",
 * so an environment without `matchMedia` reads as a normal screen. */
export function useIsShorterThan(heightPx: number): boolean {
  return useMediaQuery(`(max-height: ${heightPx - SUBPIXEL_PX}px)`);
}

/** True when the Train drills use their side-column layout (1024px and up, or 640px and up in
 * landscape). The JS twin of the `trainside:` CSS variant: both read TRAIN_SIDE_LAYOUT_QUERY,
 * so a drill's JS-mounted branches (height fit, side-column footer, verdict card vs strip)
 * always agree with its CSS split. */
export function useIsTrainSideLayout(): boolean {
  return useMediaQuery(TRAIN_SIDE_LAYOUT_QUERY);
}

/** True in the Train drills' landscape band: the side-column layout is on but the window is
 * narrower than `lg` (a foldable's inner screen or a tablet held sideways, 640-1023px wide).
 * The JS twin of the `trainside:max-lg:` CSS prefix. The side column is narrow there, so the
 * drills use the compact floated-avatar bot bubble. */
export function useIsTrainSideBand(): boolean {
  const isSideLayout = useIsTrainSideLayout();
  const isDesktop = useIsDesktop();
  return isSideLayout && !isDesktop;
}

/** True when the Train drills use their side layout on a short screen (below 560px tall: a
 * phone in landscape). The JS twin of `trainside:short:`. The drills shrink the height fit's
 * bottom gutter there so the board gets the height. */
export function useIsTrainShortSide(): boolean {
  const isSideLayout = useIsTrainSideLayout();
  const isShort = useMediaQuery(SHORT_VIEWPORT_QUERY);
  return isSideLayout && isShort;
}

/** True when the Train solutions put their actions into the app's bottom bar although the side
 * layout is on: the landscape band (below lg), except phones held sideways, which are too short
 * for it. The stacked layout always uses the bottom bar. */
export function useIsTrainBandBar(): boolean {
  const isSideBand = useIsTrainSideBand();
  const isTooShort = useIsShorterThan(TRAIN_BAND_BAR_MIN_HEIGHT_PX);
  return isSideBand && !isTooShort;
}

/** The bottom gutter of the Train drills' height fit (`useFitBoardToViewport`), given the
 * drill's own default. */
export function useTrainBoardGutter(defaultPx: number): number {
  const isBandBar = useIsTrainBandBar();
  const isShortSide = useIsTrainShortSide();
  if (isBandBar) return BAND_BAR_BOARD_GUTTER_PX;
  return isShortSide ? SHORT_SIDE_BOARD_GUTTER_PX : defaultPx;
}

/** True on a portrait foldable or small tablet (640-767px wide, portrait), which reads like a
 * phone: the Train bot bubble uses its compact layout there. */
export function useIsPortraitFoldable(): boolean {
  return useMediaQuery(PORTRAIT_FOLDABLE_QUERY);
}
