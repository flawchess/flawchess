/**
 * maiaPageKillSentinel — makes a silent page kill visible in Sentry
 * (SEED-158, 2026-09-07).
 *
 * The failure this exists for: iOS Safari terminates the whole WebContent
 * process when a page crosses WebKit's per-page memory limit. Nothing in the
 * page runs after that — no `error` event, no rejected promise, no Sentry
 * event, not even a console line (and iOS has no reachable console without a
 * Mac). On the reference iPhone 14 Pro, Maia on /analysis produced exactly
 * this: the chart renders, the user steps through a few moves, the tab dies.
 * The only place that survives the kill is storage, so this module keeps a
 * small record there while Maia is running in the foreground and reports it
 * on the NEXT page load, the way `/maia-diag.html`'s localStorage journal did
 * during the on-device bisect.
 *
 * Contract:
 *  - `armMaiaPageKillSentinel()` is called by `maiaWorkerHost.ts` on the
 *    worker's `ready` message; `noteMaiaDispatch()` on every `analyze`
 *    dispatch; `disarmMaiaPageKillSentinel()` whenever the worker is
 *    terminated (last lease released, fatal error, respawn).
 *  - The record is REMOVED on `pagehide` (a normal navigation, reload, or
 *    tab close) and whenever the document goes hidden, and re-written when it
 *    becomes visible again with the worker still alive. So a record that is
 *    still present on the next load means: the previous page session ended
 *    while it was in the FOREGROUND with Maia active and without the browser
 *    ever telling the page — a kill, not a background tab discard (Chrome
 *    discards only hidden tabs, without firing `pagehide`) and not an
 *    ordinary close.
 *  - `reportMaiaPageKillFromPreviousSession()` runs once at startup
 *    (`main.tsx`, after Sentry is initialised): if a record exists it is
 *    captured with fixed grouping (variable data in `contexts`/`tags`, never
 *    in the message — CLAUDE.md Sentry rules) and removed.
 *
 * Not iOS-specific: an Android low-memory kill or a desktop GPU-process crash
 * that takes the tab with it leaves the same trace. The `ios` tag splits the
 * populations in the dashboard.
 */

import * as Sentry from '@sentry/react';
import { isIosWebKit } from './iosWebKit';
import { readDeviceContext } from '@/lib/maiaWorkerErrors';

const STORAGE_KEY = 'flawchess:maia:page-session';
/** Fixed Sentry message (grouping rule): everything variable travels in `contexts`/`tags`. */
const SENTRY_MESSAGE_PAGE_KILLED = 'Maia worker: page was killed while Maia was active';
const SENTRY_SOURCE = 'maia-page-kill-sentinel';
const SENTRY_FAILURE_TAG = 'page-killed';

interface MaiaPageSession {
  /** `Date.now()` when the worker reported `ready`. */
  armedAt: number;
  backend: 'webgpu' | 'wasm';
  numThreads: number;
  ios: boolean;
  /** Route the worker was armed on (`/analysis` vs `/bots`). */
  pathname: string;
  /** `analyze` dispatches since `armedAt`. */
  dispatches: number;
  /** The most recent dispatch — the last thing Maia was doing before a kill. */
  last: { at: number; batch: number; fen: string } | null;
}

/** In-memory copy while the worker is alive; `null` when disarmed. */
let active: MaiaPageSession | null = null;
let listenersInstalled = false;
/** One-line summary of the previous session's kill, for the dev badge (`null` when there was none). */
let previousKillSummary: string | null = null;

function isDocumentHidden(): boolean {
  try {
    return document.visibilityState === 'hidden';
  } catch {
    return false;
  }
}

function readPathname(): string {
  try {
    return window.location.pathname;
  } catch {
    return 'unknown';
  }
}

/** Persists `active` while the page is visible; removes the record otherwise. Never throws. */
function persist(): void {
  try {
    if (active && !isDocumentHidden()) localStorage.setItem(STORAGE_KEY, JSON.stringify(active));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage unavailable (private mode / quota): the sentinel is best-effort.
  }
}

function removeRecord(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // best-effort
  }
}

/**
 * `pagehide` fires reliably on iOS Safari for every ordinary end of a page
 * (unlike `beforeunload`/`unload`, see `instrument.ts`). A hidden document
 * can be discarded or killed in the background without any event, so the
 * record is dropped on hide and restored on show — only a FOREGROUND death
 * leaves it behind.
 */
function installListeners(): void {
  if (listenersInstalled || typeof window === 'undefined') return;
  listenersInstalled = true;
  window.addEventListener('pagehide', removeRecord);
  document.addEventListener('visibilitychange', persist);
}

/** Called on the worker's `ready` message: starts (or restarts, after a respawn) the record. */
export function armMaiaPageKillSentinel(info: { backend: 'webgpu' | 'wasm'; numThreads: number }): void {
  active = {
    armedAt: Date.now(),
    backend: info.backend,
    numThreads: info.numThreads,
    ios: isIosWebKit(),
    pathname: readPathname(),
    dispatches: 0,
    last: null,
  };
  installListeners();
  persist();
}

/** Called on every `analyze` dispatch — the record always names the last thing Maia was asked to do. */
export function noteMaiaDispatch(fen: string, batch: number): void {
  if (!active) return;
  active.dispatches += 1;
  active.last = { at: Date.now(), batch, fen };
  persist();
}

/** Called whenever the worker is terminated: nothing is running, so nothing can be killed. */
export function disarmMaiaPageKillSentinel(): void {
  active = null;
  removeRecord();
}

function readPreviousSession(): MaiaPageSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return null;
    return parsed as MaiaPageSession;
  } catch {
    return null;
  }
}

/**
 * Startup check (once per page load, after Sentry is initialised): a
 * leftover record means the previous page session died in the foreground
 * with Maia active. Captures it, clears it, and returns a one-line summary
 * for the dev badge (`null` when there was nothing to report).
 */
export function reportMaiaPageKillFromPreviousSession(): string | null {
  const session = readPreviousSession();
  removeRecord();
  if (!session) return null;
  const now = Date.now();
  const sinceLastDispatchMs = session.last ? now - session.last.at : null;
  Sentry.captureException(new Error(SENTRY_MESSAGE_PAGE_KILLED), {
    tags: {
      source: SENTRY_SOURCE,
      backend: session.backend,
      maia_failure: SENTRY_FAILURE_TAG,
      ios: String(session.ios),
    },
    contexts: {
      maia_page_kill: {
        ...session,
        sessionAgeMs: now - session.armedAt,
        sinceLastDispatchMs,
      },
      engine_device: readDeviceContext(session.numThreads),
    },
  });
  previousKillSummary =
    `KILLED last session: ${session.backend} t=${session.numThreads} ` +
    `after ${session.dispatches} dispatches, last batch=${session.last?.batch ?? '-'}`;
  return previousKillSummary;
}

/** The summary `reportMaiaPageKillFromPreviousSession()` produced this page load, for the dev badge. */
export function previousMaiaPageKillSummary(): string | null {
  return previousKillSummary;
}

/** Test-only: clears in-memory state (listeners stay installed; they are idempotent). */
export function resetMaiaPageKillSentinelForTests(): void {
  active = null;
  previousKillSummary = null;
  removeRecord();
}
