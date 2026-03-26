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
  };
}

export function useEndgameStats(filters: FilterState) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameStats', params],
    queryFn: () => endgameApi.getStats(params),
  });
}

export function useEndgameTimeline(filters: FilterState, window = 50) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameTimeline', params, window],
    queryFn: () => endgameApi.getTimeline({ ...params, window }),
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
  });
}
