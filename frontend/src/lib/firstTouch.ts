/**
 * First-touch acquisition attribution (growth report 2026-09-15, item 16).
 *
 * On the first page load in this browser, remember where the visitor came
 * from: the external referrer host, the utm_* tags, and the landing pathname.
 * `useFirstTouchSync` submits it once, right after the visitor gets a token
 * (guest start, register, Google sign-in); the backend only records it on a
 * freshly created account and never overwrites an earlier record.
 *
 * Deliberately stores no full URLs: the referrer is reduced to its host and the
 * landing page to its pathname, so no query string or fragment (the Google
 * OAuth callback carries `#token=<JWT>`) can ever reach the database.
 */

export const FIRST_TOUCH_STORAGE_KEY = 'first_touch';

/** Paths that are mid-auth hops, not a real first landing (e.g. /auth/callback). */
const AUTH_PATH_PREFIX = '/auth/';

/** Keep in step with the users.first_touch_* column widths (backend truncates too). */
const HOST_MAX_LEN = 255;
const UTM_MAX_LEN = 100;
const PATH_MAX_LEN = 255;

export interface FirstTouch {
  referrer_host: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  landing_path: string;
}

interface StoredFirstTouch extends FirstTouch {
  sent: boolean;
}

function clip(value: string | null, maxLen: number): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.slice(0, maxLen) : null;
}

/** External referrer host, or null for a direct visit or an internal navigation. */
function externalReferrerHost(referrer: string, ownHost: string): string | null {
  if (!referrer) return null;
  try {
    const host = new URL(referrer).host.toLowerCase();
    return host && host !== ownHost ? clip(host, HOST_MAX_LEN) : null;
  } catch {
    return null;
  }
}

/** Build the first-touch record for a page load, or null for an auth hop. */
export function buildFirstTouch(href: string, referrer: string): FirstTouch | null {
  const url = new URL(href);
  if (url.pathname.startsWith(AUTH_PATH_PREFIX)) return null;
  const params = url.searchParams;
  return {
    referrer_host: externalReferrerHost(referrer, url.host.toLowerCase()),
    utm_source: clip(params.get('utm_source'), UTM_MAX_LEN),
    utm_medium: clip(params.get('utm_medium'), UTM_MAX_LEN),
    utm_campaign: clip(params.get('utm_campaign'), UTM_MAX_LEN),
    landing_path: url.pathname.slice(0, PATH_MAX_LEN),
  };
}

function readStored(): StoredFirstTouch | null {
  try {
    const raw = localStorage.getItem(FIRST_TOUCH_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredFirstTouch) : null;
  } catch {
    return null;
  }
}

function writeStored(value: StoredFirstTouch): void {
  try {
    localStorage.setItem(FIRST_TOUCH_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Storage blocked (private mode, site-data settings): the account stays unattributed.
  }
}

/** Record this page load as the first touch unless one is already stored. Call at boot. */
export function captureFirstTouch(href: string = window.location.href, referrer: string = document.referrer): void {
  if (readStored() !== null) return;
  const touch = buildFirstTouch(href, referrer);
  if (touch !== null) writeStored({ ...touch, sent: false });
}

/** The stored first touch if it has not been submitted yet, else null. */
export function readUnsentFirstTouch(): FirstTouch | null {
  const stored = readStored();
  if (stored === null || stored.sent) return null;
  return {
    referrer_host: stored.referrer_host,
    utm_source: stored.utm_source,
    utm_medium: stored.utm_medium,
    utm_campaign: stored.utm_campaign,
    landing_path: stored.landing_path,
  };
}

export function markFirstTouchSent(): void {
  const stored = readStored();
  if (stored !== null) writeStored({ ...stored, sent: true });
}
