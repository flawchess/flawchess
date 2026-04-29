import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/api/client';
import type { Platform, Recency, TimeControl, OpponentType, OpponentStrengthRange } from '@/types/api';
import { ANY_RANGE } from '@/lib/opponentStrength';

export function useRatingHistory(
  recency: Recency | null,
  platforms: Platform[] | null,
  opponentType: OpponentType,
  opponentStrength: OpponentStrengthRange,
) {
  const normalizedRecency = recency === 'all' ? null : recency;
  // safe: length === 1 check guarantees index 0 exists
  const platform = platforms && platforms.length === 1 ? platforms[0]! : null;
  return useQuery({
    queryKey: ['ratingHistory', normalizedRecency, platform, opponentType, opponentStrength.min, opponentStrength.max],
    queryFn: () => statsApi.getRatingHistory(normalizedRecency, platform, opponentType, opponentStrength),
  });
}

export function useGlobalStats(
  recency: Recency | null,
  platforms: Platform[] | null,
  opponentType: OpponentType,
  opponentStrength: OpponentStrengthRange,
) {
  const normalizedRecency = recency === 'all' ? null : recency;
  // safe: length === 1 check guarantees index 0 exists
  const platform = platforms && platforms.length === 1 ? platforms[0]! : null;
  return useQuery({
    queryKey: ['globalStats', normalizedRecency, platform, opponentType, opponentStrength.min, opponentStrength.max],
    queryFn: () => statsApi.getGlobalStats(normalizedRecency, platform, opponentType, opponentStrength),
  });
}

export function useMostPlayedOpenings(filters?: {
  recency: Recency | null;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  opponentStrength?: OpponentStrengthRange;
}) {
  const normalizedRecency = filters?.recency === 'all' ? null : (filters?.recency ?? null);
  const timeControl = filters?.timeControls ?? null;
  const platform = filters?.platforms ?? null;
  const rated = filters?.rated ?? null;
  const opponentType = filters?.opponentType ?? 'human';
  const opponentStrength = filters?.opponentStrength ?? ANY_RANGE;

  return useQuery({
    queryKey: ['mostPlayedOpenings', normalizedRecency, timeControl, platform, rated, opponentType, opponentStrength.min, opponentStrength.max],
    queryFn: () => statsApi.getMostPlayedOpenings({
      recency: normalizedRecency,
      time_control: timeControl,
      platform: platform,
      rated: rated,
      opponent_type: opponentType,
      opponent_strength: opponentStrength,
    }),
  });
}
