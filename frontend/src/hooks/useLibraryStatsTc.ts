import { createTcSelectionStore, pickMostPopulatedTc } from '@/hooks/tcSelectionStore';
import { isQuietTc } from '@/lib/flawComparisonMeta';
import { DEFAULT_FLAW_FILTER } from '@/hooks/useFlawFilterStore';
import { useLibraryFlawComparison } from '@/hooks/useLibrary';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { TimeControlBucket } from '@/types/endgames';

/**
 * Shared time-control selection for the Library Stats tab.
 *
 * A key separate from the Endgame one, because Library counts analyzed games and
 * Endgame counts ranked games, so a TC valid on one tab may be absent on the other.
 */
export const LIBRARY_STATS_TC_STORAGE_KEY = 'library_stats_tc';

/** The per-TC fields the Library default needs (the per-TC payload entries satisfy it structurally). */
export interface LibraryTcCount {
  tc: TimeControlBucket;
  analyzed_n: number;
  below_gate: boolean;
  /** Games in the recent window; 0 marks a quiet TC. Absent on entries that are never quiet. */
  total_n?: number;
  /** Analyzed games outside the window too: ranks the TCs when every one is quiet. */
  history_analyzed_n?: number;
}

/**
 * Default TC (258): never a quiet TC (no game in the recent window) while another TC has
 * games in it. Among the non-quiet TCs, the one with the most analyzed games at or above
 * the gate (any non-quiet TC when none is); ties go to the faster TC. When every TC is quiet,
 * the one with the most history_analyzed_n. Null when no TC is offered.
 */
export function pickDefaultLibraryTc(tcs: readonly LibraryTcCount[]): TimeControlBucket | null {
  const active = tcs.filter((t) => !isQuietTc(t));
  if (active.length === 0) {
    return pickMostPopulatedTc(
      tcs,
      () => true,
      (t) => t.history_analyzed_n ?? 0,
    );
  }
  return pickMostPopulatedTc(
    active,
    (t) => !t.below_gate,
    (t) => t.analyzed_n,
  );
}

/**
 * The selected TC plus its setter. `tcs` is the payload's offered TC list: a
 * stored choice that is not in it is ignored in favour of the default.
 */
export const useLibraryStatsTc = createTcSelectionStore<LibraryTcCount>({
  storageKey: LIBRARY_STATS_TC_STORAGE_KEY,
  pickDefault: pickDefaultLibraryTc,
  // A pinned default that turned quiet is dropped unless every TC is quiet.
  isPinStillValid: (pinned, tcs) => !isQuietTc(pinned) || tcs.every(isQuietTc),
});

const NO_TCS: readonly LibraryTcCount[] = [];

/**
 * The TC selected in the Library Stats switch, for consumers outside the flaw sections.
 * Null when no TC is offered, which is also when the switch itself is not shown.
 */
export function useSelectedLibraryStatsTc(filters: FilterState): TimeControlBucket | null {
  const comparison = useLibraryFlawComparison(filters, DEFAULT_FLAW_FILTER);
  const [selectedTc] = useLibraryStatsTc(comparison.data?.tcs ?? NO_TCS);
  return selectedTc;
}
