// ── Detect "this bundle is older than the deployed one" ───────────────────
// The compiled-in build ID (vite.config.ts BUILD_ID) is compared with the
// deployed /version.json at startup and on every resume. Why this exists: the
// installed PWA could run an old bundle indefinitely. /assets/* is immutable
// for a year (an old shell's JS keeps loading with no error), the only other
// auto-reload triggers are controllerchange and vite:preloadError, and an
// already-current service worker makes reg.update() find nothing.

import { SW_UPDATE_DEBOUNCE_MS } from '@/lib/swUpdate';
import { applyHeldUpdateReload, requestUpdateReload } from '@/lib/updateReload';
import { reportStaleBuild, type BuildCheckTrigger } from '@/lib/staleBuildDiagnostics';

/** A hung /version.json fetch must not wedge the checker. */
export const BUILD_VERSION_FETCH_TIMEOUT_MS = 5 * 1000;

/** Returns the deployed build ID, or null for anything that is not a well-formed version.json body. */
export function parseDeployedBuildId(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('buildId' in body)) return null;
  const { buildId } = body;
  return typeof buildId === 'string' && buildId !== '' ? buildId : null;
}

/**
 * Fetches the deployed build ID; null on any failure. Failures here are
 * expected (offline, the deploy window, the dev server answering with
 * index.html) and deliberately skip Sentry per frontend/CLAUDE.md. no-store
 * keeps both the browser HTTP cache and the service worker out of the way.
 */
async function fetchDeployedBuildId(): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), BUILD_VERSION_FETCH_TIMEOUT_MS);
  try {
    const response = await fetch('/version.json', { cache: 'no-store', signal: controller.signal });
    if (response.status !== 200) return null;
    return parseDeployedBuildId(await response.json());
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Builds a checker closed over the running build ID. A factory (not module
 * state) so each caller, and each test, starts with a clean debounce.
 * check() never rejects.
 */
export function createBuildVersionChecker(runningBuildId: string): (trigger: BuildCheckTrigger) => Promise<void> {
  let lastCheckMs: number | null = null;
  let checkInFlight = false;

  return async function check(trigger: BuildCheckTrigger): Promise<void> {
    try {
      // A reload held by a session is applied here, before the debounce: a
      // fetch could learn nothing new and the debounce must not swallow it.
      if (trigger === 'resume' && applyHeldUpdateReload()) return;
      if (trigger === 'resume' && lastCheckMs !== null && Date.now() - lastCheckMs < SW_UPDATE_DEBOUNCE_MS) return;
      if (checkInFlight) return;
      checkInFlight = true;
      try {
        const deployedBuildId = await fetchDeployedBuildId();
        // A failed fetch does not consume the debounce, so the next resume retries.
        if (deployedBuildId === null) return;
        lastCheckMs = Date.now();
        if (deployedBuildId === runningBuildId) return;
        requestUpdateReload({
          reason: 'build-mismatch',
          atStartup: trigger === 'startup',
          beforeReload: () => reportStaleBuild(runningBuildId, deployedBuildId, trigger),
        });
      } finally {
        checkInFlight = false;
      }
    } catch {
      // Contract: never rejects.
    }
  };
}

interface InstallBuildVersionCheckOptions {
  enabled?: boolean;
  runningBuildId?: string;
}

/**
 * Starts the check at page start and on every resume. Inert unless enabled
 * (production builds only by default) and the running build ID is known, so
 * dev and tests never fetch /version.json.
 */
export function installBuildVersionCheck(options: InstallBuildVersionCheckOptions = {}): void {
  const enabled = options.enabled ?? import.meta.env.PROD;
  const runningBuildId: unknown = options.runningBuildId ?? import.meta.env.VITE_BUILD_ID;
  if (!enabled || typeof runningBuildId !== 'string' || runningBuildId === '') return;

  const check = createBuildVersionChecker(runningBuildId);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void check('resume');
  });
  window.addEventListener('focus', () => void check('resume'));
  void check('startup');
}
