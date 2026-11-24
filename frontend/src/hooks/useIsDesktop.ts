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
import { SHORT_VIEWPORT_QUERY, TRAIN_SIDE_LAYOUT_QUERY } from '@/lib/trainSideLayout';

/** Tailwind's default `lg` breakpoint — kept module-private (not exported;
 * knip flags unused exports) since nothing outside this hook needs the raw
 * number. */
const DESKTOP_BREAKPOINT_PX = 1024;

/** Tailwind's default `sm` breakpoint: where the Train reveal's in-flow action
 * bar takes over from the fixed phone bottom bar. */
const SM_BREAKPOINT_PX = 640;

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

function useMinWidth(minWidthPx: number): boolean {
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

/** True when the Train drills use their side-column layout (1024px and up, or 768px and up in
 * landscape). The JS twin of the `trainside:` CSS variant: both read TRAIN_SIDE_LAYOUT_QUERY,
 * so a drill's JS-mounted branches (height fit, side-column footer, verdict card vs strip)
 * always agree with its CSS split. */
export function useIsTrainSideLayout(): boolean {
  return useMediaQuery(TRAIN_SIDE_LAYOUT_QUERY);
}

/** True in the Train drills' landscape band: the side-column layout is on but the window is
 * narrower than `lg` (a foldable's inner screen or a tablet held sideways, 768-1023px wide).
 * The JS twin of the `trainside:max-lg:` CSS prefix. The screen is short there, so the drills
 * hide the desktop nav header and use the compact floated-avatar bot bubble. */
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
