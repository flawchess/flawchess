import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { OpeningInsightsResponse } from '@/types/insights';
import type {
  TimeControl,
  Platform,
  OpponentType,
  OpponentStrengthRange,
} from '@/types/api';
import { ANY_RANGE, rangeToQueryParams } from '@/lib/opponentStrength';
import { presetToDates, dateRangeToWireParams } from '@/lib/recency';
import type { FilterState } from '@/components/filters/FilterPanel';

interface OpeningInsightsFilters {
  recency: FilterState['recency'];
  customRange?: FilterState['customRange'];
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
  const recency = filters?.recency ?? null;
  const customRange = filters?.customRange ?? null;
  const timeControl = filters?.timeControls ?? null;
  const platform = filters?.platforms ?? null;
  const rated = filters?.rated ?? null;
  const opponentType = filters?.opponentType ?? 'human';
  const opponentStrength = filters?.opponentStrength ?? ANY_RANGE;
  const gapParams = rangeToQueryParams(opponentStrength);

  // Resolve from_date/to_date from the preset or custom range.
  const dateRange =
    recency === 'custom'
      ? (customRange ?? {})
      : presetToDates(recency);
  const dateParams = dateRangeToWireParams(dateRange);

  return useQuery<OpeningInsightsResponse>({
    queryKey: [
      'openingInsights',
      dateParams.from_date ?? null,
      dateParams.to_date ?? null,
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
          ...dateParams,
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
