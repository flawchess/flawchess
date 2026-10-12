import { useEffect, useSyncExternalStore } from 'react';
import type { TimeControlBucket } from '@/types/endgames';

/**
 * Time-control selection store factory, shared by the Endgame Stats tab (Phase 238) and
 * the Library Stats tab (Phase 239). Each tab gets its own store and localStorage key.
 *
 * Every section carries its own switch but all of them read and write the one
 * module-level store of their tab, so switching in any section switches every section.
 * The choice is remembered across visits in localStorage.
 *
 * The store holds only what the USER chose. The effective TC is derived during render
 * from the payload (the stored choice when that TC is still offered, else the tab's
 * default), so restoring or falling back never writes state and never fires analytics.
 * Tracking lives in the switch click handler.
 *
 * The default is pinned once computed (in memory only, never persisted) and reused while
 * that TC stays in the payload. Phase 238 review (FE-IN-05): re-deriving it on every
 * render let an import refetch flip every section to another TC that had just overtaken
 * the leader, with no user action.
 */

/** Fastest to slowest: the default tie-break order and the switch order. */
export const TIME_CONTROL_ORDER: readonly TimeControlBucket[] = [
  'bullet',
  'blitz',
  'rapid',
  'classical',
];

function isTimeControlBucket(value: unknown): value is TimeControlBucket {
  return TIME_CONTROL_ORDER.some((tc) => tc === value);
}

function isOffered<T extends { tc: TimeControlBucket }>(
  tc: TimeControlBucket | null,
  tcs: readonly T[],
): tc is TimeControlBucket {
  return tc !== null && tcs.some((t) => t.tc === tc);
}

/**
 * The TC with the highest count among the eligible entries (any entry when none is
 * eligible). Ties go to the faster TC. Null for an empty list.
 */
export function pickMostPopulatedTc<T extends { tc: TimeControlBucket }>(
  tcs: readonly T[],
  isEligible: (entry: T) => boolean,
  count: (entry: T) => number,
): TimeControlBucket | null {
  const eligible = tcs.filter(isEligible);
  const candidates = eligible.length > 0 ? eligible : tcs;
  let best: T | null = null;
  for (const candidate of candidates) {
    if (
      best === null ||
      count(candidate) > count(best) ||
      (count(candidate) === count(best) &&
        TIME_CONTROL_ORDER.indexOf(candidate.tc) < TIME_CONTROL_ORDER.indexOf(best.tc))
    ) {
      best = candidate;
    }
  }
  return best?.tc ?? null;
}

interface TcSelectionStoreOptions<T extends { tc: TimeControlBucket }> {
  storageKey: string;
  /** The default TC for a payload list; null for an empty list. */
  pickDefault: (tcs: readonly T[]) => TimeControlBucket | null;
}

/**
 * Create one TC selection store. Returns the hook: `tcs` is the payload's TC list, a
 * stored choice that is not in it is ignored in favour of the default.
 */
export function createTcSelectionStore<T extends { tc: TimeControlBucket }>({
  storageKey,
  pickDefault,
}: TcSelectionStoreOptions<T>): (
  tcs: readonly T[],
) => readonly [TimeControlBucket | null, (tc: TimeControlBucket) => void] {
  /** undefined = localStorage not read yet; null = no (valid) choice stored. */
  let chosenTc: TimeControlBucket | null | undefined;
  /** The first default computed this session; null until a payload has a TC. */
  let pinnedDefaultTc: TimeControlBucket | null = null;
  const listeners = new Set<() => void>();

  /** T-238-07 / T-239-06: the stored value is user-writable, so validate it and survive a throwing storage. */
  function readStoredTc(): TimeControlBucket | null {
    try {
      const raw = localStorage.getItem(storageKey);
      return isTimeControlBucket(raw) ? raw : null;
    } catch {
      return null;
    }
  }

  function getSnapshot(): TimeControlBucket | null {
    if (chosenTc === undefined) chosenTc = readStoredTc();
    return chosenTc;
  }

  function getServerSnapshot(): TimeControlBucket | null {
    return null;
  }

  function subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }

  function setSelectedTc(tc: TimeControlBucket): void {
    // Kept in memory even when the write fails (private mode, quota): an ignored
    // click would make the switch feel broken for the rest of the session.
    chosenTc = tc;
    try {
      localStorage.setItem(storageKey, tc);
    } catch {
      // Persistence is best-effort; rendering never depends on it.
    }
    listeners.forEach((listener) => listener());
  }

  // Named use... so the rules of hooks apply to its body.
  function useTcSelection(
    tcs: readonly T[],
  ): readonly [TimeControlBucket | null, (tc: TimeControlBucket) => void] {
    const stored = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
    const pinnedOffered = isOffered(pinnedDefaultTc, tcs);
    const defaultTc = pinnedOffered ? pinnedDefaultTc : pickDefault(tcs);
    // Pin after render (module writes during render are impure). Every section pins the
    // same value, and a new default is pinned only once the old one left the payload.
    useEffect(() => {
      if (!pinnedOffered) pinnedDefaultTc = defaultTc;
    }, [pinnedOffered, defaultTc]);
    const selected = isOffered(stored, tcs) ? stored : defaultTc;
    return [selected, setSelectedTc] as const;
  }

  return useTcSelection;
}
