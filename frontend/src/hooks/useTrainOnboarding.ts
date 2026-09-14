/**
 * useTrainOnboarding — POST /train/onboarding/{step} (Phase 222, D-11/D-12).
 *
 * Stamps one of the three onboarding "seen" watermarks on stepper
 * completion. Mirrors `useTrainSettings.ts`'s mutation `onSuccess` idiom
 * exactly: `queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data)`
 * refreshes the SAME shared cache the PUT already uses, so every consumer
 * of `useTrainSettings()` sees the new watermark with no extra fetch
 * (RESEARCH Finding D). No local `Sentry.captureException` here — the
 * global `MutationCache.onError` (frontend/src/lib/queryClient.ts) already
 * captures every mutation error exactly once.
 *
 * Import note: this hook is consumed by plans 04/05/06 (the intro stepper,
 * the reveal walkthrough, and the score-screen explanation respectively).
 * `npm run knip` will flag it as unused between now and plan 04 landing —
 * expected, not a bug; see 222-01-SUMMARY.md.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import { TRAIN_SETTINGS_QUERY_KEY } from '@/hooks/useTrainSettings';

/** The three onboarding steppers this phase adds (D-11). Literal union, not
 * a bare `string` (CLAUDE.md: never bare `str` for a fixed value set) — the
 * exact three names this plan's planner chose for the path parameter. */
export type OnboardingStep = 'intro' | 'reveal_walkthrough' | 'sr_explained';

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
