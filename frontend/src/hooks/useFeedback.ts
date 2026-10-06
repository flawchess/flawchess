import { useMutation, useQueryClient } from '@tanstack/react-query';
import { feedbackApi } from '@/api/client';
import { USER_PROFILE_QUERY_KEY } from '@/hooks/useUserProfile';
import type { FeedbackRequest, FeedbackResponse } from '@/types/feedback';

/**
 * TanStack mutation wrapper for POST /api/feedback.
 *
 * Note: no Sentry.captureException in onError — MutationCache.onError in
 * queryClient.ts already captures every mutation failure globally.
 * Adding a second capture here would create duplicate Sentry events (Pitfall 1).
 */
export function useFeedback() {
  const queryClient = useQueryClient();
  return useMutation<FeedbackResponse, Error, FeedbackRequest>({
    mutationFn: feedbackApi.submit,
    onSuccess: () => {
      // SEED-191 #8: a user who has sent feedback from any source is never asked
      // again, so the cached profile (which carries feedback_ask) must refetch.
      void queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
    },
  });
}
