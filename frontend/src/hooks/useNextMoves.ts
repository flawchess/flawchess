import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { NextMovesResponse } from '@/types/api';
import type { FilterState } from '@/components/filters/FilterPanel';
import { hashToString } from '@/lib/zobrist';
import { rangeToQueryParams } from '@/lib/opponentStrength';

export function useNextMoves(fullHash: bigint, filters: FilterState) {
  const gapParams = rangeToQueryParams(filters.opponentStrength);
  return useQuery<NextMovesResponse>({
    queryKey: [
      'nextMoves',
      hashToString(fullHash),
      {
        time_control: filters.timeControls,
        platform: filters.platforms,
        rated: filters.rated,
        opponent_type: filters.opponentType,
        opponent_gap_min: gapParams.opponent_gap_min ?? null,
        opponent_gap_max: gapParams.opponent_gap_max ?? null,
        recency: filters.recency,
        color: filters.color,
      },
    ],
    queryFn: async () => {
      const response = await apiClient.post<NextMovesResponse>('/openings/next-moves', {
        target_hash: hashToString(fullHash),
        time_control: filters.timeControls,
        platform: filters.platforms,
        rated: filters.rated,
        opponent_type: filters.opponentType,
        ...gapParams,
        recency: filters.recency,
        color: filters.color,
      });
      return response.data;
    },
  });
}
