import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { OpeningsResponse } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import { rangeToQueryParams } from '@/lib/opponentStrength';
import type { FilterState } from '@/components/filters/FilterPanel';

export function useOpeningsPositionQuery(params: {
  targetHash: string;
  filters: FilterState;
  offset: number;
  limit: number;
}) {
  return useQuery<OpeningsResponse>({
    queryKey: ['openingsPosition', params.targetHash, params.filters, params.offset, params.limit],
    queryFn: async () => {
      const response = await apiClient.post<OpeningsResponse>('/openings/positions', {
        target_hash: params.targetHash,
        match_side: resolveMatchSide(params.filters.matchSide, params.filters.color),
        time_control: params.filters.timeControls,
        platform: params.filters.platforms,
        rated: params.filters.rated,
        opponent_type: params.filters.opponentType,
        ...rangeToQueryParams(params.filters.opponentStrength),
        recency: params.filters.recency,
        color: params.filters.color,
        offset: params.offset,
        limit: params.limit,
      });
      return response.data;
    },
  });
}
