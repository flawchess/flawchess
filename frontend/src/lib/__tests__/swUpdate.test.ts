// @vitest-environment jsdom
/**
 * swUpdate.test.ts — FLAWCHESS-91. `main.tsx` itself is not unit-testable
 * (module-scope `createRoot(...).render(<App/>)`), so the checker was
 * extracted into `frontend/src/lib/swUpdate.ts` and is tested here.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as Sentry from '@sentry/react';
import { createSwUpdateChecker, SW_UPDATE_DEBOUNCE_MS } from '../swUpdate';

// @sentry/react's ESM module namespace is not configurable, so vi.spyOn cannot
// redefine captureException on the real module — mock the module instead
// (mirrors workerPool.test.ts).
vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

/** Stub `navigator.serviceWorker.getRegistration` to resolve/reject with the given behavior. */
function stubServiceWorker(getRegistration: ReturnType<typeof vi.fn>): void {
  Object.defineProperty(navigator, 'serviceWorker', {
    value: { getRegistration },
    configurable: true,
  });
}

/** A `DOMException`-shaped object matching WebKit's benign update() rejection. */
function invalidStateError(): unknown {
  return { name: 'InvalidStateError', message: 'newestWorker is null' };
}

describe('createSwUpdateChecker', () => {
  beforeEach(() => {
    vi.mocked(Sentry.captureException).mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('swallows the benign WebKit InvalidStateError from reg.update() without capturing to Sentry', async () => {
    const update = vi.fn().mockRejectedValue(invalidStateError());
    const getRegistration = vi.fn().mockResolvedValue({ update });
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await expect(check()).resolves.toBeUndefined();
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('captures an unexpected error to Sentry but still resolves (never an unhandled rejection)', async () => {
    const update = vi.fn().mockRejectedValue(new TypeError('boom'));
    const getRegistration = vi.fn().mockResolvedValue({ update });
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await expect(check()).resolves.toBeUndefined();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
    const [err, ctx] = vi.mocked(Sentry.captureException).mock.calls[0]!;
    expect(err).toBeInstanceOf(TypeError);
    expect(ctx).toEqual(expect.objectContaining({ tags: expect.objectContaining({ source: 'sw-update' }) }));
  });

  it('a rejecting getRegistration() is caught the same way as a rejecting update()', async () => {
    const getRegistration = vi.fn().mockRejectedValue(new Error('registration lookup failed'));
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await expect(check()).resolves.toBeUndefined();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('no registration present resolves cleanly with no capture and no throw', async () => {
    const getRegistration = vi.fn().mockResolvedValue(undefined);
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await expect(check()).resolves.toBeUndefined();
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('debounces: a second call within SW_UPDATE_DEBOUNCE_MS does not call getRegistration again', async () => {
    const update = vi.fn().mockResolvedValue(undefined);
    const getRegistration = vi.fn().mockResolvedValue({ update });
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await check();
    await check();
    expect(getRegistration).toHaveBeenCalledTimes(1);
  });

  it('a call whose update() threw still consumed the debounce slot — the immediately-following call is a no-op', async () => {
    const update = vi.fn().mockRejectedValue(new TypeError('boom'));
    const getRegistration = vi.fn().mockResolvedValue({ update });
    stubServiceWorker(getRegistration);

    const check = createSwUpdateChecker();
    await check();
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);

    await check();
    // Still exactly one call, and getRegistration was not invoked a second time.
    expect(getRegistration).toHaveBeenCalledTimes(1);
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  });

  it('SW_UPDATE_DEBOUNCE_MS is a positive duration (sanity — pins the constant used above)', () => {
    expect(SW_UPDATE_DEBOUNCE_MS).toBeGreaterThan(0);
  });
});

// ── installSwControllerReload ─────────────────────────────────────────────
// Dynamic imports + vi.resetModules(): the reload gate is a module singleton.

const originalLocation = window.location;

interface ServiceWorkerStub extends EventTarget {
  controller: unknown;
  getRegistration: ReturnType<typeof vi.fn>;
}

function stubServiceWorkerTarget(controller: unknown, getRegistration: ReturnType<typeof vi.fn>): ServiceWorkerStub {
  const target = new EventTarget() as ServiceWorkerStub;
  target.controller = controller;
  target.getRegistration = getRegistration;
  Object.defineProperty(navigator, 'serviceWorker', { value: target, configurable: true });
  return target;
}

describe('installSwControllerReload', () => {
  let reload: ReturnType<typeof vi.fn>;

  async function install(): Promise<{
    gate: typeof import('../updateReload');
    playActive: typeof import('../playActive');
  }> {
    vi.resetModules();
    const swUpdate = await import('../swUpdate');
    swUpdate.installSwControllerReload();
    // Let the getRegistration promise settle.
    await vi.advanceTimersByTimeAsync(0);
    return { gate: await import('../updateReload'), playActive: await import('../playActive') };
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
    vi.unstubAllGlobals();
  });

  async function fireControllerChange(target: ServiceWorkerStub): Promise<void> {
    target.dispatchEvent(new Event('controllerchange'));
    await vi.advanceTimersByTimeAsync(10);
  }

  it('no controller and no registration: the first controllerchange (first install) does not reload, a later one does', async () => {
    const target = stubServiceWorkerTarget(null, vi.fn().mockResolvedValue(undefined));
    await install();

    await fireControllerChange(target);
    expect(reload).not.toHaveBeenCalled();

    // Past the cooldown-free state: the gate has not stamped anything yet.
    await fireControllerChange(target);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('no controller but an active registration: the first controllerchange reloads', async () => {
    const target = stubServiceWorkerTarget(null, vi.fn().mockResolvedValue({ active: {} }));
    await install();

    await fireControllerChange(target);

    expect(reload).toHaveBeenCalledOnce();
  });

  it('a controller at load: the first controllerchange reloads', async () => {
    const target = stubServiceWorkerTarget({}, vi.fn().mockResolvedValue(undefined));
    await install();

    await fireControllerChange(target);

    expect(reload).toHaveBeenCalledOnce();
  });

  it('getRegistration rejecting is swallowed and leaves the first-install rule intact', async () => {
    // Vitest fails the run on any unhandled rejection, so reaching the
    // assertions at all proves there was none.
    const target = stubServiceWorkerTarget(null, vi.fn().mockRejectedValue(new Error('no registration')));
    await install();

    await fireControllerChange(target);
    await vi.advanceTimersByTimeAsync(10);

    expect(reload).not.toHaveBeenCalled();
  });

  it('a controllerchange during a session holds, and applies when the session ends', async () => {
    const target = stubServiceWorkerTarget({}, vi.fn().mockResolvedValue(undefined));
    const { gate, playActive } = await install();
    const { renderHook } = await import('@testing-library/react');
    const session = renderHook(() => playActive.useMarkPlayActive());

    await fireControllerChange(target);
    await vi.advanceTimersByTimeAsync(gate.SESSION_END_SETTLE_MS * 3);
    expect(reload).not.toHaveBeenCalled();

    session.unmount();
    await vi.advanceTimersByTimeAsync(gate.SESSION_END_SETTLE_MS + 1);
    expect(reload).toHaveBeenCalledOnce();
  });
});
