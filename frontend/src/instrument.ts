import * as Sentry from "@sentry/react";
import { isStalePreloadReloadPending } from "@/lib/stalePreloadReload";

// Duck-typed interface for Axios errors — avoids importing axios in the Sentry
// instrumentation file which loads before the app bundle is ready.
interface AxiosLikeError {
  isAxiosError: true;
  response?: { status: number; data?: unknown };
  code?: string;
  message?: string;
  config?: { url?: string; method?: string };
}

function isAxiosLikeError(err: unknown): err is AxiosLikeError {
  return (
    typeof err === "object" &&
    err !== null &&
    (err as Record<string, unknown>)["isAxiosError"] === true
  );
}

// FLAWCHESS-24: axios XHR `onerror` (ERR_NETWORK/ERR_CANCELED) means no HTTP
// response was ever received. The two dominant, unactionable populations are
// (a) our own 8 `window.location.href` hard navigations aborting in-flight
// XHRs, and (b) iOS Safari backgrounding / flaky mobile connectivity (9 of
// the last 15 events). Neither is a bug we can fix. The foreground+online
// variant is deliberately KEPT (below, unchanged) because it is the only one
// that could signal a real Caddy/host outage — an outage that never reaches
// the backend's own Sentry.
const SUPPRESSIBLE_AXIOS_CODES = ["ERR_NETWORK", "ERR_CANCELED"] as const;

// Set from a 'pagehide' listener — fires reliably on iOS Safari, unlike
// 'beforeunload'/'unload' (population (b) above).
let isUnloading = false;
if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => {
    isUnloading = true;
  });
}

/**
 * True when a response-less XHR failure is EXPECTED rather than
 * informative: the page is unloading, offline, or backgrounded. Each browser
 * global is read behind its own `typeof` guard (D-09, precedent:
 * useAuth.ts's `typeof localStorage` guard) so an unavailable global reads as
 * "not suppressible" — fail-open to REPORTING, never fail-open to dropping.
 */
function isSuppressibleNetworkNoise(): boolean {
  if (isUnloading) return true;
  if (typeof navigator !== "undefined" && navigator.onLine === false) return true;
  if (typeof document !== "undefined" && document.visibilityState === "hidden") return true;
  return false;
}

// FLAWCHESS-31: axios raises ECONNABORTED with this exact message from its XHR
// `onabort` handler (and Firefox's status-0 navigation-cancel path), i.e. the
// BROWSER tore the request down: a navigation or redirect (every event was on
// /login, /auth/google/authorize, or a page change), not a server problem. A
// real timeout shares the code but says "timeout of Nms exceeded", so matching
// the message keeps any future `timeout:` config reporting. Dropped
// unconditionally: a server outage surfaces as ERR_NETWORK, never as an abort.
const BROWSER_ABORT_MESSAGE = "Request aborted";

function isBrowserAbortedRequest(error: AxiosLikeError): boolean {
  return error.code === "ECONNABORTED" && error.message === BROWSER_ABORT_MESSAGE;
}

/** The one endpoint whose 422 is a deliberate, user-facing rejection (below). */
const PASTE_GAME_URL = "/imports/paste";

/**
 * FLAWCHESS-9W: true for the pasted-PGN endpoint rejecting text that is not a
 * complete game. `PasteModal` renders the server's message in its
 * `paste-save-error` slot and the user edits and retries, so there is nothing
 * to fix — reporting it just files a Sentry issue per typo.
 *
 * Scoped to this one method+path rather than to the status: every OTHER 422
 * in the API is `from_date must be <= to_date`, which our own date-range
 * picker is supposed to make impossible and which therefore IS a bug.
 *
 * The string-`detail` check keeps the remaining bug case visible. FastAPI
 * puts a plain string in `detail` for an explicit `HTTPException` (our
 * deliberate rejection) but an ARRAY there for a Pydantic schema failure —
 * and a schema failure on this endpoint means the frontend built a malformed
 * request body, which still ships to Sentry.
 */
function isExpectedPastedPgnRejection(error: AxiosLikeError): boolean {
  if (error.response?.status !== 422) return false;
  if (error.config?.method?.toLowerCase() !== "post") return false;
  if (error.config?.url !== PASTE_GAME_URL) return false;
  const data = error.response.data;
  if (typeof data !== "object" || data === null) return false;
  return typeof (data as Record<string, unknown>)["detail"] === "string";
}

/**
 * True for an axios failure that is expected and never a bug, so the event is
 * dropped. Split out of sentryBeforeSend() to keep its complexity in bounds.
 */
function isDroppableAxiosError(error: AxiosLikeError): boolean {
  // 401 Unauthorized is never a bug — it's a normal auth failure (expired session,
  // wrong credentials). Drop it to avoid noise in Sentry.
  if (error.response?.status === 401) return true;
  // FLAWCHESS-9W: an unparseable pasted PGN is expected user input, not a
  // bug — see isExpectedPastedPgnRejection() above.
  if (isExpectedPastedPgnRejection(error)) return true;
  // FLAWCHESS-31: a browser-aborted request is never actionable — see
  // isBrowserAbortedRequest() above.
  if (isBrowserAbortedRequest(error)) return true;
  // FLAWCHESS-24: drop unactionable network noise — see SUPPRESSIBLE_AXIOS_CODES
  // and isSuppressibleNetworkNoise() docs above. A timeout ECONNABORTED (the
  // request WAS attempted) is deliberately excluded and always ships.
  return (
    error.code !== undefined &&
    (SUPPRESSIBLE_AXIOS_CODES as readonly string[]).includes(error.code) &&
    isSuppressibleNetworkNoise()
  );
}

const FILTERED_QUERY_PLACEHOLDER = "[Filtered]";

/** Replaces everything after the first "?"; applied to the page URL and navigation breadcrumbs so query-string tokens never leave the browser. */
function scrubUrlQuery(url: string): string {
  const queryStart = url.indexOf("?");
  return queryStart === -1
    ? url
    : `${url.slice(0, queryStart)}?${FILTERED_QUERY_PLACEHOLDER}`;
}

function sentryBeforeSend(
  event: Sentry.ErrorEvent,
  hint: Sentry.EventHint,
): Sentry.ErrorEvent | null {
  // FLAWCHESS-C6: a stale-chunk recovery reload is in flight, so this page is
  // about to be discarded and whatever broke in it (the lazy import resolved
  // to undefined) is fixed by the reload itself.
  if (isStalePreloadReloadPending()) return null;
  const error = hint.originalException;
  if (isAxiosLikeError(error)) {
    if (isDroppableAxiosError(error)) {
      return null;
    }
    // FLAWCHESS-64: the event previously recorded only the page transaction,
    // never the endpoint that failed (55 events, no attributable route).
    // This attachment is diagnostic only — it changes neither event grouping
    // nor any rate limit.
    if (error.config?.url !== undefined || error.config?.method !== undefined) {
      event.request = {
        ...event.request,
        ...(error.config.url !== undefined ? { url: error.config.url } : {}),
        ...(error.config.method !== undefined
          ? { method: error.config.method.toUpperCase() }
          : {}),
      };
    }
    // FLAWCHESS-64: an axios rejection's stack is always the same two minified
    // axios frames, so Sentry's default grouping collapses EVERY unfingerprinted
    // status into one issue. That issue absorbed 403s from guests on /train,
    // and once those were gated out (quick 260807-dr9) it silently "regressed"
    // by absorbing unrelated deploy-window 502s instead. Keying the fingerprint
    // on the status keeps unrelated failures in unrelated groups, so resolving
    // one can no longer be undone by the next.
    //
    // 500 keeps its historical `api-server-error` key rather than moving to
    // `api-http-500` so the existing Sentry issue keeps its history.
    const status = error.response?.status;
    if (status !== undefined) {
      event.fingerprint = status === 500 ? ["api-server-error"] : [`api-http-${status}`];
    } else if (error.code === "ECONNABORTED") {
      event.fingerprint = ["api-timeout"];
    } else if (error.code === "ERR_NETWORK") {
      event.fingerprint = ["api-network-error"];
    }
  }
  // Scrub the query string from the event URL for EVERY event, not just axios
  // ones. Sentry's HttpContext integration copies location.href (full query
  // string) into event.request.url, and that URL is NOT gated by
  // dataCollection.urlQueryParams (the SDK source says so). /reset-password
  // ?token=<JWT> is a real route, so any error captured there shipped the live
  // password-reset credential to Sentry. Placed after the axios block so it also
  // covers the url that block attaches (an API path, normally query-free).
  if (event.request?.url) {
    event.request.url = scrubUrlQuery(event.request.url);
  }
  scrubNavigationBreadcrumbs(event.breadcrumbs);
  return event;
}

// The History integration records every client-side route change as a
// "navigation" breadcrumb whose data.from / data.to keep the full query string,
// and dataCollection.urlQueryParams does not gate them (it covers fetch/xhr
// breadcrumbs and spans only). After a reset, ResetPasswordForm navigates away
// from /reset-password?token=<JWT>, so any later error in that page session
// shipped the token in event.breadcrumbs (found in Phase 232 UAT, gap G-232-3).
function scrubNavigationBreadcrumbs(breadcrumbs: Sentry.Breadcrumb[] | undefined): void {
  for (const breadcrumb of breadcrumbs ?? []) {
    if (breadcrumb.category !== "navigation" || !breadcrumb.data) continue;
    for (const key of ["from", "to"] as const) {
      const url: unknown = breadcrumb.data[key];
      if (typeof url === "string") breadcrumb.data[key] = scrubUrlQuery(url);
    }
  }
}

// Key fragments (matched case-insensitively as substrings) that identify an IP
// or user-identifying header / query parameter. Verbatim from the Sentry JS
// v10 -> v11 migration guide ("restore previous behavior" dataCollection
// snippet), so header and query-param filtering matches what v10 did.
const SENTRY_PII_KEY_DENYLIST: string[] = ["forwarded", "-ip", "remote-", "via", "-user"];

export { sentryBeforeSend };

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE, // "production" or "development" — set by Vite automatically
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) || 0,
  beforeSend: sentryBeforeSend,
  // Phase 232 / D-02: Sentry v11 reversed the dataCollection defaults to
  // "collect everything" (user IP, cookies, request/response bodies, headers,
  // query params). Left unset, login POST bodies (passwords) and session
  // cookies would start leaving the browser. This block keeps exactly what v10
  // sent, which is what the Privacy page discloses.
  // NOTE: urlQueryParams below only gates query strings in fetch breadcrumbs and
  // spans. It does NOT cover event.request.url (the page URL) or navigation
  // breadcrumbs; sentryBeforeSend() scrubs both via scrubUrlQuery().
  dataCollection: {
    // userInfo false also keeps Relay IP inference off (infer_ip "never").
    userInfo: false,
    cookies: false,
    // Deny list rather than `false`: the browser HttpContext integration only
    // ever reads User-Agent and Referer, and dropping User-Agent would lose
    // the browser/OS context Sentry derives from it.
    httpHeaders: {
      request: { deny: SENTRY_PII_KEY_DENYLIST },
      response: { deny: SENTRY_PII_KEY_DENYLIST },
    },
    httpBodies: [],
    urlQueryParams: { deny: SENTRY_PII_KEY_DENYLIST },
  },
  // v11 defaults this to true, attaching synthetic stack traces to non-Error
  // captures. With no source maps shipped (SEED-189) those frames are minified
  // and change on every deploy, which would split issues per release.
  attachStacktrace: false,
  // Suppress DOM errors caused by browser extensions (e.g. Google Translate)
  // mutating nodes that React expects to control.
  ignoreErrors: [
    /Failed to execute 'removeChild' on 'Node'/,
    /Failed to execute 'insertBefore' on 'Node'/,
    // A sw.js revalidation failing means the network is gone — unactionable
    // by construction, and the sampled events share a trace id with the
    // offline XHR failure that produced them.
    /Failed to update a ServiceWorker/,
    // FLAWCHESS-8P: WebKit's wording for that same failed revalidation.
    // Chrome says "Failed to update a ServiceWorker ..."; Safari/iOS throws a
    // TypeError reading "Script <url> load failed", so the pattern above never
    // matched it and all 6 events were Mobile Safari.
    /Script \S+\/sw\.js load failed/,
  ],
  denyUrls: [
    // These frames are entirely inside Cloudflare Web Analytics, not our code.
    /beacon\.min\.js/,
    // FLAWCHESS-CF: errors thrown by a browser extension's own content
    // scripts (e.g. "Window message ... timed out") are not ours to fix.
    /^(chrome|moz|safari-web)-extension:\/\//,
  ],
});
