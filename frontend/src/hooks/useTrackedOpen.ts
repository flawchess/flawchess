import { useCallback, useEffect, useRef, useState } from 'react';
import { popoverTargetFromTestId, trackFeature } from '@/lib/analytics';

interface UseTrackedOpenOptions {
  /** Fire at most once for the lifetime of the mounted instance. */
  once?: boolean;
}

/**
 * Open/closed state that calls `onOpen` on a false-to-true transition made by
 * the user (hover timer, tap, keyboard), never on mount (Phase 229 D-03).
 *
 * The callback runs in the setter, outside any state updater: StrictMode
 * double-invokes updaters, which would double-fire a tracking call. The setter
 * is stable across renders so it is safe in dependency arrays.
 */
export function useTrackedOpen(
  onOpen: () => void,
  options: UseTrackedOpenOptions = {},
): readonly [boolean, (next: boolean) => void] {
  const [open, setOpenState] = useState(false);
  const openRef = useRef(false);
  const firedRef = useRef(false);
  const onOpenRef = useRef(onOpen);
  const once = options.once ?? false;

  useEffect(() => {
    onOpenRef.current = onOpen;
  }, [onOpen]);

  const setOpen = useCallback(
    (next: boolean): void => {
      if (next && !openRef.current && !(once && firedRef.current)) {
        firedRef.current = true;
        onOpenRef.current();
      }
      openRef.current = next;
      setOpenState(next);
    },
    [once],
  );

  return [open, setOpen] as const;
}

/**
 * Popover open state that reports `popover-open` once per mounted instance
 * (D-13): hover flicker cannot inflate the count, and it still answers "was
 * this explanation discovered". Both the hover timer and Radix onOpenChange
 * route through the returned setter.
 */
export function useTrackedPopoverOpen(testId: string): readonly [boolean, (next: boolean) => void] {
  return useTrackedOpen(
    () => {
      const target = popoverTargetFromTestId(testId);
      if (target !== null) trackFeature('popover-open', { target });
    },
    { once: true },
  );
}
