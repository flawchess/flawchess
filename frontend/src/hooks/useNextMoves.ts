import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { NextMovesResponse } from '@/types/api';
import type { FilterState } from '@/components/filters/FilterPanel';
import { hashToString } from '@/lib/zobrist';

export function useNextMoves(fullHash: bigint, filters: FilterState) {
  return useQuery<NextMovesResponse>({
    queryKey: [
      'nextMoves',
      hashToString(fullHash),
      {
        time_control: filters.timeControls,
        platform: filters.platforms,
        rated: filters.rated,
        opponent_type: filters.opponentType,
        recency: filters.recency,
        color: filters.color,
      },
    ],
    queryFn: async () => {
      const response = await apiClient.post<NextMovesResponse>('/analysis/next-moves', {
        target_hash: hashToString(fullHash),
        time_control: filters.timeControls,
        platform: filters.platforms,
        rated: filters.rated,
        opponent_type: filters.opponentType,
        recency: filters.recency,
        color: filters.color,
      });
      return response.data;
    },
  });
}
