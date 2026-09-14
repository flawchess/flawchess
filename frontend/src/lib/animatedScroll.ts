/**
 * animatedScroll — a tunable-duration rAF scroll tween.
 *
 * WHY: the browser's native `scrollBy`/`scrollTo({ behavior: 'smooth' })` has
 * no duration knob — its timing is entirely UA-owned (Chrome runs it at
 * roughly 300-400ms for a few-hundred-pixel delta, with no way to tune it).
 * Quick task 260914-uer (QUICK-03) asked to slow down the Train walkthrough's
 * step-1 scroll-into-view, which requires an explicit, tunable animation
 * instead. This module is that single tween; the one caller today is
 * `useTrainWalkthrough.ts`'s `WALKTHROUGH_CARD_SCROLL_DURATION_MS`.
 */

/** Ease-in-out cubic — accelerates then decelerates, approximating the native
 * "smooth" feel this module replaces. */
function easeInOutCubic(progress: number): number {
  if (progress < 0.5) return 4 * progress * progress * progress;
  return 1 - Math.pow(-2 * progress + 2, 3) / 2;
}

/**
 * Animates `element.scrollTop` from its current value to `start + deltaPx`.
 *
 * - `deltaPx === 0` is a no-op (nothing to move).
 * - `durationMs <= 0` writes the destination in a single step. Callers pass
 *   `0` for the reduced-motion path — this module never reads a media query
 *   itself, that decision belongs to the caller.
 * - Otherwise walks `scrollTop` across successive `requestAnimationFrame`
 *   ticks and assigns the EXACT `start + deltaPx` on the final tick, so
 *   floating-point easing residue never leaves the scroll a pixel short.
 * - Falls back to the single-step write if `requestAnimationFrame` is not a
 *   function (keeps the module safe under any test/runtime environment).
 */
export function animateScrollTop(element: HTMLElement, deltaPx: number, durationMs: number): void {
  if (deltaPx === 0) return;
  const start = element.scrollTop;
  const destination = start + deltaPx;
  if (durationMs <= 0 || typeof requestAnimationFrame !== 'function') {
    element.scrollTop = destination;
    return;
  }

  const startTime = performance.now();
  const tick = (now: number): void => {
    const progress = Math.min(1, (now - startTime) / durationMs);
    element.scrollTop = progress === 1 ? destination : start + deltaPx * easeInOutCubic(progress);
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
