import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { MedalKey, UnclaimedMedalsResponse } from '@/types/train';

/** Query key for GET /train/medals/unclaimed (Phase 231). */
export const TRAIN_UNCLAIMED_MEDALS_QUERY_KEY = ['train', 'medals', 'unclaimed'] as const;

/**
 * GET /train/medals/unclaimed: medals from closed weeks the user has not
 * celebrated yet. `refetchOnMount: 'always'` so every Train landing visit asks
 * the server afresh (the server finalizes due weeks lazily on this read).
 * `enabled` lets the host skip guests and impersonating admins.
 *
 * No Sentry capture here: the global QueryCache.onError already reports
 * failed queries.
 */
export function useUnclaimedMedals(options: { enabled: boolean }) {
  return useQuery<UnclaimedMedalsResponse>({
    queryKey: TRAIN_UNCLAIMED_MEDALS_QUERY_KEY,
    queryFn: () => trainApi.getUnclaimedMedals(),
    refetchOnMount: 'always',
    enabled: options.enabled,
  });
}

/**
 * POST /train/medals/claim for the shown keys. On success the claimed keys are
 * removed from the cached unclaimed list so a later mount never shows them
 * from cache. The list is deliberately NOT invalidated: the host keeps a
 * per-mount closed state, but a refetch has no reason to run here either.
 *
 * A failed claim changes nothing: the rows stay unclaimed server-side and the
 * medals reappear on the next visit (D-13). No Sentry capture here: the global
 * MutationCache.onError already reports failed mutations.
 */
export function useClaimMedals() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, MedalKey[]>({
    mutationFn: (keys) => trainApi.claimMedals(keys),
    onSuccess: (_data, keys) => {
      queryClient.setQueryData<UnclaimedMedalsResponse>(TRAIN_UNCLAIMED_MEDALS_QUERY_KEY, (cached) => {
        if (!cached) return cached;
        const claimed = new Set(keys.map((key) => `${key.week_start}|${key.board}`));
        return {
          medals: cached.medals.filter((entry) => !claimed.has(`${entry.week_start}|${entry.board}`)),
        };
      });
    },
  });
}
