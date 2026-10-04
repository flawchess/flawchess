// ── Automatic (non-user) page reloads ──────────────────────────────────────
// Quick 261004-rmc: an idle open tab reloads itself after every deploy (the
// hourly service-worker update check, or stale-chunk recovery), and Umami
// recorded each of those reloads as a fresh pageview: prod sessions sitting on
// one path picked up a pageview per release. The reload leaves a marker in
// sessionStorage so the next page load can drop its landing pageview (see
// installUmamiBeforeSend in analytics.ts). User-initiated reloads (error
// boundary button, Analysis) call window.location.reload() directly on purpose.

/** sessionStorage key marking that the next page load came from an automatic reload. */
const AUTO_RELOAD_STORAGE_KEY = 'flawchess:auto-reload';

/** Reload the page on the app's own initiative, not the user's. */
export function reloadAutomatically(): void {
  try {
    window.sessionStorage.setItem(AUTO_RELOAD_STORAGE_KEY, '1');
  } catch {
    // Storage unavailable (privacy mode, quota): the reload matters more than
    // the analytics marker, so reload anyway and accept one extra pageview.
  }
  window.location.reload();
}

/**
 * True when this page load was triggered by reloadAutomatically(). Removes the
 * marker, so it reports true at most once per automatic reload.
 */
export function consumeAutoReloadMarker(): boolean {
  try {
    const marked = window.sessionStorage.getItem(AUTO_RELOAD_STORAGE_KEY) !== null;
    window.sessionStorage.removeItem(AUTO_RELOAD_STORAGE_KEY);
    return marked;
  } catch {
    return false;
  }
}
