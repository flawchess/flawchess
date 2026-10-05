/**
 * visibleStopwatch.ts — pure visible-time accumulator (Phase 233 D-04).
 *
 * Counts only the time the tab is visible; hidden spans accumulate separately.
 * No DOM and no React: `now` is injected (the hook passes `Date.now()`, the
 * same fake-timer-friendly clock useBotGameClock uses). Never persist or
 * compare `performance.now()` values across reloads.
 */

export interface StopwatchTotals {
  visibleMs: number;
  hiddenMs: number;
}

/**
 * Folded totals plus exactly one running span: `visibleSince` (tab visible) or
 * `hiddenSince` (tab hidden); the other is null.
 */
export interface VisibleStopwatch extends StopwatchTotals {
  visibleSince: number | null;
  hiddenSince: number | null;
}

/**
 * Starting while hidden opens a hidden span (the useBotGameClock CR-01 rule:
 * seed the pause from the INITIAL visibility, since `visibilitychange` fires
 * only on a transition).
 */
export function startStopwatch(now: number, hidden: boolean, seed?: StopwatchTotals): VisibleStopwatch {
  return {
    visibleMs: seed?.visibleMs ?? 0,
    hiddenMs: seed?.hiddenMs ?? 0,
    visibleSince: hidden ? null : now,
    hiddenSince: hidden ? now : null,
  };
}

/**
 * Fold the running span into its total and open the other kind. A call that
 * matches the current state returns the stopwatch unchanged: Safari fires a
 * duplicate 'hidden' alongside pagehide and again on bfcache restore, and a
 * duplicate must never re-baseline a span (that would drop the interval).
 */
export function applyVisibility(sw: VisibleStopwatch, hidden: boolean, now: number): VisibleStopwatch {
  const currentlyHidden = sw.hiddenSince !== null;
  if (currentlyHidden === hidden) return sw;
  const folded = readStopwatch(sw, now);
  return {
    visibleMs: folded.visibleMs,
    hiddenMs: folded.hiddenMs,
    visibleSince: hidden ? null : now,
    hiddenSince: hidden ? now : null,
  };
}

/** Folded totals plus the running span, without mutating the stopwatch. */
export function readStopwatch(sw: VisibleStopwatch, now: number): StopwatchTotals {
  const runningVisible = sw.visibleSince === null ? 0 : Math.max(0, now - sw.visibleSince);
  const runningHidden = sw.hiddenSince === null ? 0 : Math.max(0, now - sw.hiddenSince);
  return { visibleMs: sw.visibleMs + runningVisible, hiddenMs: sw.hiddenMs + runningHidden };
}
