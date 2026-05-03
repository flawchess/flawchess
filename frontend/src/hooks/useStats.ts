import { useQuery } from '@tanstack/react-query';
import { statsApi } from '@/api/client';
import type { Platform, Recency, TimeControl, OpponentType, OpponentStrengthRange } from '@/types/api';
import { ANY_RANGE } from '@/lib/opponentStrength';
import { rangeToQueryParams } from '@/lib/opponentStrength';
import type { BookmarkPhaseEntryQuery, BookmarkPhaseEntryResponse } from '@/types/stats';

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

export function useBookmarkPhaseEntryMetrics(
  bookmarks: BookmarkPhaseEntryQuery[],
  filters: {
    recency: Recency | null;
    timeControls: TimeControl[] | null;
    platforms: Platform[] | null;
    rated: boolean | null;
    opponentType: OpponentType;
    opponentStrength: OpponentStrengthRange;
  },
) {
  const normalizedRecency = filters.recency === 'all' ? null : filters.recency;
  const enabled = bookmarks.length > 0;
  // Sort by target_hash to keep query key stable across reorders.
  const hashKey = bookmarks.map(b => `${b.target_hash}:${b.match_side}:${b.color ?? ''}`).sort().join(',');
  const { opponent_gap_min, opponent_gap_max } = rangeToQueryParams(filters.opponentStrength);

  return useQuery<BookmarkPhaseEntryResponse>({
    queryKey: [
      'bookmarkPhaseEntryMetrics',
      hashKey,
      normalizedRecency,
      filters.timeControls,
      filters.platforms,
      filters.rated,
      filters.opponentType,
      filters.opponentStrength.min,
      filters.opponentStrength.max,
    ],
    queryFn: () => statsApi.getBookmarkPhaseEntryMetrics({
      bookmarks,
      recency: normalizedRecency,
      time_control: filters.timeControls,
      platform: filters.platforms,
      rated: filters.rated,
      opponent_type: filters.opponentType,
      opponent_gap_min,
      opponent_gap_max,
    }),
    enabled,
  });
}
