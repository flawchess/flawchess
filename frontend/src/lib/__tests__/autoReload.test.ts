// @vitest-environment jsdom
/**
 * autoReload.test.ts — Quick 261004-rmc. An automatic reload must leave a
 * one-shot marker for the next page load, and must reload even when storage
 * is unavailable.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { consumeAutoReloadMarker, reloadAutomatically } from '../autoReload';

const originalLocation = window.location;

describe('reloadAutomatically', () => {
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

  it('marks the reload as automatic before reloading', () => {
    reload.mockImplementation(() => {
      expect(window.sessionStorage.length).toBe(1);
    });
    reloadAutomatically();
    expect(reload).toHaveBeenCalledOnce();
  });

  it('reports the marker exactly once', () => {
    reloadAutomatically();
    expect(consumeAutoReloadMarker()).toBe(true);
    expect(consumeAutoReloadMarker()).toBe(false);
  });

  it('reports no marker for a normal page load', () => {
    expect(consumeAutoReloadMarker()).toBe(false);
  });

  it('still reloads when sessionStorage throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    reloadAutomatically();
    expect(reload).toHaveBeenCalledOnce();
  });

  it('reports no marker when sessionStorage throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    expect(consumeAutoReloadMarker()).toBe(false);
  });
});
