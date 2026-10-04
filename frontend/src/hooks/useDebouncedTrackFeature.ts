import { useCallback, useEffect, useRef } from 'react';
import { trackFeature, type FeatureEventMap, type FeatureEventName } from '@/lib/analytics';

/**
 * Trailing-debounce window for slider commit tracking. Radix Slider fires
 * `onValueCommit` on every keyboard step as well as on pointer-up, and the Play
 * style slider has step 0.01, so a held arrow key sent 60+ events at 50-150 ms
 * intervals in a single prod session. One adjustment burst now sends one event.
 */
export const SLIDER_TRACK_DEBOUNCE_MS = 1000;

interface PendingTrack<E extends FeatureEventName> {
  props: FeatureEventMap[E];
  /** Pathname when the user acted, so a send after navigation is attributed correctly. */
  pathname: string;
}

/**
 * Trailing-debounced `trackFeature` for slider `onValueCommit` handlers ONLY.
 * Never debounce `onValueChange`: it drives the engines and must stay synchronous.
 *
 * The returned scheduler replaces any pending event, so a burst sends exactly one
 * event carrying the LAST props, `delayMs` after the last call. Unmounting with an
 * event still pending sends it immediately (attributed to the page where the user
 * acted, and subject to that page's D-14 exclusion) instead of dropping it. An
 * event still pending when the tab is closed is lost (no pagehide flush).
 *
 * State lives in refs, so scheduling never re-renders the slider.
 */
export function useDebouncedTrackFeature<E extends FeatureEventName>(
  name: E,
  delayMs: number = SLIDER_TRACK_DEBOUNCE_MS,
): (props: FeatureEventMap[E]) => void {
  const pendingRef = useRef<PendingTrack<E> | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback((): void => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const record = pendingRef.current;
    if (record === null) return;
    pendingRef.current = null;
    trackFeature(name, record.props, record.pathname);
  }, [name]);

  const schedule = useCallback(
    (props: FeatureEventMap[E]): void => {
      pendingRef.current = { props, pathname: window.location.pathname };
      if (timerRef.current !== null) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(flush, delayMs);
    },
    [flush, delayMs],
  );

  // Unmount sends the last value instead of dropping it. StrictMode's simulated
  // unmount at mount is a no-op because nothing is pending yet.
  useEffect(() => () => flush(), [flush]);

  return schedule;
}
