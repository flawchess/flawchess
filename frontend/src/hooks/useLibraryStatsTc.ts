import { createTcSelectionStore, pickMostPopulatedTc } from '@/hooks/tcSelectionStore';
import type { TimeControlBucket } from '@/types/endgames';

/**
 * Shared time-control selection for the Library Stats tab (Phase 239).
 *
 * D-05: a key separate from the Endgame one, because Library counts analyzed games and
 * Endgame counts ranked games, so a TC valid on one tab may be absent on the other.
 */
export const LIBRARY_STATS_TC_STORAGE_KEY = 'library_stats_tc';

/** The per-TC fields the Library default needs (the per-TC payload entries satisfy it structurally). */
export interface LibraryTcCount {
  tc: TimeControlBucket;
  analyzed_n: number;
  below_gate: boolean;
}

/**
 * D-04 default: the TC with the most analyzed games among TCs at or above the gate (any
 * TC when none is). Ties go to the faster TC. Null when no TC is offered.
 */
export function pickDefaultLibraryTc(tcs: readonly LibraryTcCount[]): TimeControlBucket | null {
  return pickMostPopulatedTc(
    tcs,
    (t) => !t.below_gate,
    (t) => t.analyzed_n,
  );
}

/**
 * The selected TC plus its setter. `tcs` is the payload's offered TC list (D-02): a
 * stored choice that is not in it is ignored in favour of the D-04 default.
 */
export const useLibraryStatsTc = createTcSelectionStore<LibraryTcCount>({
  storageKey: LIBRARY_STATS_TC_STORAGE_KEY,
  pickDefault: pickDefaultLibraryTc,
});
