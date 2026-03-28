import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/api/client';
import type { Platform, Recency, TimeControl, OpponentType } from '@/types/api';

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

export function useMostPlayedOpenings(filters?: {
  recency: Recency | null;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
}) {
  const normalizedRecency = filters?.recency === 'all' ? null : (filters?.recency ?? null);
  const timeControl = filters?.timeControls ?? null;
  const platform = filters?.platforms ?? null;
  const rated = filters?.rated ?? null;
  const opponentType = filters?.opponentType ?? 'human';

  return useQuery({
    queryKey: ['mostPlayedOpenings', normalizedRecency, timeControl, platform, rated, opponentType],
    queryFn: () => statsApi.getMostPlayedOpenings({
      recency: normalizedRecency,
      time_control: timeControl,
      platform: platform,
      rated: rated,
      opponent_type: opponentType,
    }),
  });
}
