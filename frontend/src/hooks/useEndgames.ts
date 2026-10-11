import { useQuery } from '@tanstack/react-query';
import { endgameApi } from '@/api/client';
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameClass } from '@/types/endgames';

// Extract endgame-relevant filters — no color, no matchSide per D-02.
function buildEndgameParams(filters: FilterState) {
  const dateParams = dateRangeToWireParams(resolveDateRange(filters));
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    ...dateParams,
    rated: filters.rated,
    opponent_type: filters.opponentType,
    opponent_strength: filters.opponentStrength,
  };
}

// Endgame queries are expensive (heavy GROUP BY on game_positions).
// 5 minutes staleTime + no refetch-on-focus prevents redundant DB load
// from alt-tabbing or component re-mounts. Data only changes on new imports.
const ENDGAME_STALE_TIME = 5 * 60 * 1000;

// Phase 238 (D-01): the Games tab's filtered per-category stats. The key sits
// under the ['endgameOverview'] prefix so the import-completion invalidations in
// App.tsx and Import.tsx refresh it without any change.
export function useEndgameStats(
  filters: FilterState,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameOverview', 'stats', params],
    queryFn: () => endgameApi.getStats(params),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
    // Quick 260529-015: gate the fetch on Tier-2 readiness. While the page is
    // locked (Analyzing…) the stats must NOT fetch — a fetch during the locked
    // phase caches a pre-Stage-B response, and the 5min staleTime then serves
    // that stale cache when the page reactively unlocks. Disabling until tier2
    // makes the first fetch happen post-unlock.
    enabled,
  });
}

// Phase 238 (D-01): the ranked-sample payload behind the Stats tab. No filters
// argument: the endpoint ignores them by design. The key sits under the
// ['endgameOverview'] prefix so the import-completion invalidations in App.tsx
// and Import.tsx refresh it without any change.
export function useEndgameRankedStats(options: { enabled?: boolean } = {}) {
  const { enabled = true } = options;
  return useQuery({
    queryKey: ['endgameOverview', 'ranked'],
    queryFn: () => endgameApi.getRankedStats(),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
    // Same Tier-2 gate as useEndgameStats: a fetch while the page is locked would
    // cache a pre-Stage-B payload that the staleTime then keeps serving.
    enabled,
  });
}

export function useEndgameGames(
  endgameClass: EndgameClass | null,
  filters: FilterState,
  offset: number,
  limit: number,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameGames', endgameClass, params, offset, limit],
    queryFn: () => endgameApi.getGames({
      ...params,
      endgame_class: endgameClass!,
      offset,
      limit,
    }),
    enabled: enabled && endgameClass !== null,
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
