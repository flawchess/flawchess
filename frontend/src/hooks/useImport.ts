import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ImportRequest, ImportStartedResponse, ImportStatusResponse } from '@/types/api';

/** Trigger a new import job. Returns ImportStartedResponse (with job_id). */
export function useImportTrigger() {
  return useMutation<ImportStartedResponse, Error, ImportRequest>({
    mutationFn: async (request: ImportRequest) => {
      const response = await apiClient.post<ImportStartedResponse>('/imports', request);
      return response.data;
    },
  });
}

/** Poll a single import job. Stops when status is 'done' or 'error'. */
export function useImportPolling(jobId: string | null) {
  return useQuery<ImportStatusResponse, Error>({
    queryKey: ['import', jobId],
    queryFn: async () => {
      const response = await apiClient.get<ImportStatusResponse>(`/imports/${jobId}`);
      return response.data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });
}
