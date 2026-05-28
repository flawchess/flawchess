import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { ReadinessResponse } from '@/types/api';

const READINESS_POLL_INTERVAL_MS = 3_000;
const READINESS_STALE_TIME_MS = 3_000;

/** Poll GET /imports/readiness every 3s until Tier 2 is reached.
 *
 * Tier 1 (tier1=true): no active import job in-flight for this user.
 * Tier 2 (tier2=true): tier1=true AND evals drained AND percentile rows exist
 *   (or user has no games).
 *
 * Defaults tier1=false and tier2=false before the first fetch resolves, so
 * gated surfaces (endgames page, eval-dependent stats) do not flash open on
 * initial page load.
 *
 * Polling stops when tier2 is true — at that point all Stage-A and Stage-B
 * work is complete and further polling provides no signal.
 *
 * All consumers on the same page share one in-flight request via the shared
 * queryKey ['imports', 'readiness'] — TanStack Query deduplicates them.
 *
 * NOTE: This hook does NOT include a window.location.reload() effect.
 * Consumers that need to react to the tier2 transition should use a
 * toast/notification (e.g. App.tsx Tier-2 watcher) rather than a hard reload.
 */
export function useReadiness() {
  const query = useQuery<ReadinessResponse>({
    queryKey: ['imports', 'readiness'],
    queryFn: async () => {
      const response = await apiClient.get<ReadinessResponse>('/imports/readiness');
      return response.data;
    },
    staleTime: READINESS_STALE_TIME_MS,
    refetchInterval: (query) => {
      return query.state.data?.tier2 ? false : READINESS_POLL_INTERVAL_MS;
    },
  });

  return {
    tier1: query.data?.tier1 ?? false,
    tier2: query.data?.tier2 ?? false,
    pendingCount: query.data?.pending_count ?? 0,
    totalCount: query.data?.total_count ?? 0,
    isLoading: query.isLoading,
  };
}
