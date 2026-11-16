// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest';

import { removeRetiredBookmarkChartKeys, removeRetiredDotKeys } from '../retiredLocalStorage';

beforeEach(() => {
  localStorage.clear();
});

describe('removeRetiredBookmarkChartKeys', () => {
  it('removes the prefixed keys, keeps unrelated ones and returns the count', () => {
    localStorage.setItem('bookmark-chart-enabled-3', 'false');
    localStorage.setItem('bookmark-chart-enabled-17', 'true');
    localStorage.setItem('unrelated-key', 'keep');

    expect(removeRetiredBookmarkChartKeys(localStorage)).toBe(2);

    expect(localStorage.getItem('bookmark-chart-enabled-3')).toBeNull();
    expect(localStorage.getItem('bookmark-chart-enabled-17')).toBeNull();
    expect(localStorage.getItem('unrelated-key')).toBe('keep');
  });

  it('is a no-op on a second call', () => {
    localStorage.setItem('bookmark-chart-enabled-3', 'false');
    removeRetiredBookmarkChartKeys(localStorage);
    expect(removeRetiredBookmarkChartKeys(localStorage)).toBe(0);
  });

  it('returns 0 without throwing when storage access throws', () => {
    const throwing = {
      get length(): number {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredBookmarkChartKeys(throwing)).toBe(0);
  });

  it('returns 0 without throwing when key() throws', () => {
    const throwing = {
      length: 1,
      key: () => {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredBookmarkChartKeys(throwing)).toBe(0);
  });
});

describe('removeRetiredDotKeys', () => {
  it('removes every user_flag: key and the two retired Openings hint keys, keeps unrelated ones and returns the count', () => {
    localStorage.setItem('user_flag:a@b.c:openings_visited', '1');
    localStorage.setItem('user_flag:a@b.c:train_bots_visited', '1');
    localStorage.setItem('played-as-hint-dismissed', 'true');
    localStorage.setItem('filters-hint-dismissed', 'true');
    localStorage.setItem('unrelated-key', 'keep');
    localStorage.setItem('flawchess-mute', 'keep too');

    expect(removeRetiredDotKeys(localStorage)).toBe(4);

    expect(localStorage.getItem('user_flag:a@b.c:openings_visited')).toBeNull();
    expect(localStorage.getItem('user_flag:a@b.c:train_bots_visited')).toBeNull();
    expect(localStorage.getItem('played-as-hint-dismissed')).toBeNull();
    expect(localStorage.getItem('filters-hint-dismissed')).toBeNull();
    expect(localStorage.getItem('unrelated-key')).toBe('keep');
    expect(localStorage.getItem('flawchess-mute')).toBe('keep too');
  });

  it('is a no-op on a second call', () => {
    localStorage.setItem('user_flag:a@b.c:openings_visited', '1');
    removeRetiredDotKeys(localStorage);
    expect(removeRetiredDotKeys(localStorage)).toBe(0);
  });

  it('returns 0 without throwing when storage access throws', () => {
    const throwing = {
      get length(): number {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredDotKeys(throwing)).toBe(0);
  });

  it('returns 0 without throwing when key() throws', () => {
    const throwing = {
      length: 1,
      key: () => {
        throw new Error('storage blocked');
      },
    } as unknown as Storage;
    expect(removeRetiredDotKeys(throwing)).toBe(0);
  });
});
