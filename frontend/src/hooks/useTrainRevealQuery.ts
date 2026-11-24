/**
 * useTrainRevealQuery: the post-solve reveal GET, shared by TrainReveal and
 * TrainRevealGameFooter so both read one cache entry (one fetch per puzzle).
 *
 * The cache key `['train-reveal', sessionId, position]` is also seeded by tests and read
 * by the solve screen's restore path, so it must not change.
 */

import { useQuery } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { PuzzleRevealResponse } from '@/types/train';

/**
 * `enabled` is the caller's post-solve gate (`verdict !== null`): the query stays off until the
 * solve POST has landed, so no answer-key data is reachable before that.
 */
export function useTrainRevealQuery(
  sessionId: number | null,
  position: number,
  enabled: boolean,
): UseQueryResult<PuzzleRevealResponse> {
  return useQuery<PuzzleRevealResponse>({
    queryKey: ['train-reveal', sessionId, position],
    queryFn: () => trainApi.revealPuzzle(sessionId as number, position),
    enabled: enabled && sessionId !== null,
    staleTime: Infinity, // the answer key never changes once solved
  });
}
