/**
 * Prefix of the per-bookmark "Include in opening results" toggle keys, retired in
 * Phase 242 (D-16) together with the toggle itself.
 */
const RETIRED_BOOKMARK_CHART_KEY_PREFIX = 'bookmark-chart-enabled-';

/**
 * One-time cleanup of the retired bookmark chart toggle keys. Collects the matching
 * keys first (removing while iterating shifts the indexes), then removes them.
 * Best-effort: private-mode or locked-down storage can throw, which is expected and
 * not worth a Sentry event, so any access error returns 0.
 */
export function removeRetiredBookmarkChartKeys(storage: Storage = window.localStorage): number {
  try {
    const retired: string[] = [];
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key !== null && key.startsWith(RETIRED_BOOKMARK_CHART_KEY_PREFIX)) retired.push(key);
    }
    for (const key of retired) storage.removeItem(key);
    return retired.length;
  } catch {
    return 0;
  }
}

/** Prefix of the per-device dot flags (`user_flag:<email>:<name>`), retired in Phase 255 (D-04). */
export const RETIRED_DOT_FLAG_KEY_PREFIX = 'user_flag:';

/** The two Openings sidebar hint keys, retired in Phase 255 (D-07). */
export const RETIRED_DOT_HINT_KEYS = ['played-as-hint-dismissed', 'filters-hint-dismissed'] as const;

function isRetiredDotKey(key: string): boolean {
  return key.startsWith(RETIRED_DOT_FLAG_KEY_PREFIX) || (RETIRED_DOT_HINT_KEYS as readonly string[]).includes(key);
}

/**
 * One-time cleanup of the per-device dot flags retired by phase 255: the route
 * state moved server-side (D-04) and the Openings hint keys are no longer read.
 * Same collect-then-remove shape and best-effort error handling as
 * removeRetiredBookmarkChartKeys; returns the number of keys removed.
 */
export function removeRetiredDotKeys(storage: Storage = window.localStorage): number {
  try {
    const retired: string[] = [];
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key !== null && isRetiredDotKey(key)) retired.push(key);
    }
    for (const key of retired) storage.removeItem(key);
    return retired.length;
  } catch {
    return 0;
  }
}
