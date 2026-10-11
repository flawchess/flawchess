import { useEffect, useSyncExternalStore } from 'react';
import type { RankedTcStats, TimeControlBucket } from '@/types/endgames';

/**
 * Shared time-control selection for the Endgame Stats tab (Phase 238).
 *
 * Every section carries its own switch (D-00h) but all of them read and write
 * this one module-level store, so switching in any section switches every
 * section. The choice is remembered across visits in localStorage (D-13).
 *
 * The store holds only what the USER chose. The effective TC is derived during
 * render from the payload (the stored choice when that TC still has ranked
 * games, else the D-12 default), so restoring or falling back never writes
 * state and never fires analytics. Tracking lives in the switch click handler.
 *
 * The D-12 default is pinned once computed (in memory only, never persisted) and
 * reused while that TC stays in the payload. Phase 238 review (FE-IN-05): re-deriving
 * it on every render let an import refetch flip every section to another TC that had
 * just overtaken the leader, with no user action.
 */

export const ENDGAME_STATS_TC_STORAGE_KEY = 'endgame_stats_tc';

// Fastest to slowest: the D-12 tie-break order and the switch order (D-14).
const TC_ORDER: readonly TimeControlBucket[] = ['bullet', 'blitz', 'rapid', 'classical'];

function isTimeControlBucket(value: unknown): value is TimeControlBucket {
  return TC_ORDER.some((tc) => tc === value);
}

/** undefined = localStorage not read yet; null = no (valid) choice stored. */
let chosenTc: TimeControlBucket | null | undefined;
/** The first D-12 default computed this session; null until a payload has a TC. */
let pinnedDefaultTc: TimeControlBucket | null = null;
const listeners = new Set<() => void>();

/** T-238-07: the stored value is user-writable, so validate it and survive a throwing storage. */
function readStoredTc(): TimeControlBucket | null {
  try {
    const raw = localStorage.getItem(ENDGAME_STATS_TC_STORAGE_KEY);
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
    localStorage.setItem(ENDGAME_STATS_TC_STORAGE_KEY, tc);
  } catch {
    // Persistence is best-effort; rendering never depends on it.
  }
  listeners.forEach((listener) => listener());
}

function isInPayload(
  tc: TimeControlBucket | null,
  tcs: readonly RankedTcStats[],
): tc is TimeControlBucket {
  return tc !== null && tcs.some((t) => t.tc === tc);
}

/**
 * D-12 default: the TC with the most ranked games among TCs at or above the
 * anchor floor (any TC when none is). Ties go to the faster TC. Null when the
 * ranked sample is empty.
 */
export function pickDefaultTc(tcs: readonly RankedTcStats[]): TimeControlBucket | null {
  const aboveFloor = tcs.filter((t) => t.anchor_games >= t.anchor_min_games);
  const candidates = aboveFloor.length > 0 ? aboveFloor : tcs;
  let best: RankedTcStats | null = null;
  for (const candidate of candidates) {
    if (
      best === null ||
      candidate.ranked_games > best.ranked_games ||
      (candidate.ranked_games === best.ranked_games &&
        TC_ORDER.indexOf(candidate.tc) < TC_ORDER.indexOf(best.tc))
    ) {
      best = candidate;
    }
  }
  return best?.tc ?? null;
}

/**
 * The selected TC plus its setter. `tcs` is the payload's TC list (D-14): a
 * stored choice that is not in it is ignored in favour of the D-12 default.
 */
export function useEndgameStatsTc(
  tcs: readonly RankedTcStats[],
): readonly [TimeControlBucket | null, (tc: TimeControlBucket) => void] {
  const stored = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const pinnedInPayload = isInPayload(pinnedDefaultTc, tcs);
  const defaultTc = pinnedInPayload ? pinnedDefaultTc : pickDefaultTc(tcs);
  // Pin after render (module writes during render are impure). Every section pins the
  // same value, and a new default is pinned only once the old one left the payload.
  useEffect(() => {
    if (!pinnedInPayload) pinnedDefaultTc = defaultTc;
  }, [pinnedInPayload, defaultTc]);
  const selected = isInPayload(stored, tcs) ? stored : defaultTc;
  return [selected, setSelectedTc] as const;
}
