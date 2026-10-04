import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { TRAIN_LEADERBOARD_QUERY_KEY } from '@/hooks/useTrainLeaderboard';
import type { UserProfile } from '@/types/users';

export const USER_PROFILE_QUERY_KEY = ['userProfile'] as const;

export function useUserProfile() {
  return useQuery<UserProfile>({
    queryKey: USER_PROFILE_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes
  });
}

/**
 * Phase 230 D-16: persist the weekly-leaderboard opt-out through the profile
 * PUT. The response is the full profile, so it replaces the cached profile
 * directly (the switch reads the server's answer), and the cached boards are
 * invalidated so the landing re-ranks without a reload. No Sentry call: the
 * global MutationCache.onError already reports failed mutations.
 */
export function useSetLeaderboardHidden() {
  const queryClient = useQueryClient();
  return useMutation<UserProfile, Error, boolean>({
    mutationFn: async (hidden) => {
      const res = await apiClient.put<UserProfile>('/users/me/profile', {
        leaderboard_hidden: hidden,
      });
      return res.data;
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile);
      void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY });
    },
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
