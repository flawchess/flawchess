import { createTcSelectionStore, pickMostPopulatedTc } from '@/hooks/tcSelectionStore';
import type { RankedTcStats, TimeControlBucket } from '@/types/endgames';

/**
 * Shared time-control selection for the Endgame Stats tab (Phase 238).
 *
 * The store mechanics (module-level choice, localStorage persistence D-13, validated
 * read, pinned default FE-IN-05) live in createTcSelectionStore, shared with the Library
 * Stats tab; this module supplies the Endgame key and the D-12 default.
 */

export const ENDGAME_STATS_TC_STORAGE_KEY = 'endgame_stats_tc';

/**
 * D-12 default: the TC with the most ranked games among TCs at or above the
 * anchor floor (any TC when none is). Ties go to the faster TC. Null when the
 * ranked sample is empty.
 */
export function pickDefaultTc(tcs: readonly RankedTcStats[]): TimeControlBucket | null {
  return pickMostPopulatedTc(
    tcs,
    (t) => t.anchor_games >= t.anchor_min_games,
    (t) => t.ranked_games,
  );
}

/**
 * The selected TC plus its setter. `tcs` is the payload's TC list (D-14): a
 * stored choice that is not in it is ignored in favour of the D-12 default.
 */
export const useEndgameStatsTc = createTcSelectionStore<RankedTcStats>({
  storageKey: ENDGAME_STATS_TC_STORAGE_KEY,
  pickDefault: pickDefaultTc,
});
