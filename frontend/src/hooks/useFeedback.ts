import { useMutation } from '@tanstack/react-query';
import { feedbackApi } from '@/api/client';
import type { FeedbackRequest, FeedbackResponse } from '@/types/feedback';

/**
 * TanStack mutation wrapper for POST /api/feedback.
 *
 * Note: no Sentry.captureException in onError — MutationCache.onError in
 * queryClient.ts already captures every mutation failure globally.
 * Adding a second capture here would create duplicate Sentry events (Pitfall 1).
 */
export function useFeedback() {
  return useMutation<FeedbackResponse, Error, FeedbackRequest>({
    mutationFn: feedbackApi.submit,
  });
}
