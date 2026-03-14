import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { AnalysisRequest, AnalysisResponse } from '@/types/api';

export function useAnalysis() {
  return useMutation<AnalysisResponse, Error, AnalysisRequest>({
    mutationFn: async (request: AnalysisRequest) => {
      const response = await apiClient.post<AnalysisResponse>('/analysis/positions', request);
      return response.data;
    },
  });
}

/**
 * Auto-fetch paginated games on mount (no position filter).
 * Used by Dashboard to show a default games list.
 */
export function useGamesQuery(params: {
  offset: number;
  limit: number;
  enabled?: boolean;
}) {
  return useQuery<AnalysisResponse>({
    queryKey: ['games', params.offset, params.limit],
    queryFn: async () => {
      const response = await apiClient.post<AnalysisResponse>('/analysis/positions', {
        offset: params.offset,
        limit: params.limit,
      });
      return response.data;
    },
    enabled: params.enabled !== false,
  });
}
