/**
 * useTrainSettingsDraft: the ONE local draft of the Train settings row, with the
 * debounced auto-save and the saved / error indicator.
 *
 * Every writer of `PUT /train/settings` on the Train landing edits this draft: the
 * weekday chips and reminder controls (`TrainScheduleSettings`), the per-mode session-size
 * sliders and the blunder-check level picker (`TrainModeSettings`), and a launcher row's
 * "Turn on". The PUT is a full replace of the schedule fields, so two components with
 * their own drafts would overwrite each other's edit; one draft instance (owned by
 * `TrainStartScreen`) means an edit made in the same burst as another rides the same PUT.
 *
 * - The draft is seeded exactly once from the first resolved settings response and never
 *   re-seeded from a later refetch (our own cache write after a save must not reset it).
 * - `update(patch)` marks the draft edited; mounting and seeding never save.
 * - A save fires 600 ms after the last edit, only when the debounced draft differs from
 *   what the server last confirmed.
 * - `onSaved` is called after a save actually persists (see `TrainStartScreen`'s
 *   `onSettingsSaved`); it is held in a ref so a parent re-render with a new callback
 *   identity can never re-fire an in-flight save.
 * - The UI can never produce a draft with both session sizes at 0 (D-05); `update` drops
 *   such a patch, and the server and the DB CHECK back it up.
 *
 * The reminder toggle's "write the draft only after a successful subscribe" exception
 * lives in `TrainScheduleSettings`; it still goes through `update`.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { useDebounce } from '@/hooks/useDebounce';
import { useTrainSettings } from '@/hooks/useTrainSettings';
import type { BlunderCheckLevel, TrainSettingsResponse } from '@/types/train';

export const TRAIN_SETTINGS_SAVE_DEBOUNCE_MS = 600;
export const TRAIN_SETTINGS_SAVED_INDICATOR_MS = 2000;

/** The editable subset of the settings row, local to the Train landing. */
export interface EditableTrainSettings {
  weekdayMask: number;
  puzzlesPerSession: number;
  /** 0 turns the mode off. */
  blunderCheckPerSession: number;
  /** The self-declared level, or null until chosen. */
  blunderCheckLevel: BlunderCheckLevel | null;
  /** Edited by ReminderControls; toggle-ON is written only after a successful subscribe. */
  reminderEnabled: boolean;
  reminderHour: number;
}

export type TrainSettingsPatch =
  | Partial<EditableTrainSettings>
  | ((prev: EditableTrainSettings) => Partial<EditableTrainSettings>);

export type SettingsSaveIndicator = 'idle' | 'saved' | 'error' | 'reminder-error';

export interface TrainSettingsDraftApi {
  /** Null until the settings response has been seeded. */
  draft: EditableTrainSettings | null;
  /** Merges a patch into the draft; pass a function to derive it from the latest draft (toggles). */
  update: (patch: TrainSettingsPatch) => void;
  indicator: SettingsSaveIndicator;
  setIndicator: Dispatch<SetStateAction<SettingsSaveIndicator>>;
  isPending: boolean;
  isError: boolean;
}

/** Both sessions off is rejected server-side (422), so the UI never builds that draft. */
function bothModesOff(next: EditableTrainSettings): boolean {
  return next.puzzlesPerSession === 0 && next.blunderCheckPerSession === 0;
}

function matchesServer(draft: EditableTrainSettings, data: TrainSettingsResponse): boolean {
  return (
    draft.weekdayMask === data.weekday_mask &&
    draft.puzzlesPerSession === data.puzzles_per_session &&
    draft.blunderCheckPerSession === data.blunder_check_per_session &&
    draft.blunderCheckLevel === (data.blunder_check_level ?? null) &&
    draft.reminderEnabled === data.reminder_enabled &&
    draft.reminderHour === data.reminder_hour
  );
}

export function useTrainSettingsDraft({ onSaved }: { onSaved?: () => void } = {}): TrainSettingsDraftApi {
  const { data, isPending, isError, save } = useTrainSettings();

  const [draft, setDraft] = useState<EditableTrainSettings | null>(null);
  const hasEditedRef = useRef(false);
  const [indicator, setIndicator] = useState<SettingsSaveIndicator>('idle');
  const savedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onSavedRef = useRef(onSaved);
  useEffect(() => {
    onSavedRef.current = onSaved;
  }, [onSaved]);

  // Seed the local draft exactly once from the resolved settings, never re-seeded on a
  // later background refetch (e.g. our own cache write after a save).
  useEffect(() => {
    if (data !== undefined && draft === null) {
      setDraft({
        weekdayMask: data.weekday_mask,
        puzzlesPerSession: data.puzzles_per_session,
        blunderCheckPerSession: data.blunder_check_per_session,
        blunderCheckLevel: data.blunder_check_level ?? null,
        reminderEnabled: data.reminder_enabled,
        reminderHour: data.reminder_hour,
      });
    }
  }, [data, draft]);

  const debouncedDraft = useDebounce(draft, TRAIN_SETTINGS_SAVE_DEBOUNCE_MS);

  // Fire the save only once the user has actually edited something, and only when the
  // debounced draft differs from what the server last confirmed: mounting (seed effect
  // above) must never itself trigger a save.
  useEffect(() => {
    if (!hasEditedRef.current || debouncedDraft === null || data === undefined) return;
    if (matchesServer(debouncedDraft, data)) return;
    save(
      {
        weekdayMask: debouncedDraft.weekdayMask,
        puzzlesPerSession: debouncedDraft.puzzlesPerSession,
        blunderCheckPerSession: debouncedDraft.blunderCheckPerSession,
        blunderCheckLevel: debouncedDraft.blunderCheckLevel ?? undefined,
        reminderEnabled: debouncedDraft.reminderEnabled,
        reminderHour: debouncedDraft.reminderHour,
        // Echo the current server value: this debounced save never writes a new intent;
        // only the iOS install-affordance tap does.
        reminderIntentAt: data.reminder_intent_at,
      },
      {
        onSuccess: () => {
          setIndicator('saved');
          if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current);
          savedTimeoutRef.current = setTimeout(() => setIndicator('idle'), TRAIN_SETTINGS_SAVED_INDICATOR_MS);
          onSavedRef.current?.();
        },
        onError: () => {
          setIndicator('error');
        },
      },
    );
  }, [debouncedDraft, data, save]);

  useEffect(() => {
    return () => {
      if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current);
    };
  }, []);

  const update = useCallback((patch: TrainSettingsPatch): void => {
    hasEditedRef.current = true;
    setDraft((prev) => {
      if (prev === null) return prev;
      const next = { ...prev, ...(typeof patch === 'function' ? patch(prev) : patch) };
      return bothModesOff(next) ? prev : next;
    });
  }, []);

  return { draft, update, indicator, setIndicator, isPending, isError };
}
