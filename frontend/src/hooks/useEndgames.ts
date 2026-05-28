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

const DEFAULT_OVERVIEW_WINDOW = 100;

export function useEndgameOverview(
  filters: FilterState,
  options: { window?: number; enabled?: boolean } = {},
) {
  const { window = DEFAULT_OVERVIEW_WINDOW, enabled = true } = options;
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameOverview', params, window],
    queryFn: () => endgameApi.getOverview({ ...params, window }),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
    // Quick 260529-015: gate the fetch on Tier-2 readiness. While the page is
    // locked (Analyzing…) the overview must NOT fetch — a fetch during the
    // locked phase caches a pre-Stage-B response (only the score_gap badge),
    // and the 5min staleTime then serves that stale cache when the page
    // reactively unlocks, so the eval-dependent badges only appear after a
    // manual reload. Disabling until tier2 makes the first fetch happen
    // post-unlock (after Stage B has committed all percentile rows).
    enabled,
  });
}

export function useEndgameGames(
  endgameClass: EndgameClass | null,
  filters: FilterState,
  offset: number,
  limit: number,
) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameGames', endgameClass, params, offset, limit],
    queryFn: () => endgameApi.getGames({
      ...params,
      endgame_class: endgameClass!,
      offset,
      limit,
    }),
    enabled: endgameClass !== null,
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
