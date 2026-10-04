import { useQuery } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { TrainLeaderboardResponse } from '@/types/train';

/**
 * Query key for GET /train/leaderboard (Phase 230). The landing variant uses
 * it as-is; the score-screen variant extends it with `'session'` and the id,
 * so invalidating this prefix refreshes both (TrainDevClock, the week rollover).
 */
export const TRAIN_LEADERBOARD_QUERY_KEY = ['train', 'leaderboard'] as const;

interface UseTrainLeaderboardOptions {
  /**
   * Omitted (undefined): the Train landing card. A number: the score screen,
   * which asks the server for `rank_without_session` of that session.
   * `null`: the session id is not known yet, the query stays disabled.
   */
  sessionId?: number | null;
}

/**
 * GET /train/leaderboard, both weekly boards in one payload.
 *
 * Landing variant: `refetchOnMount: 'always'`. Done after a session unmounts
 * and remounts the landing, so every return shows fresh standings without the
 * page having to invalidate anything (RESEARCH Pattern 6). Score-screen
 * variant: staleTime 0 and its own key, because the before/after rank is only
 * meaningful when read at the same moment as the finished session.
 *
 * No polling interval: the board refreshes on mount, on the week rollover
 * (card-side invalidation) and on dev-clock changes. No Sentry capture here:
 * the global QueryCache.onError already reports failed queries.
 */
export function useTrainLeaderboard(options?: UseTrainLeaderboardOptions) {
  const sessionId = options?.sessionId;
  const isLanding = sessionId === undefined;
  return useQuery<TrainLeaderboardResponse>({
    queryKey: isLanding
      ? TRAIN_LEADERBOARD_QUERY_KEY
      : [...TRAIN_LEADERBOARD_QUERY_KEY, 'session', sessionId],
    queryFn: () => trainApi.getLeaderboard(sessionId ?? undefined),
    refetchOnMount: isLanding ? 'always' : true,
    staleTime: isLanding ? undefined : 0,
    enabled: isLanding || sessionId !== null,
  });
}
