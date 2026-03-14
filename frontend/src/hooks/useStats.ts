import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/api/client';
import type { Recency } from '@/types/api';

export function useRatingHistory(recency: Recency | null) {
  const normalizedRecency = recency === 'all' ? null : recency;
  return useQuery({
    queryKey: ['ratingHistory', normalizedRecency],
    queryFn: () => statsApi.getRatingHistory(normalizedRecency),
  });
}

export function useGlobalStats(recency: Recency | null) {
  const normalizedRecency = recency === 'all' ? null : recency;
  return useQuery({
    queryKey: ['globalStats', normalizedRecency],
    queryFn: () => statsApi.getGlobalStats(normalizedRecency),
  });
}
