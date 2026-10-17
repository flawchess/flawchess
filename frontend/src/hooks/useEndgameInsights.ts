import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { apiClient } from '@/api/client';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';

// One cached report per user: it does not depend on any page filter, so the key
// is constant. App.tsx invalidates the ['endgame-insights'] prefix on import completion
// (a refetch only; the server never drops an existing report after an import).
const CACHED_ENDGAME_INSIGHTS_KEY = ['endgame-insights', 'cached'] as const;

// Shared by every Generate mutation so useEndgameInsightsGenerating sees a request
// started by either Stats-tab mount (the tab mounts twice, desktop + mobile).
const ENDGAME_INSIGHTS_MUTATION_KEY = ['endgame-insights', 'generate'] as const;

/**
 * POST /api/insights/endgame — generate LLM-produced Endgame Insights report.
 *
 * Sends no query parameters: the report is filter-free, so Generate never
 * reads or resets the page filters.
 *
 * On success the result is written into the cached-report query, which is the single
 * source of truth for the rendered report. Don't keep the result in component
 * state: a Stats-tab remount would fall back to the stale pre-Generate cache
 * entry and the freshly generated report would vanish.
 *
 * Error capture: global MutationCache.onError in lib/queryClient.ts handles Sentry.
 * Do NOT add Sentry.captureException in consumers of this hook.
 */
export function useEndgameInsights() {
  const queryClient = useQueryClient();
  return useMutation<EndgameInsightsResponse, InsightsAxiosError, void>({
    mutationKey: ENDGAME_INSIGHTS_MUTATION_KEY,
    mutationFn: async () => {
      const response = await apiClient.post<EndgameInsightsResponse>('/insights/endgame');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(CACHED_ENDGAME_INSIGHTS_KEY, data);
    },
  });
}

/**
 * GET /api/insights/endgame/cached — auto-load the user's previously-cached report.
 *
 * Returns null on 404 (no cache row) so callers can render the empty state
 * silently. Other axios errors propagate. The endpoint never invokes the LLM
 * and never consumes rate-limit budget, so it is safe to fire on every page
 * mount. Takes no filters and uses one constant query key.
 */
export function useCachedEndgameInsights() {
  return useQuery<EndgameInsightsResponse | null>({
    queryKey: CACHED_ENDGAME_INSIGHTS_KEY,
    queryFn: async () => {
      try {
        const response = await apiClient.get<EndgameInsightsResponse>(
          '/insights/endgame/cached',
        );
        return response.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: false,
  });
}

/** True while any Generate request is in flight, whichever Stats-tab mount started it. */
export function useEndgameInsightsGenerating(): boolean {
  return useIsMutating({ mutationKey: ENDGAME_INSIGHTS_MUTATION_KEY }) > 0;
}
