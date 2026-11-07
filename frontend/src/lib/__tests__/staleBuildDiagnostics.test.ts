// @vitest-environment jsdom
/**
 * staleBuildDiagnostics.test.ts — the single pre-reload Sentry event. Every
 * failure or stall in collection or flush must still resolve (the reload may
 * never wait on diagnostics), and device-local cache keys must never leak a
 * credential into the event.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as Sentry from '@sentry/react';
import {
  CACHE_COLLECT_TIMEOUT_MS,
  MAX_REPORTED_SHELL_ENTRIES,
  SENTRY_FLUSH_TIMEOUT_MS,
  STALE_BUILD_SENTRY_MESSAGE,
  reportStaleBuild,
} from '../staleBuildDiagnostics';
import { BEFORE_RELOAD_TIMEOUT_MS } from '../updateReload';

vi.mock('@sentry/react', () => ({ captureMessage: vi.fn(), flush: vi.fn() }));

interface FakeShellEntry {
  url: string;
  date: string | null;
}

/** Stubs the Cache API with one html-shell cache holding `entries`. */
function stubCaches(entries: FakeShellEntry[]): void {
  const keys = entries.map((entry) => ({ url: entry.url }));
  const cache = {
    keys: vi.fn().mockResolvedValue(keys),
    match: vi.fn(async (request: { url: string }) => {
      const found = entries.find((entry) => entry.url === request.url);
      return { headers: { get: () => found?.date ?? null } };
    }),
  };
  vi.stubGlobal('caches', { has: vi.fn().mockResolvedValue(true), open: vi.fn().mockResolvedValue(cache) });
}

function stubServiceWorker(getRegistration: () => Promise<unknown>, controller: unknown = {}): void {
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { controller, getRegistration },
  });
}

function sentContext(): Record<string, unknown> {
  const call = vi.mocked(Sentry.captureMessage).mock.calls[0];
  const options = call[1] as { contexts: { stale_build: Record<string, unknown> } };
  return options.contexts.stale_build;
}

describe('reportStaleBuild', () => {
  beforeEach(() => {
    vi.mocked(Sentry.captureMessage).mockReset();
    vi.mocked(Sentry.flush).mockReset().mockResolvedValue(true);
    stubServiceWorker(() => Promise.resolve({ active: { state: 'activated' }, waiting: null }));
    stubCaches([{ url: 'https://flawchess.com/__html-shell__', date: 'Mon, 02 Nov 2026 10:00:00 GMT' }]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('sends exactly one event with the fixed message and every diagnostic field', async () => {
    await reportStaleBuild('20260101T000000Z-aaaaaa', '20261107T000000Z-bbbbbb', 'resume');

    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
    expect(vi.mocked(Sentry.captureMessage).mock.calls[0][0]).toBe(STALE_BUILD_SENTRY_MESSAGE);
    const options = vi.mocked(Sentry.captureMessage).mock.calls[0][1] as {
      level: string;
      tags: Record<string, string>;
    };
    expect(options.level).toBe('info');
    expect(options.tags).toEqual({ source: 'build-version-check', trigger: 'resume' });

    const context = sentContext();
    expect(context).toMatchObject({
      running_build_id: '20260101T000000Z-aaaaaa',
      deployed_build_id: '20261107T000000Z-bbbbbb',
      collection: 'complete',
      sw_controller: true,
      sw_active_state: 'activated',
      sw_waiting_state: null,
      html_shell_entry_count: 1,
    });
    expect(context.html_shell_entries).toEqual(['/__html-shell__ @ Mon, 02 Nov 2026 10:00:00 GMT']);
    expect(typeof context.page_age_ms).toBe('number');
    expect(Sentry.flush).toHaveBeenCalledOnce();
  });

  it('reports pathnames only: a token in a legacy shell key never appears anywhere in the event', async () => {
    stubCaches([{ url: 'https://flawchess.com/auth/reset-password?token=abc', date: null }]);

    await reportStaleBuild('a', 'b', 'startup');

    expect(sentContext().html_shell_entries).toEqual(['/auth/reset-password @ no-date']);
    expect(JSON.stringify(vi.mocked(Sentry.captureMessage).mock.calls)).not.toContain('abc');
  });

  it('reports html_shell_entries as strings (Sentry normalizes contexts to depth 3)', async () => {
    await reportStaleBuild('a', 'b', 'startup');

    const entries = sentContext().html_shell_entries as unknown[];
    expect(entries.every((entry) => typeof entry === 'string')).toBe(true);
  });

  it('caps the reported entries while the count stays true', async () => {
    const total = MAX_REPORTED_SHELL_ENTRIES + 5;
    stubCaches(Array.from({ length: total }, (_, i) => ({ url: `https://flawchess.com/p${i}`, date: null })));

    await reportStaleBuild('a', 'b', 'startup');

    expect(sentContext().html_shell_entry_count).toBe(total);
    expect(sentContext().html_shell_entries).toHaveLength(MAX_REPORTED_SHELL_ENTRIES);
  });

  it('does not create the html-shell cache when it does not exist', async () => {
    const open = vi.fn();
    vi.stubGlobal('caches', { has: vi.fn().mockResolvedValue(false), open });

    await reportStaleBuild('a', 'b', 'startup');

    expect(open).not.toHaveBeenCalled();
    expect(sentContext().html_shell_entry_count).toBe(0);
  });

  it('still sends one event and resolves when caches rejects', async () => {
    vi.stubGlobal('caches', { has: vi.fn().mockRejectedValue(new Error('denied')), open: vi.fn() });

    await expect(reportStaleBuild('a', 'b', 'startup')).resolves.toBeUndefined();

    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
    expect(sentContext().collection).toBe('failed');
    expect(sentContext().sw_active_state).toBe('activated');
  });

  it('still sends one event and resolves when getRegistration rejects', async () => {
    stubServiceWorker(() => Promise.reject(new Error('nope')));

    await expect(reportStaleBuild('a', 'b', 'startup')).resolves.toBeUndefined();

    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
    expect(sentContext().collection).toBe('failed');
    expect(sentContext().html_shell_entry_count).toBe(1);
  });

  it('still sends one event and resolves when performance throws', async () => {
    vi.spyOn(performance, 'getEntriesByType').mockImplementation(() => {
      throw new Error('no perf');
    });

    await expect(reportStaleBuild('a', 'b', 'startup')).resolves.toBeUndefined();

    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
    vi.restoreAllMocks();
  });

  it('sends a partial event at CACHE_COLLECT_TIMEOUT_MS when caches never settles', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('caches', { has: vi.fn(() => new Promise(() => {})), open: vi.fn() });

    const done = reportStaleBuild('a', 'b', 'startup');
    await vi.advanceTimersByTimeAsync(CACHE_COLLECT_TIMEOUT_MS - 1);
    expect(Sentry.captureMessage).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
    expect(sentContext().collection).toBe('timed_out');
    expect(sentContext().sw_active_state).toBe('activated');
    await done;
  });

  it('resolves when captureMessage throws', async () => {
    vi.mocked(Sentry.captureMessage).mockImplementation(() => {
      throw new Error('sdk down');
    });

    await expect(reportStaleBuild('a', 'b', 'startup')).resolves.toBeUndefined();
  });

  it('resolves when flush rejects', async () => {
    vi.mocked(Sentry.flush).mockRejectedValue(new Error('flush failed'));

    await expect(reportStaleBuild('a', 'b', 'startup')).resolves.toBeUndefined();
    expect(Sentry.captureMessage).toHaveBeenCalledOnce();
  });

  it('resolves at SENTRY_FLUSH_TIMEOUT_MS when flush never settles', async () => {
    vi.useFakeTimers();
    vi.mocked(Sentry.flush).mockReturnValue(new Promise(() => {}));

    let resolved = false;
    const done = reportStaleBuild('a', 'b', 'startup').then(() => {
      resolved = true;
    });
    await vi.advanceTimersByTimeAsync(SENTRY_FLUSH_TIMEOUT_MS - 1);
    expect(resolved).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await done;
    expect(resolved).toBe(true);
  });

  it('keeps the worst-case collection plus flush below the reload bound', () => {
    expect(CACHE_COLLECT_TIMEOUT_MS + SENTRY_FLUSH_TIMEOUT_MS).toBeLessThan(BEFORE_RELOAD_TIMEOUT_MS);
  });
});
