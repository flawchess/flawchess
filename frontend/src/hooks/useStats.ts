import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/api/client';
import type { Platform, Recency } from '@/types/api';

export function useRatingHistory(recency: Recency | null, platforms: Platform[] | null) {
  const normalizedRecency = recency === 'all' ? null : recency;
  const platform = platforms && platforms.length === 1 ? platforms[0] : null;
  return useQuery({
    queryKey: ['ratingHistory', normalizedRecency, platform],
    queryFn: () => statsApi.getRatingHistory(normalizedRecency, platform),
  });
}

export function useGlobalStats(recency: Recency | null, platforms: Platform[] | null) {
  const normalizedRecency = recency === 'all' ? null : recency;
  const platform = platforms && platforms.length === 1 ? platforms[0] : null;
  return useQuery({
    queryKey: ['globalStats', normalizedRecency, platform],
    queryFn: () => statsApi.getGlobalStats(normalizedRecency, platform),
  });
}

export function useMostPlayedOpenings() {
  return useQuery({
    queryKey: ['mostPlayedOpenings'],
    queryFn: () => statsApi.getMostPlayedOpenings(),
  });
}
