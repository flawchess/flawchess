// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  RETURN_TO_STORAGE_KEY,
  clearReturnTo,
  peekReturnTo,
  sanitizeReturnTo,
  stashReturnTo,
} from '@/lib/returnTo';

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

describe('sanitizeReturnTo', () => {
  it.each(['/train', '/bots', '/openings/explorer', '/library/games?tab=flaws', '/analysis#ply=12'])(
    'accepts app path %s',
    (path) => {
      expect(sanitizeReturnTo(path)).toBe(path);
    },
  );

  it.each([
    '//evil.com',
    '//evil.com/train',
    '/\\evil.com',
    'https://evil.com/train',
    'javascript:alert(1)',
    'train',
    '',
    '/',
    '/?x=1',
    '/login',
    '/login?tab=register',
    '/auth/callback',
    '/auth/reset-password?token=x',
  ])('rejects %s', (path) => {
    expect(sanitizeReturnTo(path)).toBeNull();
  });

  it('rejects null and undefined', () => {
    expect(sanitizeReturnTo(null)).toBeNull();
    expect(sanitizeReturnTo(undefined)).toBeNull();
  });
});

describe('stash / peek / clear', () => {
  it('round-trips a safe path and peek does not consume it', () => {
    stashReturnTo('/train');
    expect(peekReturnTo()).toBe('/train');
    expect(peekReturnTo()).toBe('/train');
    clearReturnTo();
    expect(peekReturnTo()).toBeNull();
  });

  it('does not stash an unsafe path', () => {
    stashReturnTo('//evil.com');
    expect(sessionStorage.getItem(RETURN_TO_STORAGE_KEY)).toBeNull();
  });

  it('ignores an unsafe value written to storage directly', () => {
    sessionStorage.setItem(RETURN_TO_STORAGE_KEY, '//evil.com');
    expect(peekReturnTo()).toBeNull();
  });

  it('survives storage that throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(() => stashReturnTo('/train')).not.toThrow();
    expect(peekReturnTo()).toBeNull();
    expect(() => clearReturnTo()).not.toThrow();
  });
});
