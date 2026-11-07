// ── Shared gate for every "a newer build exists" reload ───────────────────
// Both the /version.json mismatch (buildVersionCheck.ts) and the service
// worker takeover (swUpdate.ts) go through requestUpdateReload, because after
// a deploy the resume-time reg.update() installs the new worker, whose
// skipWaiting + clientsClaim fire `controllerchange`: gating only the version
// reload would change nothing. The stale-chunk preload reload
// (stalePreloadReload.ts) stays outside the gate: it fires only once a
// navigation has already failed.

import { useEffect } from 'react';
import { reloadAutomatically } from '@/lib/autoReload';
import { isPlayActive, subscribePlayActive } from '@/lib/playActive';

/** sessionStorage key holding the epoch-ms of the last update reload (both reasons share it). */
export const UPDATE_RELOAD_STORAGE_KEY = 'flawchess:update-reload-at';

/**
 * One update reload per window, across both reasons. It also suppresses the
 * redundant second reload when a version reload is followed moments later by
 * the new worker's controllerchange, and is the loop guard for a startup
 * check that is still mismatched right after a reload. Anything suppressed
 * self-heals at the next resume check after the window.
 */
export const UPDATE_RELOAD_COOLDOWN_MS = 5 * 60 * 1000;

/** Upper bound on how long beforeReload (the Sentry diagnostics) may delay the reload. */
export const BEFORE_RELOAD_TIMEOUT_MS = 3 * 1000;

/**
 * After the session flag drops, wait this long before applying a held reload.
 * Rematch and restored-reveal transitions flip the flag false then true inside
 * one React commit; applying on the false edge would reload mid-transition.
 */
export const SESSION_END_SETTLE_MS = 1000;

export type UpdateReloadReason = 'build-mismatch' | 'sw-update';

export interface UpdateReloadRequest {
  reason: UpdateReloadReason;
  /** True for the check run at page start: a fresh load has no session to protect. */
  atStartup: boolean;
  /** Runs once before the reload; failure, throw or slowness never blocks the reload. */
  beforeReload?: () => Promise<void>;
}

let reloadInFlight = false;

// A runtime reload requested during a session waits here. One slot: all
// requests ask for the same thing (load the newest build).
let heldRequest: UpdateReloadRequest | null = null;
let heldSessionHoldCount = 0;
let settleTimer: ReturnType<typeof setTimeout> | undefined;
let unsubscribePlayActive: (() => void) | null = null;

function readLastReloadMs(): number | null {
  const raw = window.sessionStorage.getItem(UPDATE_RELOAD_STORAGE_KEY);
  if (raw === null) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Stamps the cooldown; false when storage is unavailable. */
function stampReload(nowMs: number): boolean {
  try {
    window.sessionStorage.setItem(UPDATE_RELOAD_STORAGE_KEY, String(nowMs));
    return true;
  } catch {
    return false;
  }
}

function isWithinCooldown(nowMs: number): boolean {
  try {
    const lastMs = readLastReloadMs();
    return lastMs !== null && nowMs - lastMs < UPDATE_RELOAD_COOLDOWN_MS;
  } catch {
    return false;
  }
}

/** Runs beforeReload bounded by BEFORE_RELOAD_TIMEOUT_MS; never rejects. */
async function runBeforeReload(beforeReload: (() => Promise<void>) | undefined): Promise<void> {
  if (beforeReload === undefined) return;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const pending = beforeReload();
    const timeout = new Promise<void>((resolve) => {
      timer = setTimeout(resolve, BEFORE_RELOAD_TIMEOUT_MS);
    });
    await Promise.race([pending, timeout]);
  } catch {
    // Diagnostics must never hold the reload back.
  } finally {
    clearTimeout(timer);
  }
}

async function applyNow(request: UpdateReloadRequest): Promise<void> {
  if (reloadInFlight) return;
  const nowMs = Date.now();
  if (isWithinCooldown(nowMs)) return;
  const stamped = stampReload(nowMs);
  // Without the stamp a persistent mismatch could reload forever, so a
  // mismatch fails closed (stalePreloadReload.ts pattern). A sw-update reload
  // cannot loop (the new worker only takes over once) and is today's
  // behaviour, so it still proceeds.
  if (!stamped && request.reason === 'build-mismatch') return;
  reloadInFlight = true;
  await runBeforeReload(request.beforeReload);
  reloadAutomatically();
}

/**
 * True while a reload must not happen: an immersive screen is mounted (bot
 * game, Train solve screen: the shared playActive flag, not a route check,
 * because /train and /bots also serve idle landing pages) or a component
 * holds the reload through useHoldUpdateReload.
 */
export function isUpdateSessionActive(): boolean {
  return isPlayActive() || heldSessionHoldCount > 0;
}

function applyHeld(): void {
  const request = heldRequest;
  heldRequest = null;
  clearTimeout(settleTimer);
  settleTimer = undefined;
  unsubscribePlayActive?.();
  unsubscribePlayActive = null;
  if (request !== null) void applyNow(request);
}

/** (Re)starts the settle timer; applies the held request only if no session is active when it fires. */
function scheduleSettleCheck(): void {
  if (heldRequest === null) return;
  clearTimeout(settleTimer);
  settleTimer = setTimeout(() => {
    settleTimer = undefined;
    if (!isUpdateSessionActive()) applyHeld();
  }, SESSION_END_SETTLE_MS);
}

function holdRequest(request: UpdateReloadRequest): void {
  // A mismatch (carries diagnostics) replaces a held sw-update; a sw-update
  // never replaces a held mismatch.
  if (heldRequest === null || request.reason === 'build-mismatch') heldRequest = request;
  unsubscribePlayActive ??= subscribePlayActive(scheduleSettleCheck);
}

/**
 * Requests an update reload. Safe to call repeatedly; at most one reload
 * results. A startup request always applies (a fresh load has no session to
 * lose); a runtime request during a session is held until it ends.
 */
export function requestUpdateReload(request: UpdateReloadRequest): void {
  if (!request.atStartup && isUpdateSessionActive()) {
    holdRequest(request);
    return;
  }
  void applyNow(request);
}

/**
 * Applies a held reload if the session is over. Returns whether one was held
 * (so a resume check can skip its fetch: nothing new can be learned, and the
 * resume debounce must not swallow a held reload).
 */
export function applyHeldUpdateReload(): boolean {
  if (heldRequest === null) return false;
  if (!isUpdateSessionActive()) applyHeld();
  return true;
}

/**
 * Holds update reloads while the calling component is mounted, for screens
 * that are not covered by the playActive flag. The Train score screen is local
 * Train.tsx state: a reload there would lose it, and useMarkPlayActive cannot
 * cover it (ProtectedLayout hides the mobile header on that flag).
 */
export function useHoldUpdateReload(): void {
  useEffect(() => {
    heldSessionHoldCount += 1;
    return () => {
      heldSessionHoldCount -= 1;
      scheduleSettleCheck();
    };
  }, []);
}
