import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EnqueueTier1Response } from '@/types/api';

/**
 * Mutation to enqueue a single game for Stockfish full eval (tier-1, user-triggered).
 *
 * On success, invalidates ['imports', 'eval-coverage'] so the coverage badge
 * updates within one render cycle without waiting for the 3s poll (RESEARCH.md Pitfall 5).
 *
 * @param gameId - the game to enqueue
 */
export function useTier1Enqueue(gameId: number) {
  const queryClient = useQueryClient();
  return useMutation<EnqueueTier1Response, Error, void>({
    mutationFn: async () => {
      const response = await apiClient.post<EnqueueTier1Response>(
        `/imports/eval/tier1/${gameId}`,
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['imports', 'eval-coverage'] });
      // Invalidate the games list so the card refetches and reflects the new
      // analysis_state once the eval completes (prefix match covers all param variants).
      void queryClient.invalidateQueries({ queryKey: ['library-games'] });
    },
  });
}
