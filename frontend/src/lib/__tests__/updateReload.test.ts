// @vitest-environment jsdom
/**
 * updateReload.test.ts — the shared gate for every "a newer build exists"
 * reload. The gate is a module singleton (in-flight flag), so each test loads
 * a fresh copy via vi.resetModules() + dynamic import.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

const originalLocation = window.location;

type UpdateReloadModule = typeof import('../updateReload');

async function loadGate(): Promise<UpdateReloadModule> {
  vi.resetModules();
  return import('../updateReload');
}

describe('requestUpdateReload', () => {
  let reload: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_800_000_000_000);
    window.sessionStorage.clear();
    reload = vi.fn();
    Object.defineProperty(window, 'location', { configurable: true, value: { reload } });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('two requests make one reload and one beforeReload', async () => {
    const { requestUpdateReload } = await loadGate();
    const beforeReload = vi.fn().mockResolvedValue(undefined);

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true, beforeReload });
    requestUpdateReload({ reason: 'build-mismatch', atStartup: true, beforeReload });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
    expect(beforeReload).toHaveBeenCalledOnce();
  });

  it('still reloads when beforeReload rejects', async () => {
    const { requestUpdateReload } = await loadGate();

    requestUpdateReload({
      reason: 'build-mismatch',
      atStartup: true,
      beforeReload: () => Promise.reject(new Error('boom')),
    });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('still reloads when beforeReload throws synchronously', async () => {
    const { requestUpdateReload } = await loadGate();

    requestUpdateReload({
      reason: 'build-mismatch',
      atStartup: true,
      beforeReload: () => {
        throw new Error('boom');
      },
    });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('reloads at BEFORE_RELOAD_TIMEOUT_MS when beforeReload never settles', async () => {
    const { requestUpdateReload, BEFORE_RELOAD_TIMEOUT_MS } = await loadGate();

    requestUpdateReload({
      reason: 'build-mismatch',
      atStartup: true,
      beforeReload: () => new Promise<void>(() => {}),
    });
    await vi.advanceTimersByTimeAsync(BEFORE_RELOAD_TIMEOUT_MS - 1);
    expect(reload).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('marks the reload as automatic so Umami drops its pageview', async () => {
    const { requestUpdateReload } = await loadGate();
    const { consumeAutoReloadMarker } = await import('../autoReload');

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
    await vi.runAllTimersAsync();

    expect(consumeAutoReloadMarker()).toBe(true);
  });

  it('cooldown: a request within the window after a reload does nothing, for either reason', async () => {
    const { requestUpdateReload, UPDATE_RELOAD_STORAGE_KEY, UPDATE_RELOAD_COOLDOWN_MS } = await loadGate();
    window.sessionStorage.setItem(UPDATE_RELOAD_STORAGE_KEY, String(Date.now()));

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
    requestUpdateReload({ reason: 'sw-update', atStartup: false });
    await vi.advanceTimersByTimeAsync(UPDATE_RELOAD_COOLDOWN_MS - 1);

    expect(reload).not.toHaveBeenCalled();
  });

  it('cooldown: reloads again once the window has passed', async () => {
    const { requestUpdateReload, UPDATE_RELOAD_STORAGE_KEY, UPDATE_RELOAD_COOLDOWN_MS } = await loadGate();
    window.sessionStorage.setItem(UPDATE_RELOAD_STORAGE_KEY, String(Date.now() - UPDATE_RELOAD_COOLDOWN_MS));

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('a sw-update request right after a mismatch reload does not reload again', async () => {
    const { requestUpdateReload } = await loadGate();

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
    await vi.runAllTimersAsync();
    // The reload happened and the new worker's controllerchange follows.
    requestUpdateReload({ reason: 'sw-update', atStartup: false });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
  });

  describe('storage unavailable', () => {
    beforeEach(() => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });
    });

    it('a build mismatch fails closed (no loop guard, no reload)', async () => {
      const { requestUpdateReload } = await loadGate();

      requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
      await vi.runAllTimersAsync();

      expect(reload).not.toHaveBeenCalled();
    });

    it('a sw-update still reloads (cannot loop, and is today behaviour)', async () => {
      const { requestUpdateReload } = await loadGate();

      requestUpdateReload({ reason: 'sw-update', atStartup: false });
      await vi.runAllTimersAsync();

      expect(reload).toHaveBeenCalledOnce();
    });
  });
});

describe('session hold', () => {
  let reload: ReturnType<typeof vi.fn>;

  async function loadWithSession(): Promise<
    UpdateReloadModule & { useMarkPlayActive: typeof import('../playActive').useMarkPlayActive }
  > {
    const gate = await loadGate();
    const { useMarkPlayActive } = await import('../playActive');
    return { ...gate, useMarkPlayActive };
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_800_000_000_000);
    window.sessionStorage.clear();
    reload = vi.fn();
    Object.defineProperty(window, 'location', { configurable: true, value: { reload } });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('a runtime request while a session is active does not reload, even after timers advance', async () => {
    const { requestUpdateReload, useMarkPlayActive } = await loadWithSession();
    renderHook(() => useMarkPlayActive());

    requestUpdateReload({ reason: 'sw-update', atStartup: false });
    await vi.advanceTimersByTimeAsync(60_000);

    expect(reload).not.toHaveBeenCalled();
  });

  it('a startup request while a session is active reloads', async () => {
    const { requestUpdateReload, useMarkPlayActive } = await loadWithSession();
    renderHook(() => useMarkPlayActive());

    requestUpdateReload({ reason: 'build-mismatch', atStartup: true });
    await vi.runAllTimersAsync();

    expect(reload).toHaveBeenCalledOnce();
  });

  it('held, then the session ends: no reload before SESSION_END_SETTLE_MS, a reload after it', async () => {
    const { requestUpdateReload, useMarkPlayActive, SESSION_END_SETTLE_MS } = await loadWithSession();
    const session = renderHook(() => useMarkPlayActive());
    requestUpdateReload({ reason: 'sw-update', atStartup: false });

    session.unmount();
    await vi.advanceTimersByTimeAsync(SESSION_END_SETTLE_MS - 1);
    expect(reload).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('held, then unmount and a new mount in one synchronous step (rematch): no reload after the settle delay', async () => {
    const { requestUpdateReload, useMarkPlayActive, SESSION_END_SETTLE_MS } = await loadWithSession();
    const first = renderHook(() => useMarkPlayActive());
    requestUpdateReload({ reason: 'sw-update', atStartup: false });

    first.unmount();
    renderHook(() => useMarkPlayActive());
    await vi.advanceTimersByTimeAsync(SESSION_END_SETTLE_MS * 3);

    expect(reload).not.toHaveBeenCalled();
  });

  it('held, play ends while useHoldUpdateReload is mounted (solve to score screen): no reload until the hold unmounts', async () => {
    const { requestUpdateReload, useMarkPlayActive, useHoldUpdateReload, SESSION_END_SETTLE_MS } =
      await loadWithSession();
    const solve = renderHook(() => useMarkPlayActive());
    requestUpdateReload({ reason: 'sw-update', atStartup: false });

    // Solve screen unmounts, score screen mounts.
    solve.unmount();
    const score = renderHook(() => useHoldUpdateReload());
    await vi.advanceTimersByTimeAsync(SESSION_END_SETTLE_MS * 3);
    expect(reload).not.toHaveBeenCalled();

    score.unmount();
    await vi.advanceTimersByTimeAsync(SESSION_END_SETTLE_MS + 1);
    expect(reload).toHaveBeenCalledOnce();
  });

  describe('applyHeldUpdateReload', () => {
    it('returns false with nothing held', async () => {
      const { applyHeldUpdateReload } = await loadWithSession();

      expect(applyHeldUpdateReload()).toBe(false);
      await vi.runAllTimersAsync();
      expect(reload).not.toHaveBeenCalled();
    });

    it('returns true and does not reload while the session is still active', async () => {
      const { requestUpdateReload, applyHeldUpdateReload, useMarkPlayActive } = await loadWithSession();
      renderHook(() => useMarkPlayActive());
      requestUpdateReload({ reason: 'sw-update', atStartup: false });

      expect(applyHeldUpdateReload()).toBe(true);
      await vi.advanceTimersByTimeAsync(10_000);

      expect(reload).not.toHaveBeenCalled();
    });

    it('returns true and reloads once the session is inactive, without waiting for the settle delay', async () => {
      const { requestUpdateReload, applyHeldUpdateReload, useMarkPlayActive, SESSION_END_SETTLE_MS } =
        await loadWithSession();
      const session = renderHook(() => useMarkPlayActive());
      requestUpdateReload({ reason: 'sw-update', atStartup: false });
      session.unmount();

      expect(applyHeldUpdateReload()).toBe(true);
      await vi.advanceTimersByTimeAsync(SESSION_END_SETTLE_MS - 1);

      expect(reload).toHaveBeenCalledOnce();
    });
  });

  it('a held sw-update is replaced by a later mismatch, whose beforeReload then runs', async () => {
    const { requestUpdateReload, applyHeldUpdateReload, useMarkPlayActive } = await loadWithSession();
    const session = renderHook(() => useMarkPlayActive());
    const beforeReload = vi.fn().mockResolvedValue(undefined);
    requestUpdateReload({ reason: 'sw-update', atStartup: false });
    requestUpdateReload({ reason: 'build-mismatch', atStartup: false, beforeReload });

    session.unmount();
    applyHeldUpdateReload();
    await vi.runAllTimersAsync();

    expect(beforeReload).toHaveBeenCalledOnce();
    expect(reload).toHaveBeenCalledOnce();
  });

  it('a held mismatch is not replaced by a later sw-update', async () => {
    const { requestUpdateReload, applyHeldUpdateReload, useMarkPlayActive } = await loadWithSession();
    const session = renderHook(() => useMarkPlayActive());
    const beforeReload = vi.fn().mockResolvedValue(undefined);
    requestUpdateReload({ reason: 'build-mismatch', atStartup: false, beforeReload });
    requestUpdateReload({ reason: 'sw-update', atStartup: false });

    session.unmount();
    applyHeldUpdateReload();
    await vi.runAllTimersAsync();

    expect(beforeReload).toHaveBeenCalledOnce();
    expect(reload).toHaveBeenCalledOnce();
  });
});
