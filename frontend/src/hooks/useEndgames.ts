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

export function useEndgameStats(filters: FilterState) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameStats', params],
    queryFn: () => endgameApi.getStats(params),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

const DEFAULT_TIMELINE_WINDOW = 100;

export function useEndgameTimeline(filters: FilterState, window = DEFAULT_TIMELINE_WINDOW) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameTimeline', params, window],
    queryFn: () => endgameApi.getTimeline({ ...params, window }),
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

export function useEndgamePerformance(filters: FilterState) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgamePerformance', params],
    queryFn: () => endgameApi.getPerformance(params),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}

const DEFAULT_CONV_RECOV_WINDOW = 100;

export function useEndgameConvRecovTimeline(filters: FilterState, window = DEFAULT_CONV_RECOV_WINDOW) {
  const params = buildEndgameParams(filters);
  return useQuery({
    queryKey: ['endgameConvRecovTimeline', params, window],
    queryFn: () => endgameApi.getConvRecovTimeline({ ...params, window }),
    staleTime: ENDGAME_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
