import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { USER_PROFILE_QUERY_KEY } from '@/hooks/useUserProfile';
import type { FeedbackAskAction, FeedbackAskView, UserProfile } from '@/types/users';

/** Serializes view -> snooze/done so a fast click cannot overtake the in-flight view. */
const FEEDBACK_ASK_MUTATION_SCOPE = 'feedback-ask';

function patchFeedbackAsk(
  queryClient: ReturnType<typeof useQueryClient>,
  feedbackAsk: FeedbackAskView,
): void {
  queryClient.setQueryData<UserProfile>(USER_PROFILE_QUERY_KEY, (profile) =>
    profile ? { ...profile, feedback_ask: feedbackAsk } : profile,
  );
}

/**
 * Phase 234 (SEED-191): report a view, snooze or done for Hilda's milestone
 * feedback ask via POST /users/me/feedback-ask. Three deliberate choices:
 *
 * - `scope` serializes the calls, so a fast "Maybe later" click is sent after
 *   the in-flight view rather than racing it.
 * - snooze/done hide the bubble immediately (SEED-191 #6): `onMutate` cancels
 *   in-flight profile refetches (a stale response must not re-show the ask)
 *   and patches the cached `feedback_ask` to inactive; `onSuccess` then
 *   replaces it with the server's answer.
 * - a view never touches the cache. A scoped mutation runs `onMutate`
 *   immediately even while it waits behind an in-flight view, so a view
 *   response that patched `active: true` would resurrect a bubble the user
 *   just dismissed.
 *
 * No Sentry call: the global MutationCache.onError already reports failures.
 */
export function useFeedbackAsk() {
  const queryClient = useQueryClient();
  return useMutation<FeedbackAskView, Error, FeedbackAskAction>({
    mutationFn: async (action) => {
      const res = await apiClient.post<FeedbackAskView>('/users/me/feedback-ask', { action });
      return res.data;
    },
    scope: { id: FEEDBACK_ASK_MUTATION_SCOPE },
    onMutate: async (action) => {
      if (action === 'view') return;
      await queryClient.cancelQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      patchFeedbackAsk(queryClient, { active: false });
    },
    onSuccess: (view, action) => {
      // See the docstring: a view response must never resurrect a dismissed bubble.
      if (action === 'view') return;
      patchFeedbackAsk(queryClient, view);
    },
  });
}
