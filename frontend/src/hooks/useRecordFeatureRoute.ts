import { useCallback } from 'react';
import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { USER_PROFILE_QUERY_KEY, useUserProfile } from '@/hooks/useUserProfile';
import { applyRouteWrite, isRouteWriteNeeded } from '@/lib/featureRoute';
import type { FeatureRouteActionRequest, FeatureRouteState, UserProfile } from '@/types/users';

export const FEATURE_ROUTE_MUTATION_KEY = ['feature-route'] as const;
/** Serializes writes so two quick completions reach the server in order. */
const FEATURE_ROUTE_MUTATION_SCOPE = 'feature-route';
/** Length of the YYYY-MM-DD prefix of an ISO timestamp. */
const ISO_DATE_LENGTH = 10;

/**
 * Clients whose profile has to be refetched once their last route write settles.
 * Per client and at module level because three hook instances (recorder, Openings,
 * Train) share one serialized write queue.
 */
const profileRefetchOwed = new WeakSet<QueryClient>();

function patchFeatureRoute(queryClient: QueryClient, featureRoute: FeatureRouteState | null): void {
  queryClient.setQueryData<UserProfile>(USER_PROFILE_QUERY_KEY, (profile) =>
    profile ? { ...profile, feature_route: featureRoute } : profile,
  );
}

/** The profile is being refetched, or is stale and due for a refetch at its next trigger. */
function isProfileRefetchDue(queryClient: QueryClient): boolean {
  if (queryClient.isFetching({ queryKey: USER_PROFILE_QUERY_KEY }) > 0) return true;
  return queryClient.getQueryCache().find({ queryKey: USER_PROFILE_QUERY_KEY })?.isStale() ?? false;
}

/**
 * Record a feature-route completion via POST /users/me/feature-route. Returns a
 * fire-and-forget callback. Three deliberate choices:
 *
 * - The callback no-ops when the route state is missing or corrupt (fail closed),
 *   during impersonation (the server also no-ops), and when the cached state
 *   already has the step done, so render-driven callers cannot loop.
 * - `onMutate` cancels in-flight profile refetches (a stale response must not
 *   undo the write) and patches the cached profile optimistically, so the dot
 *   moves on at once. A refetch that was cancelled or was due is repeated in
 *   `onSettled` after the last write, so the patch never hides a newer profile.
 * - `onSuccess` writes the server state only when this is the last feature-route
 *   mutation (the mutation still counts itself while its callbacks run, TanStack
 *   v5), so an older response cannot revert a newer optimistic patch.
 *
 * No Sentry call (the global MutationCache.onError reports failures) and no
 * trackFeature (completions already live in Postgres; dot rendering is not a user
 * action).
 */
export function useRecordFeatureRoute(): (request: FeatureRouteActionRequest) => void {
  const queryClient = useQueryClient();
  const { data: profile } = useUserProfile();
  const mutation = useMutation<FeatureRouteState | null, Error, FeatureRouteActionRequest>({
    mutationKey: FEATURE_ROUTE_MUTATION_KEY,
    mutationFn: async (request) => {
      const res = await apiClient.post<FeatureRouteState | null>('/users/me/feature-route', request);
      return res.data;
    },
    scope: { id: FEATURE_ROUTE_MUTATION_SCOPE },
    onMutate: async (request) => {
      // Bug fix (WR-02): the cancel below drops an in-flight profile refetch, and the
      // patch marks the whole cached profile fresh (setQueryData resets isInvalidated
      // and dataUpdatedAt). Game counts and the nav lock then stayed stale for another
      // stale time. Remember that a refetch is owed; onSettled repeats it.
      if (isProfileRefetchDue(queryClient)) profileRefetchOwed.add(queryClient);
      await queryClient.cancelQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      const cached = queryClient.getQueryData<UserProfile>(USER_PROFILE_QUERY_KEY);
      if (cached?.feature_route == null) return;
      const today = new Date().toISOString().slice(0, ISO_DATE_LENGTH);
      patchFeatureRoute(
        queryClient,
        applyRouteWrite(cached.feature_route, request, { today, activeDays: cached.active_days }),
      );
    },
    onSuccess: (state) => {
      if (queryClient.isMutating({ mutationKey: FEATURE_ROUTE_MUTATION_KEY }) !== 1) return;
      patchFeatureRoute(queryClient, state);
    },
    onSettled: () => {
      // Only after the last queued write, so the refetch cannot return a state older
      // than a write that is still on its way. Also runs when the write failed.
      if (queryClient.isMutating({ mutationKey: FEATURE_ROUTE_MUTATION_KEY }) !== 1) return;
      if (!profileRefetchOwed.delete(queryClient)) return;
      void queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
    },
  });
  const { mutate } = mutation;
  const state = profile?.feature_route ?? null;
  const impersonated = profile?.impersonation != null;
  return useCallback(
    (request: FeatureRouteActionRequest): void => {
      if (state == null || impersonated || !isRouteWriteNeeded(state, request)) return;
      mutate(request);
    },
    [state, impersonated, mutate],
  );
}
