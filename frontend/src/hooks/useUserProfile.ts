import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { UserProfile } from '@/types/users';

export function useUserProfile() {
  return useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes
  });
}

/**
 * The single definition of the zero-game test (Phase 224 D-03): true when the
 * account has imported at least one game from either platform. Shared by the
 * Home redirect and the Train games-less copy branch — never re-derive this
 * sum inline elsewhere.
 */
export function hasImportedGames(profile: UserProfile | undefined | null): boolean {
  return (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;
}
