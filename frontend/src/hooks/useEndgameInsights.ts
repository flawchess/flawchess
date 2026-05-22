import { useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { apiClient, buildFilterParams } from '@/api/client';
import { resolveDateRange, dateRangeToWireParams } from '@/lib/recency';
import type { FilterState } from '@/components/filters/FilterPanel';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';

function buildInsightsParams(filters: FilterState): Record<string, unknown> {
  const dateParams = dateRangeToWireParams(resolveDateRange(filters));
  return {
    ...buildFilterParams({
      time_control: filters.timeControls,
      platform: filters.platforms,
      ...dateParams,
      rated: filters.rated,
      // NOTE: opponent_type intentionally omitted — insights router rejects it.
      opponent_strength: filters.opponentStrength,
    }),
    color: filters.color,
  };
}

/**
 * POST /api/insights/endgame — generate LLM-produced Endgame Insights report.
 *
 * Shared filter serialization with useEndgames via buildFilterParams.
 * Appends `color` (only param the insights endpoint accepts but endgame endpoint doesn't).
 * Does NOT pass `opponent_type` — insights router does not accept it
 * (hardcoded to "human" server-side per Phase 65).
 *
 * Error capture: global MutationCache.onError in lib/queryClient.ts handles Sentry.
 * Do NOT add Sentry.captureException in consumers of this hook.
 */
export function useEndgameInsights() {
  return useMutation<EndgameInsightsResponse, InsightsAxiosError, FilterState>({
    mutationFn: async (filters: FilterState) => {
      const params = buildInsightsParams(filters);
      const response = await apiClient.post<EndgameInsightsResponse>(
        '/insights/endgame',
        null,
        { params },
      );
      return response.data;
    },
  });
}

/**
 * GET /api/insights/endgame/cached — auto-load a previously-cached report.
 *
 * Returns null on 404 (no cache row) so callers can render the empty state
 * silently. Other axios errors propagate. The endpoint never invokes the LLM
 * and never consumes rate-limit budget, so it is safe to fire on every page
 * mount and filter change.
 *
 * Shares filter serialization with useEndgameInsights via buildInsightsParams
 * so the cache lookup keys exactly match what a Generate click would produce.
 */
export function useCachedEndgameInsights(filters: FilterState) {
  const params = buildInsightsParams(filters);
  return useQuery<EndgameInsightsResponse | null>({
    queryKey: ['endgame-insights', 'cached', params],
    queryFn: async () => {
      try {
        const response = await apiClient.get<EndgameInsightsResponse>(
          '/insights/endgame/cached',
          { params },
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
