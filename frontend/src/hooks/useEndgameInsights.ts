import { useMutation } from '@tanstack/react-query';
import { apiClient, buildFilterParams } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type {
  EndgameInsightsResponse,
  InsightsAxiosError,
} from '@/types/insights';

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
      const params = {
        ...buildFilterParams({
          time_control: filters.timeControls,
          platform: filters.platforms,
          recency: filters.recency,
          rated: filters.rated,
          // NOTE: opponent_type intentionally omitted — insights router rejects it.
          opponent_strength: filters.opponentStrength,
        }),
        color: filters.color,
      };
      const response = await apiClient.post<EndgameInsightsResponse>(
        '/insights/endgame',
        null,
        { params },
      );
      return response.data;
    },
  });
}
