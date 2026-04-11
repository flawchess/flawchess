import { useQuery } from '@tanstack/react-query';
import { endgameApi } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameClass } from '@/types/endgames';

// Extract endgame-relevant filters — no color, no matchSide per D-02.
function buildEndgameParams(filters: FilterState) {
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    recency: filters.recency,
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
  window: number = DEFAULT_OVERVIEW_WINDOW,
) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameOverview', params, window],
    queryFn: () => endgameApi.getOverview({ ...params, window }),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
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
