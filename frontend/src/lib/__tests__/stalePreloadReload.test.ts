// @vitest-environment jsdom
/**
 * stalePreloadReload.test.ts — FLAWCHESS-C0. A tab opened before a deploy
 * must reload once when a lazy chunk from the old build is gone, but never
 * reload-loop when the reload does not fix it.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  handleVitePreloadError,
  PRELOAD_RELOAD_COOLDOWN_MS,
  PRELOAD_RELOAD_STORAGE_KEY,
} from '../stalePreloadReload';

const NOW_MS = 1_800_000_000_000;
const originalLocation = window.location;

function preloadErrorEvent(): Event {
  return new Event('vite:preloadError', { cancelable: true });
}

describe('handleVitePreloadError', () => {
  let reload: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    window.sessionStorage.clear();
    reload = vi.fn();
    Object.defineProperty(window, 'location', { configurable: true, value: { reload } });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
    vi.restoreAllMocks();
  });

  it('reloads and swallows the error on the first stale-chunk failure', () => {
    const event = preloadErrorEvent();
    handleVitePreloadError(event, NOW_MS);

    expect(reload).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
    expect(window.sessionStorage.getItem(PRELOAD_RELOAD_STORAGE_KEY)).toBe(String(NOW_MS));
  });

  it('lets the error through instead of reload-looping within the cooldown', () => {
    window.sessionStorage.setItem(PRELOAD_RELOAD_STORAGE_KEY, String(NOW_MS));
    const event = preloadErrorEvent();
    handleVitePreloadError(event, NOW_MS + PRELOAD_RELOAD_COOLDOWN_MS - 1);

    expect(reload).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });

  it('reloads again after the cooldown, so a later deploy in the same tab still self-heals', () => {
    window.sessionStorage.setItem(PRELOAD_RELOAD_STORAGE_KEY, String(NOW_MS));
    const event = preloadErrorEvent();
    handleVitePreloadError(event, NOW_MS + PRELOAD_RELOAD_COOLDOWN_MS);

    expect(reload).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it('does not reload when sessionStorage is unavailable (no loop guard possible)', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('denied', 'SecurityError');
    });
    const event = preloadErrorEvent();
    handleVitePreloadError(event, NOW_MS);

    expect(reload).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });
});
