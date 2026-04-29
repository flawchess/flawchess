import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { OpeningInsightsResponse } from '@/types/insights';
import type {
  Recency,
  TimeControl,
  Platform,
  OpponentType,
  OpponentStrengthRange,
} from '@/types/api';
import { ANY_RANGE, rangeToQueryParams } from '@/lib/opponentStrength';

interface OpeningInsightsFilters {
  recency: Recency | null;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  opponentStrength: OpponentStrengthRange;
}

/**
 * Phase 71 (D-16, D-17): TanStack Query hook for POST /api/insights/openings.
 * Filter-driven (no Generate button — auto-fetches on filter change). The block
 * always sends color: "all" regardless of the active global color filter (D-02).
 * Errors are captured by the global QueryCache.onError handler in queryClient.ts —
 * do NOT add Sentry.captureException here (CLAUDE.md frontend Sentry rules).
 */
export function useOpeningInsights(filters?: OpeningInsightsFilters) {
  // Normalize filter inputs (mirrors useMostPlayedOpenings in useStats.ts).
  const normalizedRecency = filters?.recency === 'all' ? null : (filters?.recency ?? null);
  const timeControl = filters?.timeControls ?? null;
  const platform = filters?.platforms ?? null;
  const rated = filters?.rated ?? null;
  const opponentType = filters?.opponentType ?? 'human';
  const opponentStrength = filters?.opponentStrength ?? ANY_RANGE;
  const gapParams = rangeToQueryParams(opponentStrength);

  return useQuery<OpeningInsightsResponse>({
    queryKey: [
      'openingInsights',
      normalizedRecency,
      timeControl,
      platform,
      rated,
      opponentType,
      opponentStrength.min,
      opponentStrength.max,
    ],
    queryFn: () =>
      apiClient
        .post<OpeningInsightsResponse>('/insights/openings', {
          recency: normalizedRecency ?? undefined,
          time_control: timeControl ?? undefined,
          platform: platform ?? undefined,
          rated: rated ?? undefined,
          opponent_type: opponentType,
          ...gapParams,
          color: 'all', // D-02: always 'all' regardless of global filter
        })
        .then((r) => r.data),
    // staleTime inherits 30_000 from queryClient.ts global default
  });
}
