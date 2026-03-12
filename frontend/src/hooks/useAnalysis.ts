import { useMutation } from '@tanstack/react-query';
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
