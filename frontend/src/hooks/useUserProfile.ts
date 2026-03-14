import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();

  return useMutation<UserProfile, Error, Partial<UserProfile>>({
    mutationFn: async (data) => {
      const res = await apiClient.put<UserProfile>('/users/me/profile', data);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['userProfile'], data);
    },
  });
}
