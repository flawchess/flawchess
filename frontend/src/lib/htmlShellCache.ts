// Offline app-shell cache for the service worker's navigation route
// (vite.config.ts runtimeCaching, NetworkFirst). Bug fix (quick 261107-dnz):
// entries were keyed per full URL with no expiry, so /?utm_source=pwa (the PWA
// start_url) could hold a weeks-old shell that was served whenever its network
// fetch threw. Every route-like navigation now shares ONE entry, the latest
// successful app-shell load, so the offline fallback can never be an old
// per-URL copy.
//
// DD-6: one shared key is right because Caddy serves the same index.html for
// every route-like path (/, /train, /privacy, /privacy/ ...). The prerendered
// dist/privacy/index.html is only reachable at the literal /privacy/index.html,
// which the route guard below excludes. If Caddy ever serves that prerendered
// page at /privacy, this key needs revisiting.
//
// DD-7: the legacy per-URL entries in the existing `html-shell` cache are left
// in place. They become unreachable, are a handful of small documents, and
// deleting them needs worker activate logic. Their `date` headers also show up
// in the stale-build diagnostics (staleBuildDiagnostics.ts) as direct evidence
// for or against the stale-entry hypothesis. The synthetic key below cannot
// collide with a legacy entry and is recognisable in those diagnostics.

/** Workbox cache name for the app-shell navigations. */
export const HTML_SHELL_CACHE_NAME = 'html-shell';

/** The single shared key every app-shell navigation is stored and matched under. */
export const HTML_SHELL_CACHE_KEY = '/__html-shell__';

/** Structural, not the DOM Request type: tsconfig.node pulls this file in via vite.config.ts and has no DOM lib. */
interface HtmlShellMatchContext {
  request: { mode: string };
  url: URL;
}

// CONSTRAINTS for the two members below. generateSW serializes them into
// dist/sw.js with Function.prototype.toString(), so they must (1) reference
// NOTHING outside their own body (no module consts, no imports, no helper
// functions: those do not exist in the worker) and (2) be plain functions or
// arrow functions with `cacheKeyWillBeUsed` as a property holding an arrow
// (method shorthand serializes to a syntax error). The key literal is therefore
// repeated inside the plugin, and htmlShellCache.test.ts keeps it in step with
// HTML_SHELL_CACHE_KEY. Workbox strips comments inside serialized functions, so
// this is the only place the reasoning survives.

/**
 * Route matcher: a navigation to a route-like path that is not the backend.
 * Excludes file-like paths (last segment has a dot) except /index.html, so
 * /privacy/index.html, /google83883b0af640c73c.html and /og-image.jpg can never
 * overwrite the shared shell (new risk with a single key).
 */
export const isHtmlShellNavigation = ({ request, url }: HtmlShellMatchContext): boolean => {
  if (request.mode !== 'navigate') return false;
  if (url.pathname.startsWith('/api/')) return false;
  const lastSegment = url.pathname.slice(url.pathname.lastIndexOf('/') + 1);
  return !lastSegment.includes('.') || url.pathname === '/index.html';
};

/** Workbox plugin: store and match every shell navigation under the one shared key. */
export const htmlShellCacheKeyPlugin = {
  cacheKeyWillBeUsed: async (): Promise<string> => '/__html-shell__',
};
