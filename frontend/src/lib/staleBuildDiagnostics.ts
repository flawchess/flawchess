// ── Evidence for "why was this client running an old build?" ─────────────
// The installed PWA intermittently showed a weeks-old build and the cause on
// the owner's phone is unconfirmed. Before each version-mismatch reload this
// sends ONE Sentry event describing the page, the service worker and the
// html-shell cache, so the next occurrences carry the answer.
//
// Everything here is best-effort and bounded: collection or flush failing or
// stalling must never hold the reload back (BEFORE_RELOAD_TIMEOUT_MS in
// updateReload.ts is the outer bound; the two inner bounds sum below it).

import * as Sentry from '@sentry/react';
import { HTML_SHELL_CACHE_NAME } from '@/lib/htmlShellCache';

export type BuildCheckTrigger = 'startup' | 'resume';

/** Fixed (no variables) so every event groups into one Sentry issue. Must match none of the ignoreErrors patterns. */
export const STALE_BUILD_SENTRY_MESSAGE = 'Stale frontend build detected by version check';

/** Bound on the async collection (service worker registration + cache reads). */
export const CACHE_COLLECT_TIMEOUT_MS = 800;

/** Bound on flushing the event to Sentry before the page is replaced. */
export const SENTRY_FLUSH_TIMEOUT_MS = 1200;

/** Legacy per-URL html-shell caches can hold many entries; the count stays true. */
export const MAX_REPORTED_SHELL_ENTRIES = 20;

type CollectionStatus = 'complete' | 'timed_out' | 'failed';

interface SyncFields {
  page_age_ms?: number;
  navigation_type?: string;
  transfer_size?: number;
  sw_controller?: boolean;
}

interface AsyncFields {
  sw_active_state?: string | null;
  sw_waiting_state?: string | null;
  html_shell_entry_count?: number;
  // Strings, not objects: Sentry normalizes contexts to depth 3, so an array
  // of objects would arrive as `[Object]`.
  html_shell_entries?: string[];
}

const TIMED_OUT = Symbol('timed_out');

/** Resolves with the promise's value, or TIMED_OUT after `ms`. A rejection propagates. */
async function raceTimeout<T>(promise: Promise<T>, ms: number): Promise<T | typeof TIMED_OUT> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<typeof TIMED_OUT>((resolve) => {
    timer = setTimeout(() => resolve(TIMED_OUT), ms);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

function collectSyncFields(): SyncFields {
  const fields: SyncFields = {};
  try {
    fields.page_age_ms = Math.round(Date.now() - performance.timeOrigin);
    if (typeof performance.getEntriesByType === 'function') {
      const entry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
      if (entry !== undefined) {
        fields.navigation_type = entry.type;
        fields.transfer_size = entry.transferSize;
      }
    }
  } catch {
    // Partial diagnostics are still useful.
  }
  try {
    fields.sw_controller = Boolean(navigator.serviceWorker?.controller);
  } catch {
    // Same: leave the field out.
  }
  return fields;
}

/** Pathname only: legacy html-shell keys can hold /auth/reset-password?token=<JWT>. */
function pathnameOf(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return '[unparseable]';
  }
}

async function collectServiceWorkerFields(into: AsyncFields): Promise<void> {
  const registration = await navigator.serviceWorker.getRegistration();
  into.sw_active_state = registration?.active?.state ?? null;
  into.sw_waiting_state = registration?.waiting?.state ?? null;
}

async function collectHtmlShellFields(into: AsyncFields): Promise<void> {
  if (typeof caches === 'undefined') return;
  // has() first so reading never creates the cache as a side effect.
  if (!(await caches.has(HTML_SHELL_CACHE_NAME))) {
    into.html_shell_entry_count = 0;
    into.html_shell_entries = [];
    return;
  }
  const cache = await caches.open(HTML_SHELL_CACHE_NAME);
  const keys = await cache.keys();
  into.html_shell_entry_count = keys.length;
  const entries: string[] = [];
  into.html_shell_entries = entries;
  for (const key of keys.slice(0, MAX_REPORTED_SHELL_ENTRIES)) {
    const response = await cache.match(key);
    entries.push(`${pathnameOf(key.url)} @ ${response?.headers.get('date') ?? 'no-date'}`);
  }
}

/** Runs one collector so its failure cannot lose the others' results; true when it threw. */
async function runCollector(collector: Promise<void>): Promise<boolean> {
  try {
    await collector;
    return false;
  } catch {
    return true;
  }
}

/** Fills `into` as results arrive, so a timeout still reports what was gathered. */
async function collectAsyncFields(into: AsyncFields): Promise<CollectionStatus> {
  const collectors = [
    runCollector(Promise.resolve().then(() => collectServiceWorkerFields(into))),
    runCollector(Promise.resolve().then(() => collectHtmlShellFields(into))),
  ];
  const raced = await raceTimeout(Promise.all(collectors), CACHE_COLLECT_TIMEOUT_MS);
  if (raced === TIMED_OUT) return 'timed_out';
  return raced.some(Boolean) ? 'failed' : 'complete';
}

/** Sends the single pre-reload Sentry event. Never rejects. */
export async function reportStaleBuild(
  runningBuildId: string,
  deployedBuildId: string,
  trigger: BuildCheckTrigger,
): Promise<void> {
  try {
    const syncFields = collectSyncFields();
    const asyncFields: AsyncFields = {};
    let collection: CollectionStatus = 'failed';
    try {
      collection = await collectAsyncFields(asyncFields);
    } catch {
      collection = 'failed';
    }
    // Snapshot: a late-resolving collector must not mutate an event in flight.
    const snapshot: AsyncFields = {
      ...asyncFields,
      ...(asyncFields.html_shell_entries ? { html_shell_entries: [...asyncFields.html_shell_entries] } : {}),
    };
    try {
      Sentry.captureMessage(STALE_BUILD_SENTRY_MESSAGE, {
        // Expected after every deploy for clients that were open across it, not an error.
        level: 'info',
        tags: { source: 'build-version-check', trigger },
        contexts: {
          stale_build: {
            running_build_id: runningBuildId,
            deployed_build_id: deployedBuildId,
            collection,
            ...syncFields,
            ...snapshot,
          },
        },
      });
      await raceTimeout(Sentry.flush(SENTRY_FLUSH_TIMEOUT_MS), SENTRY_FLUSH_TIMEOUT_MS);
    } catch {
      // A failing Sentry call must not hold the reload back.
    }
  } catch {
    // Never reject.
  }
}
