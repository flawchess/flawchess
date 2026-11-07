/**
 * htmlShellCache.test.ts — the html-shell route matcher and cache key plugin.
 *
 * generateSW serializes both with Function.prototype.toString() into sw.js,
 * where module scope does not exist. Every case therefore runs on the original
 * function AND on a copy revived from its source text with `new Function`,
 * which throws a ReferenceError on any closure.
 */
import { describe, expect, it } from 'vitest';
import {
  HTML_SHELL_CACHE_KEY,
  HTML_SHELL_CACHE_NAME,
  htmlShellCacheKeyPlugin,
  isHtmlShellNavigation,
} from '../htmlShellCache';

type Matcher = typeof isHtmlShellNavigation;
// Workbox calls the callback with { mode, request, ... }; the real plugin ignores it.
type KeyFn = (arg: unknown) => Promise<string>;

function revive<T>(fn: unknown): T {
  return new Function(`return (${String(fn)})`)() as T;
}

function ctx(path: string, mode = 'navigate'): { request: { mode: string }; url: URL } {
  return { request: { mode }, url: new URL(path, 'https://flawchess.com') };
}

const variants: Array<[string, Matcher, KeyFn]> = [
  ['original', isHtmlShellNavigation, htmlShellCacheKeyPlugin.cacheKeyWillBeUsed],
  [
    'revived from toString()',
    revive<Matcher>(isHtmlShellNavigation),
    revive<KeyFn>(htmlShellCacheKeyPlugin.cacheKeyWillBeUsed),
  ],
];

describe('html-shell cache constants', () => {
  it('keeps the cache name', () => {
    expect(HTML_SHELL_CACHE_NAME).toBe('html-shell');
  });
});

describe.each(variants)('%s', (_label, matches, cacheKeyWillBeUsed) => {
  it.each([
    '/',
    '/?utm_source=pwa',
    '/train',
    '/privacy',
    '/privacy/',
    '/index.html',
    '/auth/reset-password?token=x',
  ])('treats a navigation to %s as an app-shell navigation', (path) => {
    expect(matches(ctx(path))).toBe(true);
  });

  it.each([
    '/api/auth/google/callback',
    '/privacy/index.html',
    '/google83883b0af640c73c.html',
    '/og-image.jpg',
    '/sw.js',
  ])('does not treat %s as an app-shell navigation', (path) => {
    expect(matches(ctx(path))).toBe(false);
  });

  it('ignores non-navigate requests', () => {
    expect(matches(ctx('/train', 'cors'))).toBe(false);
  });

  it.each(['https://flawchess.com/', 'https://flawchess.com/?utm_source=pwa', 'https://flawchess.com/train'])(
    'keys the request %s under the one shared entry',
    async (requestUrl) => {
      expect(HTML_SHELL_CACHE_KEY).toBe('/__html-shell__');
      expect(await cacheKeyWillBeUsed({ mode: 'read', request: { url: requestUrl } })).toBe(HTML_SHELL_CACHE_KEY);
    },
  );
});
