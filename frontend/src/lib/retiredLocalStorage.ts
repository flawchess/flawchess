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
