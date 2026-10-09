/**
 * useIsDesktop — a shared `matchMedia`-based desktop/mobile gate (Phase 200,
 * D-06/D-08/D-09). Promotes the page-local pattern already proven in
 * `Bots.tsx` (`useIsDesktop` there, `DESKTOP_BREAKPOINT_PX = 800`) to a
 * reusable hook, at Tailwind's own default `lg` breakpoint (1024px) instead
 * of a page-specific value — so this JS gate always agrees with a caller's
 * `lg:` CSS split (e.g. `TrainSolveScreen.tsx`'s `lg:flex-row` desktop/mobile
 * layout), never drifting from it under a differently-tuned threshold.
 *
 * Used by `TrainReveal.tsx` to decide whether the legend spotlight is driven
 * by whole-card hover (desktop, D-06) or glyph tap (mobile, D-08).
 */
import { useEffect, useState } from 'react';

/** Tailwind's default `lg` breakpoint — kept module-private (not exported;
 * knip flags unused exports) since nothing outside this hook needs the raw
 * number. */
const DESKTOP_BREAKPOINT_PX = 1024;

/** Tailwind's default `sm` breakpoint: where the Train reveal's in-flow action
 * bar takes over from the fixed phone bottom bar. */
const SM_BREAKPOINT_PX = 640;

function useMinWidth(minWidthPx: number): boolean {
  const query = `(min-width: ${minWidthPx}px)`;
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

export function useIsDesktop(): boolean {
  return useMinWidth(DESKTOP_BREAKPOINT_PX);
}

/** True from Tailwind's `sm` (640px) up, so a JS gate always agrees with a
 * caller's `sm:` CSS split (e.g. mounting exactly one of the in-flow vs fixed
 * phone Train reveal action bar instead of CSS-hiding the other copy). */
export function useIsSmUp(): boolean {
  return useMinWidth(SM_BREAKPOINT_PX);
}
