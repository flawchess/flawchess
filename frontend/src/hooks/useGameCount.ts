import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

/**
 * Total count of the user's imported games, across ALL platforms — including
 * `flawchess` (bot-practice) and `pgn` (pasted) rows. This is deliberate
 * on purpose: a user whose only games are bot games must read "You have N
 * games", not "You have 0 games", in the empty state that appears once the
 * analytics defaults flip to Human + Rated.
 *
 * Shared `['gameCount']` query key so Openings and GlobalStats hit the same
 * cached request.
 */
export function useGameCount() {
  return useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/users/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
}

/**
 * Convenience wrapper returning just the count (or null while loading/absent),
 * so a page component (GlobalStats) doesn't carry the optional-chain/nullish
 * branches inline.
 */
export function useGameCountValue(): number | null {
  const { data } = useGameCount();
  return data ? data.count : null;
}
