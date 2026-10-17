import { useQuery } from '@tanstack/react-query';
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
