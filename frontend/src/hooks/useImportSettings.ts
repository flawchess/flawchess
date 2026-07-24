import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { TimeControl } from '@/types/api';

/** Allowed backlog import caps (mirrors the backend's `game_cap` CHECK constraint / Literal). */
export type GameCap = 1000 | 3000 | 5000;

/** Per-user import settings: which time controls to import and the backlog cap per (platform, TC). */
export interface ImportSettings {
  tc_bullet: boolean;
  tc_blitz: boolean;
  tc_rapid: boolean;
  tc_classical: boolean;
  game_cap: GameCap;
  /** Count of ALL imported games keyed by platform then time control, e.g. { "chess.com": { "blitz": 2705 } }. */
  imported_counts: Record<string, Record<string, number>>;
}

/** PATCH request body for /users/me/import-settings — all TC toggles + game_cap required (no partial update). */
export type ImportSettingsUpdate = Omit<ImportSettings, 'imported_counts'>;

export const IMPORT_SETTINGS_QUERY_KEY = ['import-settings'] as const;

/** The subset of ImportSettings/ImportSettingsUpdate keys that hold a per-TC boolean toggle. */
export type TcSettingsKey = `tc_${TimeControl}`;

/** Maps a TimeControl to its ImportSettings/ImportSettingsUpdate boolean field name. */
export function tcSettingsKey(tc: TimeControl): TcSettingsKey {
  return `tc_${tc}`;
}

/** Fetch the authenticated user's import settings (TC toggles + game_cap + imported_counts). */
export function useImportSettings() {
  return useQuery<ImportSettings, Error>({
    queryKey: IMPORT_SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get<ImportSettings>('/users/me/import-settings');
      return response.data;
    },
  });
}

/**
 * Auto-save PATCH for import settings (D-09 — no Save button, no dirty state).
 * Optimistically writes the new settings into the ['import-settings'] cache so
 * toggles feel instant; rolls back to the pre-mutation snapshot on error
 * (UI-SPEC error backstop). Manual apiClient calls are covered by the global
 * TanStack Query MutationCache.onError handler per CLAUDE.md — no duplicate
 * Sentry.captureException here.
 */
export function useUpdateImportSettings() {
  const queryClient = useQueryClient();
  return useMutation<
    ImportSettings,
    Error,
    ImportSettingsUpdate,
    { previous: ImportSettings | undefined }
  >({
    mutationFn: async (update) => {
      const response = await apiClient.patch<ImportSettings>('/users/me/import-settings', update);
      return response.data;
    },
    onMutate: async (update) => {
      await queryClient.cancelQueries({ queryKey: IMPORT_SETTINGS_QUERY_KEY });
      const previous = queryClient.getQueryData<ImportSettings>(IMPORT_SETTINGS_QUERY_KEY);
      queryClient.setQueryData<ImportSettings>(IMPORT_SETTINGS_QUERY_KEY, (old) =>
        old ? { ...old, ...update } : old,
      );
      return { previous };
    },
    onError: (_err, _update, context) => {
      if (context?.previous) {
        queryClient.setQueryData(IMPORT_SETTINGS_QUERY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: IMPORT_SETTINGS_QUERY_KEY });
    },
  });
}
