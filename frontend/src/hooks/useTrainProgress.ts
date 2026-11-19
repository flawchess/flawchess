import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { TrainProgressResponse } from '@/types/train';

/**
 * The shared query key for GET /train/progress. Load-bearing: the nav badge reads the SAME key
 * so TanStack Query dedupes both consumers to one in-flight request.
 */
export const TRAIN_PROGRESS_QUERY_KEY = ['train', 'progress'] as const;

/**
 * GET /train/progress — the streak, this-week tally, and
 * honest mastered/parked counts.
 *
 * Uses the global queryClient defaults (staleTime 30s, retry 1) — no
 * custom `refetchInterval`, no polling (a schedule becoming due at midnight
 * surfaces on the next focus/navigation refetch, not live).
 *
 * `options.enabled` lets the nav-badge call site gate the request off for
 * guests and locked-nav accounts, where the waiting-puzzles badge is not shown.
 */
export function useTrainProgress(options?: { enabled?: boolean }) {
  return useQuery<TrainProgressResponse>({
    queryKey: TRAIN_PROGRESS_QUERY_KEY,
    queryFn: trainApi.getProgress,
    enabled: options?.enabled ?? true,
  });
}

/**
 * POST /train/blunder-check-notice/dismiss — hides the launch notice (D-21). Optimistic: the
 * cached progress flips `blunder_check_notice` to false on mutate, so the card drops the notice
 * at once, and the progress query is invalidated on settle so the server's answer wins (a failed
 * dismissal brings the notice back).
 *
 * No Sentry call here: the global MutationCache.onError already captures every mutation error.
 */
export function useDismissBlunderCheckNotice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: trainApi.dismissBlunderCheckNotice,
    onMutate: () => {
      queryClient.setQueryData<TrainProgressResponse>(TRAIN_PROGRESS_QUERY_KEY, (cached) =>
        cached === undefined ? cached : { ...cached, blunder_check_notice: false },
      );
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: TRAIN_PROGRESS_QUERY_KEY });
    },
  });
}
