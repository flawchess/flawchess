import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { AnalysisResponse } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import type { FilterState } from '@/components/filters/FilterPanel';

export function usePositionAnalysisQuery(params: {
  targetHash: string;
  filters: FilterState;
  offset: number;
  limit: number;
}) {
  return useQuery<AnalysisResponse>({
    queryKey: ['positionAnalysis', params.targetHash, params.filters, params.offset, params.limit],
    queryFn: async () => {
      const response = await apiClient.post<AnalysisResponse>('/openings/positions', {
        target_hash: params.targetHash,
        match_side: resolveMatchSide(params.filters.matchSide, params.filters.color),
        time_control: params.filters.timeControls,
        platform: params.filters.platforms,
        rated: params.filters.rated,
        opponent_type: params.filters.opponentType,
        recency: params.filters.recency,
        color: params.filters.color,
        offset: params.offset,
        limit: params.limit,
      });
      return response.data;
    },
  });
}
