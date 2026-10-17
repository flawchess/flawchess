/**
 * useTrainOnboarding: POST /train/onboarding/{step}.
 *
 * Stamps one onboarding step: the intro and score-explanation "seen"
 * watermarks on stepper completion, or one finished part of the reveal tour
 * (`reveal_tour_1..3`, which advances the server's forward-only
 * `reveal_tour_stage`). Mirrors `useTrainSettings.ts`'s mutation `onSuccess`
 * idiom exactly: `queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data)`
 * refreshes the SAME shared cache the PUT already uses, so every consumer
 * of `useTrainSettings()` sees the new watermark with no extra fetch.
 * No local `Sentry.captureException` here: the
 * global `MutationCache.onError` (frontend/src/lib/queryClient.ts) already
 * captures every mutation error exactly once.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import { TRAIN_SETTINGS_QUERY_KEY } from '@/hooks/useTrainSettings';

/** One finished part of the first-reveal tour; part N maps to
 * the server stage N. */
export type RevealTourStep = 'reveal_tour_1' | 'reveal_tour_2' | 'reveal_tour_3';

/** Mirrors the server's `OnboardingStep` Literal exactly (the server answers
 * any other step with a 422). Literal union, not a bare `string` (CLAUDE.md). */
export type OnboardingStep = 'intro' | 'sr_explained' | RevealTourStep;

export function useTrainOnboarding(): { stamp: (step: OnboardingStep) => void; isPending: boolean } {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: trainApi.stampOnboarding,
    onSuccess: (data) => {
      queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data);
    },
  });

  return { stamp: mutation.mutate, isPending: mutation.isPending };
}
