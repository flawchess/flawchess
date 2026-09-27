/**
 * Umami custom-event helper.
 *
 * Prefer the plain `data-umami-event` attribute wherever it works: the tracker
 * binds `<button>` elements and outbound `<a target="_blank">` links itself,
 * with no code.
 *
 * Use this helper for INTERNAL react-router links. On an `<a href>` without
 * `target="_blank"` umami calls `preventDefault()` and then assigns
 * `location.href` itself, which downgrades a client-side navigation into a
 * full page reload — so the attribute must never go on a `<Link>`.
 *
 * No-ops when the tracker is absent (local dev, ad blockers, the
 * `data-domains` gate), so callers never need to guard.
 */
/** The subset of an outgoing tracker payload this module rewrites. */
interface UmamiPayload {
  url?: string;
  referrer?: string;
  [key: string]: unknown;
}

declare global {
  interface Window {
    umami?: {
      track: (eventName: string, eventData?: Record<string, string>) => void;
      identify: (sessionData: Record<string, string>) => void;
    };
    /** Named by `data-before-send` on the tracker tag in index.html. */
    umamiBeforeSend?: (type: string, payload: UmamiPayload) => UmamiPayload;
  }
}

export function trackEvent(eventName: string, eventData?: Record<string, string>): void {
  window.umami?.track(eventName, eventData);
}

/**
 * Query params that carry credentials. /auth/reset-password?token=<reset JWT>
 * was stored verbatim in website_event.url_query (and in the next pageview's
 * referrer). `data-exclude-search` would also drop the utm_* tags, so the
 * params are removed one by one instead. Fragments (`#token=`) are already
 * dropped by `data-exclude-hash`.
 */
const SENSITIVE_QUERY_PARAMS: readonly string[] = ['token'];

/**
 * The Google OAuth round trip returns through accounts.google.* (any ccTLD), so
 * every Google sign-in was recorded as a pageview referred by it, making it the
 * top "referrer" and hiding the real acquisition sources.
 */
const OAUTH_REFERRER_HOST = /^accounts\.google\.[a-z.]+$/;

function stripSensitiveParams(value: string): string {
  if (!value) return value;
  try {
    // Internal referrers arrive origin-stripped ("/auth/..."): keep them relative.
    const isRelative = value.startsWith('/');
    const url = new URL(value, window.location.origin);
    const present = SENSITIVE_QUERY_PARAMS.filter((param) => url.searchParams.has(param));
    if (present.length === 0) return value;
    present.forEach((param) => url.searchParams.delete(param));
    return isRelative ? `${url.pathname}${url.search}${url.hash}` : url.toString();
  } catch {
    return value;
  }
}

function isOAuthReferrer(referrer: string): boolean {
  if (!referrer || referrer.startsWith('/')) return false;
  try {
    return OAUTH_REFERRER_HOST.test(new URL(referrer).hostname.toLowerCase());
  } catch {
    return false;
  }
}

/** Rewrite every outgoing tracker payload (pageviews, events, identify). */
export function scrubUmamiPayload(_type: string, payload: UmamiPayload): UmamiPayload {
  const scrubbed: UmamiPayload = { ...payload };
  if (typeof scrubbed.url === 'string') scrubbed.url = stripSensitiveParams(scrubbed.url);
  if (typeof scrubbed.referrer === 'string') {
    scrubbed.referrer = isOAuthReferrer(scrubbed.referrer) ? '' : stripSensitiveParams(scrubbed.referrer);
  }
  return scrubbed;
}

/**
 * Register the hook the tracker looks up by name at send time. Must run before
 * the first pageview: the deferred tracker only sends once the document is
 * complete, after main.tsx has executed.
 */
export function installUmamiBeforeSend(): void {
  window.umamiBeforeSend = scrubUmamiPayload;
}

export type UmamiAccountType = 'guest' | 'registered';

/**
 * Tag the Umami session with the account type so page and event reports can be
 * split into guests vs registered users (the activity dashboard knows the type
 * but not the pages; Umami knew the pages but not the type). No identifier is
 * sent, only this one coarse label.
 */
export function identifyAccountType(accountType: UmamiAccountType): void {
  window.umami?.identify({ account: accountType });
}
