/**
 * useTrainSettings — GET/PUT /train/settings.
 *
 * The mutation reads the browser's IANA timezone at CALL TIME via
 * `Intl.DateTimeFormat().resolvedOptions().timeZone` — captured on
 * every save, never surfaced or made editable in the UI. On success it
 * writes the fresh row straight into this hook's own query cache
 * (`queryClient.setQueryData`) and invalidates
 * `TRAIN_PROGRESS_QUERY_KEY` — a changed `weekday_mask` can shift
 * `current_week_required` and advance the streak snapshot, so a stale
 * progress cache could show a contradictory streak / this-week hint.
 *
 * Does NOT call `Sentry.captureException` on a failed save — the global
 * `MutationCache.onError` (frontend/src/lib/queryClient.ts) already captures
 * every mutation error exactly once.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import { TRAIN_PROGRESS_QUERY_KEY } from '@/hooks/useTrainProgress';
import type { TrainSettingsResponse, TrainSettingsUpdate } from '@/types/train';

/** The shared query key for GET /train/settings. */
export const TRAIN_SETTINGS_QUERY_KEY = ['train', 'settings'] as const;

export interface TrainSettingsDraft {
  weekdayMask: number;
  puzzlesPerSession: number;
  /** Full-replace PUT body: every field (including the nullable
   * `reminderIntentAt`) must be sent, or every save 422s. */
  reminderEnabled: boolean;
  reminderHour: number;
  reminderIntentAt: string | null;
}

/**
 * `options.enabled` lets a caller gate the request off, mirroring
 * `useTrainProgress`'s pattern. `ProtectedLayout` mounts
 * `useReminderResurface` app-wide and passes a guest gate: guests have no
 * reminder slot or push subscription, so there is nothing to fetch for them.
 * The Train-page call sites (`useTrainReminderSlot`, `TrainScheduleSettings`)
 * keep the default `enabled: true`.
 */
export function useTrainSettings(options?: { enabled?: boolean }) {
  const queryClient = useQueryClient();

  const query = useQuery<TrainSettingsResponse>({
    queryKey: TRAIN_SETTINGS_QUERY_KEY,
    queryFn: trainApi.getSettings,
    enabled: options?.enabled ?? true,
  });

  const mutation = useMutation({
    mutationFn: ({
      weekdayMask,
      puzzlesPerSession,
      reminderEnabled,
      reminderHour,
      reminderIntentAt,
    }: TrainSettingsDraft) => {
      const body: TrainSettingsUpdate = {
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        weekday_mask: weekdayMask,
        puzzles_per_session: puzzlesPerSession,
        reminder_enabled: reminderEnabled,
        reminder_hour: reminderHour,
        reminder_intent_at: reminderIntentAt,
      };
      return trainApi.updateSettings(body);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data);
      void queryClient.invalidateQueries({ queryKey: TRAIN_PROGRESS_QUERY_KEY });
    },
  });

  return {
    ...query,
    save: mutation.mutate,
    isSaving: mutation.isPending,
    isSaveError: mutation.isError,
    isSaveSuccess: mutation.isSuccess,
  };
}
