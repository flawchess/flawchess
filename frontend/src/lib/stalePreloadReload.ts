// ── Stale-chunk recovery after a deploy ───────────────────────────────────
// FLAWCHESS-C0: a tab opened before a deploy still references the previous
// build's content-hashed chunks. Those files are gone after the deploy, so the
// next lazy route (e.g. /activity) fails with "Unable to preload CSS for ..."
// or "Failed to fetch dynamically imported module" and lands on the error
// boundary. Vite dispatches a cancelable `vite:preloadError` event for exactly
// this case; reloading picks up the new index.html and its current chunks.
// Extracted from main.tsx so it is unit-testable (see swUpdate.ts).

/** sessionStorage key holding the epoch-ms of the last recovery reload. */
export const PRELOAD_RELOAD_STORAGE_KEY = 'flawchess:preload-reload-at';

/**
 * A second preload failure within this window after a recovery reload means
 * the reload did not help (asset host down, a broken build), so the error is
 * let through to the error boundary and Sentry instead of reload-looping. A
 * cooldown rather than a one-shot flag, so a later deploy in the same tab
 * session can still self-heal.
 */
export const PRELOAD_RELOAD_COOLDOWN_MS = 60 * 1000;

function readLastReloadMs(): number | null {
  const raw = window.sessionStorage.getItem(PRELOAD_RELOAD_STORAGE_KEY);
  if (raw === null) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Handles one `vite:preloadError` event: reloads the page once per cooldown
 * window, otherwise leaves the event alone so Vite rethrows the error.
 */
export function handleVitePreloadError(event: Event, nowMs: number = Date.now()): void {
  try {
    const lastReloadMs = readLastReloadMs();
    if (lastReloadMs !== null && nowMs - lastReloadMs < PRELOAD_RELOAD_COOLDOWN_MS) return;
    window.sessionStorage.setItem(PRELOAD_RELOAD_STORAGE_KEY, String(nowMs));
  } catch {
    // Storage unavailable (privacy mode, quota): without the guard a reload
    // could loop forever, so fail to reporting the error instead.
    return;
  }
  event.preventDefault();
  window.location.reload();
}

/** Registers the stale-chunk recovery listener. Call once at startup. */
export function installStalePreloadReload(): void {
  window.addEventListener('vite:preloadError', (event) => handleVitePreloadError(event));
}
