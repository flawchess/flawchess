// @vitest-environment jsdom
/**
 * buildVersionCheck.test.ts — the startup/resume comparison of the compiled-in
 * build ID with the deployed /version.json. Uses the REAL reload gate and the
 * REAL diagnostics (only @sentry/react, fetch and window.location are stubbed),
 * so the ordering "one event, then the reload" is asserted end to end.
 *
 * The gate is a module singleton, so every test loads fresh copies of all the
 * modules (and therefore a fresh @sentry/react mock) via vi.resetModules().
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

vi.mock('@sentry/react', () => ({ captureMessage: vi.fn(), flush: vi.fn(), captureException: vi.fn() }));

const RUNNING_ID = '20260101T000000Z-aaaaaa';
const DEPLOYED_ID = '20261107T000000Z-bbbbbb';
const originalLocation = window.location;

interface Loaded {
  check: typeof import('../buildVersionCheck');
  gate: typeof import('../updateReload');
  swUpdate: typeof import('../swUpdate');
  diagnostics: typeof import('../staleBuildDiagnostics');
  sentry: typeof import('@sentry/react');
}

async function load(): Promise<Loaded> {
  vi.resetModules();
  const sentry = await import('@sentry/react');
  vi.mocked(sentry.flush).mockResolvedValue(true);
  return {
    check: await import('../buildVersionCheck'),
    gate: await import('../updateReload'),
    swUpdate: await import('../swUpdate'),
    diagnostics: await import('../staleBuildDiagnostics'),
    sentry,
  };
}

function jsonResponse(body: unknown, status = 200): unknown {
  return { status, json: async () => body };
}

/** Lets pending microtasks and the bounded beforeReload settle. */
async function settle(loaded: Loaded): Promise<void> {
  await vi.advanceTimersByTimeAsync(loaded.gate.BEFORE_RELOAD_TIMEOUT_MS + 1);
}

describe('buildVersionCheck', () => {
  let reload: ReturnType<typeof vi.fn>;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_800_000_000_000);
    window.sessionStorage.clear();
    reload = vi.fn();
    Object.defineProperty(window, 'location', { configurable: true, value: { reload } });
    Object.defineProperty(navigator, 'serviceWorker', {
      configurable: true,
      value: { controller: null, getRegistration: () => Promise.resolve(undefined) },
    });
    vi.stubGlobal('caches', { has: vi.fn().mockResolvedValue(false), open: vi.fn() });
    fetchMock = vi.fn().mockResolvedValue(jsonResponse({ buildId: RUNNING_ID }));
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe('mismatch handling', () => {
    it('reloads on mismatch, with one event sent BEFORE the reload, carrying the auto-reload marker', async () => {
      const loaded = await load();
      fetchMock.mockResolvedValue(jsonResponse({ buildId: DEPLOYED_ID }));

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);

      expect(reload).toHaveBeenCalledOnce();
      expect(loaded.sentry.captureMessage).toHaveBeenCalledOnce();
      expect(vi.mocked(loaded.sentry.captureMessage).mock.calls[0][0]).toBe(
        loaded.diagnostics.STALE_BUILD_SENTRY_MESSAGE,
      );
      expect(vi.mocked(loaded.sentry.captureMessage).mock.invocationCallOrder[0]).toBeLessThan(
        reload.mock.invocationCallOrder[0],
      );
      const { consumeAutoReloadMarker } = await import('../autoReload');
      expect(consumeAutoReloadMarker()).toBe(true);
    });

    it('does not reload and sends no event when the IDs match', async () => {
      const loaded = await load();

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);

      expect(reload).not.toHaveBeenCalled();
      expect(loaded.sentry.captureMessage).not.toHaveBeenCalled();
    });

    it('fetches /version.json with cache no-store', async () => {
      const loaded = await load();

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');

      expect(fetchMock).toHaveBeenCalledOnce();
      expect(fetchMock.mock.calls[0][0]).toBe('/version.json');
      expect(fetchMock.mock.calls[0][1]).toMatchObject({ cache: 'no-store' });
    });

    it('a stamp inside the cooldown stops the reload and sends no event; after it, it reloads', async () => {
      const loaded = await load();
      fetchMock.mockResolvedValue(jsonResponse({ buildId: DEPLOYED_ID }));
      window.sessionStorage.setItem(loaded.gate.UPDATE_RELOAD_STORAGE_KEY, String(Date.now()));

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);
      expect(reload).not.toHaveBeenCalled();
      expect(loaded.sentry.captureMessage).not.toHaveBeenCalled();

      window.sessionStorage.setItem(
        loaded.gate.UPDATE_RELOAD_STORAGE_KEY,
        String(Date.now() - loaded.gate.UPDATE_RELOAD_COOLDOWN_MS),
      );
      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);
      expect(reload).toHaveBeenCalledOnce();
    });
  });

  describe('malformed or failed responses never reload', () => {
    const cases: Array<[string, () => unknown]> = [
      ['fetch rejects', () => Promise.reject(new TypeError('offline'))],
      ['non-200', () => Promise.resolve(jsonResponse({ buildId: DEPLOYED_ID }, 503))],
      [
        'HTML body (json() throws)',
        () =>
          Promise.resolve({
            status: 200,
            json: async () => {
              throw new SyntaxError('Unexpected token <');
            },
          }),
      ],
      ['empty object', () => Promise.resolve(jsonResponse({}))],
      ['non-string buildId', () => Promise.resolve(jsonResponse({ buildId: 42 }))],
      ['empty buildId', () => Promise.resolve(jsonResponse({ buildId: '' }))],
    ];

    it.each(cases)('%s', async (_name, respond) => {
      const loaded = await load();
      fetchMock.mockImplementation(respond);

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);

      expect(reload).not.toHaveBeenCalled();
      expect(loaded.sentry.captureMessage).not.toHaveBeenCalled();
    });

    it('a hung fetch aborts at BUILD_VERSION_FETCH_TIMEOUT_MS without reloading, and the next check still runs', async () => {
      const loaded = await load();
      fetchMock.mockImplementationOnce(
        (_url: string, init: { signal: AbortSignal }) =>
          new Promise((_resolve, reject) => {
            init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
          }),
      );
      const check = loaded.check.createBuildVersionChecker(RUNNING_ID);

      const first = check('startup');
      await vi.advanceTimersByTimeAsync(loaded.check.BUILD_VERSION_FETCH_TIMEOUT_MS);
      await first;
      expect(reload).not.toHaveBeenCalled();

      fetchMock.mockResolvedValue(jsonResponse({ buildId: DEPLOYED_ID }));
      await check('startup');
      await settle(loaded);
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(reload).toHaveBeenCalledOnce();
    });
  });

  describe('resume', () => {
    it('two checks inside SW_UPDATE_DEBOUNCE_MS make one fetch', async () => {
      const loaded = await load();
      const check = loaded.check.createBuildVersionChecker(RUNNING_ID);

      await check('resume');
      await check('resume');

      expect(fetchMock).toHaveBeenCalledOnce();
    });

    it('checks again once the debounce window has passed', async () => {
      const loaded = await load();
      const check = loaded.check.createBuildVersionChecker(RUNNING_ID);

      await check('resume');
      await vi.advanceTimersByTimeAsync(loaded.swUpdate.SW_UPDATE_DEBOUNCE_MS);
      await check('resume');

      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it('a failed fetch does not consume the debounce', async () => {
      const loaded = await load();
      const check = loaded.check.createBuildVersionChecker(RUNNING_ID);
      fetchMock.mockRejectedValueOnce(new TypeError('offline'));

      await check('resume');
      await check('resume');

      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('during a session', () => {
    it('a resume mismatch makes no reload and no event; after the session ends a resume inside the debounce window applies it without a new fetch', async () => {
      const loaded = await load();
      const { useMarkPlayActive } = await import('../playActive');
      fetchMock.mockResolvedValue(jsonResponse({ buildId: DEPLOYED_ID }));
      const session = renderHook(() => useMarkPlayActive());
      const check = loaded.check.createBuildVersionChecker(RUNNING_ID);

      await check('resume');
      await settle(loaded);
      expect(reload).not.toHaveBeenCalled();
      expect(loaded.sentry.captureMessage).not.toHaveBeenCalled();

      session.unmount();
      await check('resume');
      // Strictly before SESSION_END_SETTLE_MS: only the resume path can have
      // applied it, not the settle timer.
      await vi.advanceTimersByTimeAsync(loaded.gate.SESSION_END_SETTLE_MS - 1);

      expect(fetchMock).toHaveBeenCalledOnce();
      expect(reload).toHaveBeenCalledOnce();
      expect(loaded.sentry.captureMessage).toHaveBeenCalledOnce();
    });

    it('a startup mismatch during a session reloads', async () => {
      const loaded = await load();
      const { useMarkPlayActive } = await import('../playActive');
      fetchMock.mockResolvedValue(jsonResponse({ buildId: DEPLOYED_ID }));
      renderHook(() => useMarkPlayActive());

      await loaded.check.createBuildVersionChecker(RUNNING_ID)('startup');
      await settle(loaded);

      expect(reload).toHaveBeenCalledOnce();
    });
  });

  describe('installBuildVersionCheck', () => {
    function captureListeners(): { documentAdd: ReturnType<typeof vi.spyOn>; windowAdd: ReturnType<typeof vi.spyOn> } {
      // Capture instead of registering, so no listener leaks into other tests.
      return {
        documentAdd: vi.spyOn(document, 'addEventListener').mockImplementation(() => {}),
        windowAdd: vi.spyOn(window, 'addEventListener').mockImplementation(() => {}),
      };
    }

    it('is inert with defaults under vitest: no fetch and no listeners', async () => {
      const loaded = await load();
      const { documentAdd, windowAdd } = captureListeners();

      loaded.check.installBuildVersionCheck();
      await settle(loaded);

      expect(fetchMock).not.toHaveBeenCalled();
      expect(documentAdd).not.toHaveBeenCalled();
      expect(windowAdd).not.toHaveBeenCalled();
    });

    it('is inert without a running build ID even when enabled', async () => {
      const loaded = await load();
      const { documentAdd } = captureListeners();

      loaded.check.installBuildVersionCheck({ enabled: true, runningBuildId: '' });

      expect(fetchMock).not.toHaveBeenCalled();
      expect(documentAdd).not.toHaveBeenCalled();
    });

    it('when enabled with a running ID it fetches at once and listens for resume', async () => {
      const loaded = await load();
      const { documentAdd, windowAdd } = captureListeners();

      loaded.check.installBuildVersionCheck({ enabled: true, runningBuildId: RUNNING_ID });
      await settle(loaded);

      expect(fetchMock).toHaveBeenCalledOnce();
      expect(documentAdd).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
      expect(windowAdd).toHaveBeenCalledWith('focus', expect.any(Function));
    });

    it('a hidden visibilitychange makes no fetch; a visible one does (after the debounce)', async () => {
      const loaded = await load();
      const { documentAdd } = captureListeners();
      loaded.check.installBuildVersionCheck({ enabled: true, runningBuildId: RUNNING_ID });
      await settle(loaded);
      fetchMock.mockClear();
      await vi.advanceTimersByTimeAsync(loaded.swUpdate.SW_UPDATE_DEBOUNCE_MS);
      const onVisibility = documentAdd.mock.calls.find((call) => call[0] === 'visibilitychange')![1] as () => void;

      Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
      onVisibility();
      await settle(loaded);
      expect(fetchMock).not.toHaveBeenCalled();

      Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
      onVisibility();
      await settle(loaded);
      expect(fetchMock).toHaveBeenCalledOnce();
    });
  });
});
