/**
 * useFitPaneToViewport — the tallest a scrollable pane can be while still
 * leaving the chrome BELOW it (the fixed mobile bottom bar, page padding, any
 * sibling rows) fully on screen, so the pane scrolls internally instead of
 * the whole page scrolling underneath it.
 *
 * Sibling of `useFitBoardToViewport.ts` (read that file first) — same
 * document-relative, single-pass measurement idiom, applied to a scroll
 * container instead of a board's width.
 *
 * The hook OWNS its ref (`useRef<HTMLDivElement>(null)`) rather than
 * accepting one from the caller: its one consumer, `TrainSolveScreen`, is
 * built against a tight statement budget, so it needs ref + measurement from
 * a single call site (`const feedbackPane = useFitPaneToViewport(...)`).
 *
 * Measurement (this is the load-bearing part, read carefully before
 * changing it):
 *
 *   const rect = pane.getBoundingClientRect();
 *   const paneTop = rect.top + window.scrollY;                                  // document-relative => scroll-invariant
 *   const chromeBelow = document.body.getBoundingClientRect().bottom - rect.bottom; // everything laid out below the pane
 *   const available = document.documentElement.clientHeight - paneTop - chromeBelow - gutterPx;
 *
 * `chromeBelow` is MEASURED, not estimated, because the chrome under the
 * pane differs by breakpoint (`main`'s `pb-16` reserving the fixed mobile
 * bottom bar below `sm`, the page wrapper's `py-6` elsewhere) — the same
 * lesson `useFitBoardToViewport`'s docstring records from the 191 UAT.
 * `chromeBelow` is also invariant under the cap this hook applies: capping
 * the pane's height moves `body`'s bottom edge and the pane's own bottom edge
 * by the SAME amount, so the measurement converges in one pass rather than
 * feeding back on itself. Never substitute `documentElement.scrollHeight`
 * here — it clamps to the viewport once the content fits, which would make
 * the pane shrink by `gutterPx` on every subsequent measurement pass.
 *
 * Initial state is `null` ("no cap yet") so nothing is clipped before the
 * first layout pass has a real pane to measure.
 */
import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

export interface FitPaneToViewportOptions {
  /** Space kept free between the pane's bottom edge and the measured chrome
   * below it. */
  gutterPx: number;
  /** Never caps the pane below this height — below it the page is allowed to
   * scroll again rather than squeezing the pane's content into an unreadable
   * slot. */
  minPx: number;
}

export interface FitPaneToViewport {
  /** Attach to the pane element whose height should be capped. */
  paneRef: RefObject<HTMLDivElement | null>;
  /** `null` until the first layout pass measures a mounted pane; after that,
   * the max-height in px to apply via inline `style`. */
  maxHeightPx: number | null;
}

export function useFitPaneToViewport({ gutterPx, minPx }: FitPaneToViewportOptions): FitPaneToViewport {
  const paneRef = useRef<HTMLDivElement>(null);
  const [maxHeightPx, setMaxHeightPx] = useState<number | null>(null);

  const measure = useCallback(() => {
    const pane = paneRef.current;
    if (pane === null) return;
    const rect = pane.getBoundingClientRect();
    const paneTop = rect.top + window.scrollY;
    const chromeBelow = document.body.getBoundingClientRect().bottom - rect.bottom;
    const available = document.documentElement.clientHeight - paneTop - chromeBelow - gutterPx;
    setMaxHeightPx(Math.round(Math.max(minPx, available)));
  }, [gutterPx, minPx]);

  useLayoutEffect(() => {
    measure();
    const pane = paneRef.current;
    const observed = pane?.parentElement ?? pane;
    const observer = new ResizeObserver(measure);
    if (observed !== null && observed !== undefined) observer.observe(observed);
    window.addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [measure]);

  return { paneRef, maxHeightPx };
}
